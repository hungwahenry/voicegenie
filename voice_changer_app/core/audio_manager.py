import pyaudio
import threading
import queue
from typing import Optional, List, Dict

class JitterBuffer:
    """
    Smooths out irregular audio chunk arrival from API.
    Pre-fills buffer before playback to prevent gaps.
    """
    def __init__(self, target_size=5):
        self.buffer = queue.Queue(maxsize=20)
        self.target_size = target_size  # Number of chunks to pre-buffer
        self.is_primed = False
        self._lock = threading.Lock()
    
    def add_chunk(self, data: bytes):
        """Add audio chunk from API response"""
        try:
            self.buffer.put(data, block=False)
            with self._lock:
                if not self.is_primed and self.buffer.qsize() >= self.target_size:
                    self.is_primed = True
        except queue.Full:
            # Buffer full, drop oldest or skip (we skip here)
            pass
    
    def get_chunk(self, timeout=0.1) -> Optional[bytes]:
        """Get chunk for playback (only after primed)"""
        with self._lock:
            if not self.is_primed:
                return None
        try:
            return self.buffer.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def reset(self):
        """Clear buffer and reset priming"""
        with self._lock:
            while not self.buffer.empty():
                try:
                    self.buffer.get_nowait()
                except queue.Empty:
                    break
            self.is_primed = False

class AudioManager:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.is_running = False
        
        self.input_queue = queue.Queue()
        self.jitter_buffer = JitterBuffer(target_size=5)
        self._output_thread = None
        
        self.chunk_size = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000

    def get_devices(self) -> List[Dict]:
        """List all available audio inputs and outputs."""
        devices = []
        for i in range(self.p.get_device_count()):
            dev = self.p.get_device_info_by_index(i)
            if dev['maxInputChannels'] > 0:
                devices.append({"index": i, "name": dev['name'], "type": "input"})
            elif dev['maxOutputChannels'] > 0:
                devices.append({"index": i, "name": dev['name'], "type": "output"})
        return devices

    def start_streams(self, input_idx: int, output_idx: int):
        """Start input and output streams."""
        if self.is_running:
            self.stop_streams()

        try:
            def input_callback(in_data, frame_count, time_info, status):
                if self.is_running:
                    self.input_queue.put(in_data)
                    # print(".", end="", flush=True) # Debug visualizer
                return (None, pyaudio.paContinue)

            self.input_stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=input_idx,
                frames_per_buffer=self.chunk_size,
                stream_callback=input_callback
            )
            
            self.output_stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                output=True,
                output_device_index=output_idx,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_running = True
            self.input_stream.start_stream()
            self.output_stream.start_stream()
            
            self._output_thread = threading.Thread(target=self._output_loop, daemon=True)
            self._output_thread.start()
            
            print(f"Audio streams started on In:{input_idx} Out:{output_idx}")
            
        except Exception as e:
            print(f"Error starting streams: {e}")
            self.stop_streams()
            raise e
    
    def _output_loop(self):
        """Background thread that continuously drains jitter buffer to output"""
        while self.is_running:
            chunk = self.jitter_buffer.get_chunk(timeout=0.05)
            if chunk and self.output_stream and self.is_running:
                try:
                    self.output_stream.write(chunk)
                except OSError:
                    pass

    def stop_streams(self):
        """Stop and close streams."""
        self.is_running = False
        
        if self._output_thread and self._output_thread.is_alive():
            self._output_thread.join(timeout=0.5)
        
        if self.input_stream:
            if self.input_stream.is_active():
                self.input_stream.stop_stream()
            self.input_stream.close()
            self.input_stream = None
            
        if self.output_stream:
            if self.output_stream.is_active():
                self.output_stream.stop_stream()
            self.output_stream.close()
            self.output_stream = None

        self.jitter_buffer.reset()
        with self.input_queue.mutex:
            self.input_queue.queue.clear()

    def get_input_chunk(self, timeout: float = 0.5) -> Optional[bytes]:
        """Get the next chunk of audio from the input queue."""
        try:
            return self.input_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def write_output_chunk(self, data: bytes):
        """Write processed audio to jitter buffer (not directly to output)."""
        if self.is_running:
            self.jitter_buffer.add_chunk(data)

    def terminate(self):
        """Cleanup PyAudio."""
        self.stop_streams()
        self.p.terminate()
