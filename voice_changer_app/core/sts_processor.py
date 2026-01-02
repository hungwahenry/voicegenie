import threading
import json
import time
import io
import wave
import queue
import numpy as np
from elevenlabs import ElevenLabs
from concurrent.futures import ThreadPoolExecutor
from core.vad import VAD

class STSProcessor:
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
        
        self.vad = VAD()
        self.silence_chunks = 0
        
        # Propagate direct setting of threshold to the VAD helper
        self._vad_threshold = 500
        self._vad_pause = 1.0
        self._max_duration = 30.0
        self._latency = 4
        self._stability = 0.5
        self._similarity = 0.75
        self._remove_background_noise = True

    @property
    def vad_threshold(self):
        return self._vad_threshold

    @vad_threshold.setter
    def vad_threshold(self, value):
        self._vad_threshold = value
        self.vad.threshold = value

    @property
    def vad_pause(self):
        return self._vad_pause

    @vad_pause.setter
    def vad_pause(self, value):
        self._vad_pause = float(value)

    @property
    def max_duration(self):
        return self._max_duration

    @max_duration.setter
    def max_duration(self, value):
        self._max_duration = float(value)

    @property
    def latency(self):
        return self._latency

    @latency.setter
    def latency(self, value):
        self._latency = int(value)
        
    @property
    def stability(self):
        return self._stability

    @stability.setter
    def stability(self, value):
        self._stability = float(value)

    @property
    def similarity(self):
        return self._similarity

    @similarity.setter
    def similarity(self, value):
        self._similarity = float(value)

    @property
    def remove_background_noise(self):
        return self._remove_background_noise

    @remove_background_noise.setter
    def remove_background_noise(self, value):
        self._remove_background_noise = bool(value)

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
        print("STS Processing & Worker threads started.")

    def stop_processing(self):
        self.is_processing = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
    
    def _process_loop(self, audio_manager):
        """
        Smart Phrase Buffering Loop:
        1. Wait for speech (VAD).
        2. Buffer audio while speaking.
        3. End buffer on Silence (EOS) or Max Duration.
        4. Send full phrase to API.
        """
        print("Starting Smart Audio Capture Loop...")
        
        buffer = bytearray()
        is_speaking = False
        silence_start_time = None
        
        # Config
        MIN_DURATION = 0.5     # Min phrase length (ignore clicks)
        
        while self.is_processing and not self._stop_event.is_set():
            chunk = audio_manager.get_input_chunk(timeout=0.1)
            if not chunk:
                continue

            # 1. Visualization
            if self.on_audio_data:
                pts = VAD.process_for_visualization(chunk)
                if pts: self.on_audio_data(pts)
            
            # 2. VAD Check
            is_speech_frame, rms = self.vad.is_speech(chunk)
            
            if self.on_vad_level:
                self.on_vad_level(min(rms / 2000.0, 1.0))

            current_time = time.time()

            # --- State Machine ---
            if is_speech_frame:
                if not is_speaking:
                    if self.on_log: self.on_log(f"[VAD] Speech started (RMS: {int(rms)})")
                    is_speaking = True
                
                silence_start_time = None # Reset silence timer
                buffer.extend(chunk)
            
            else:
                # Silence frame
                if is_speaking:
                    buffer.extend(chunk) # Keep trailing silence for natural fade
                    
                    if silence_start_time is None:
                        silence_start_time = current_time
                    
                    # Check if silence exceeded threshold
                    if (current_time - silence_start_time) > self.vad_pause:
                        # End of Phrase
                        duration = len(buffer) / 32000.0 # 16000Hz * 2 bytes
                        
                        if duration >= MIN_DURATION:
                            if self.on_log: self.on_log(f"[VAD] Phrase complete ({duration:.1f}s) - Sending...")
                            self.processing_queue.put(bytes(buffer))
                        else:
                            if self.on_log: self.on_log(f"[VAD] IPvbr ignored (too short: {duration:.1f}s)")
                        
                        # Reset
                        buffer.clear()
                        is_speaking = False
                        silence_start_time = None
                else:
                    # Idle silence - do nothing (Gate Closed)
                    pass

            # Safety: Force send if buffer gets too big
            if len(buffer) > (self.max_duration * 32000):
                 if self.on_log: self.on_log("[VAD] Max duration reached - Forcing send.")
                 self.processing_queue.put(bytes(buffer))
                 buffer.clear()
                 is_speaking = False
                 silence_start_time = None 

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
            # wav_file not needed for raw PCM
            
            if self.on_log:
                self.on_log(f"[API] Sending {len(audio_data)} bytes...")

            response_stream = self.client.speech_to_speech.convert(
                voice_id=self.current_voice_id,
                audio=audio_data, # Send raw bytes directly
                output_format="pcm_16000",
                optimize_streaming_latency=self.latency,
                model_id="eleven_multilingual_sts_v2",
                file_format = "pcm_s16le_16", # Raw PCM input for lowest latency
                remove_background_noise=self.remove_background_noise,
                voice_settings=json.dumps({
                    "stability": self.stability,
                    "similarity_boost": self.similarity
                })
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
