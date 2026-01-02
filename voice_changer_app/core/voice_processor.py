import threading
import time
import io
import wave
import queue
import numpy as np
from elevenlabs import ElevenLabs, VoiceSettings
from concurrent.futures import ThreadPoolExecutor
from typing import Generator, Iterator

class VoiceProcessor:
    def __init__(self, api_key: str):
        self.client = ElevenLabs(api_key=api_key)
        self.current_voice_id = None
        self.is_processing = False
        self._thread = None
        self._stop_event = threading.Event()
        
        self._executor = ThreadPoolExecutor(max_workers=1)
        self.processing_queue = queue.Queue()
        
        self.on_log = None
        self.on_vad_level = None
        self.on_audio_data = None
        
        self.vad_threshold = 500
        self.silence_chunks = 0
        self.max_silence = 10

    def set_voice(self, voice_id: str):
        self.current_voice_id = voice_id

    def get_voices(self):
        """Fetch available voices from API."""
        try:
            response = self.client.voices.get_all()
            return response.voices
        except Exception as e:
            msg = f"Error fetching voices: {e}"
            print(msg)
            if self.on_log: self.on_log(msg)
            return []

    def start_processing(self, audio_manager):
        if self.is_processing:
            return

        self.is_processing = True
        self._stop_event.clear()
        
        self._thread = threading.Thread(target=self._process_loop, args=(audio_manager,))
        self._thread.daemon = True
        self._thread.start()
        
        self._executor.submit(self._worker_loop, audio_manager)
        print("Voice Processing & Worker threads started.")

    def stop_processing(self):
        self.is_processing = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        with self.processing_queue.mutex:
            self.processing_queue.queue.clear()

    def _process_loop(self, audio_manager):
        """
        Inner loop that accumulates audio, checks VAD, and pushes active chunks to queue.
        """
        print("Starting Audio Capture Loop...")
        
        buffer = bytearray()
        accumulate_target = 4800 # ~300ms at 16khz
        
        while self.is_processing and not self._stop_event.is_set():
            chunk = audio_manager.get_input_chunk(timeout=0.1)
            if not chunk:
                continue

            if self.on_audio_data:
                try:
                    pts = np.frombuffer(chunk, dtype=np.int16)[::50]
                    norm_pts = pts.astype(np.float32) / 32768.0
                    self.on_audio_data(norm_pts.tolist())
                except (ValueError, AttributeError):
                    pass
            
            buffer.extend(chunk)
            
            if len(buffer) >= accumulate_target:
                raw_bytes = bytes(buffer)
                audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
                
                raw_bytes = bytes(buffer)
                audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
                
                rms = np.sqrt(np.mean(audio_np**2))
                
                if self.on_vad_level:
                    norm_level = min(rms / 2000.0, 1.0)
                    self.on_vad_level(norm_level)
                
                if rms > self.vad_threshold:
                    if self.on_log:
                        self.on_log(f"[VAD] Voice detected (RMS: {int(rms)}) - Queuing...")
                    
                    self.processing_queue.put(raw_bytes)
                    self.silence_chunks = 0
                else:
                    if self.silence_chunks == 0 and self.on_log:
                        self.on_log(f"[VAD] Silence detected (RMS: {int(rms)} < {self.vad_threshold})")
                    self.silence_chunks += 1
                
                buffer.clear() 

    def _worker_loop(self, audio_manager):
        while self.is_processing or not self.processing_queue.empty():
            try:
                audio_data = self.processing_queue.get(timeout=1.0)
                if not self.is_processing: break
                
                self._process_single_chunk(audio_data, audio_manager)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker Error: {e}")

    def _create_wav_bytes(self, pcm_data: bytes) -> io.BytesIO:
        """Helper to wrap raw PCM in a WAV container in-memory."""
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(pcm_data)
        wav_io.seek(0)
        return wav_io

    def _process_single_chunk(self, audio_data: bytes, audio_manager):
        if not self.current_voice_id:
            if self.on_log: self.on_log("[ERROR] No voice selected!")
            return

        try:
            wav_file = self._create_wav_bytes(audio_data)
            
            if self.on_log:
                self.on_log(f"[API] Sending {len(audio_data)} bytes...")

            response_stream = self.client.speech_to_speech.convert(
                voice_id=self.current_voice_id,
                audio=wav_file, 
                output_format="pcm_16000",
                optimize_streaming_latency=4,
                model_id="eleven_english_sts_v2"
            )
            
            total_received = 0
            for stream_chunk in response_stream:
                if stream_chunk:
                    total_received += len(stream_chunk)
                    audio_manager.write_output_chunk(stream_chunk)
            
            if self.on_log:
                self.on_log(f"[SUCCESS] Received {total_received} bytes")

        except Exception as e:
            msg = f"[API ERROR] {e}"
            print(msg)
            if self.on_log: self.on_log(msg)
