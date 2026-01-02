import customtkinter as ctk
import threading
import time
from tkinter import messagebox
from utils.settings import Settings
from utils.constants import APP_VERSION, APP_AUTHOR, APP_TITLE
from core.audio_manager import AudioManager
from core.voice_processor import VoiceProcessor

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AppWindow:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("500x700") # Slightly wider for side-by-side
        self.root.resizable(False, True) # Allow vertical resize for logs
        
        # Init components
        self.settings = Settings()
        self.audio_mgr = AudioManager()
        
        # Processor init
        self.processor = None
        if self.settings.api_key:
            try:
                self.processor = VoiceProcessor(self.settings.api_key)
                self._bind_callbacks()
            except Exception as e:
                print(e)
        
        self._setup_ui()
        self._load_devices()
        self._load_voices_async()

    def _bind_callbacks(self):
        if self.processor:
            self.processor.on_log = self._log_message
            self.processor.on_vad_level = None # Unused now
            self.processor.on_audio_data = self._update_waveform
            
            # Throttling for waveform (prevent UI lag)
            self._last_waveform_update = 0
            self._waveform_throttle = 0.066  # ~15 FPS max

    def _setup_ui(self):
        # 1. Header / API Key (Top)
        self.auth_frame = ctk.CTkFrame(self.root)
        self.auth_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(self.auth_frame, text="API Key:").pack(side="left", padx=5)
        self.api_key_var = ctk.StringVar(value=self.settings.api_key)
        self.api_entry = ctk.CTkEntry(self.auth_frame, textvariable=self.api_key_var, show="*", width=280)
        self.api_entry.pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(self.auth_frame, text="Save", width=50, command=self._save_api_key).pack(side="right", padx=5)

        # 2. Config Container (Side-by-Side)
        self.config_box = ctk.CTkFrame(self.root, fg_color="transparent")
        self.config_box.pack(fill="x", padx=10, pady=5)

        # === Left Col: Devices ===
        self.dev_frame = ctk.CTkFrame(self.config_box)
        self.dev_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ctk.CTkLabel(self.dev_frame, text="Audio Devices", font=("Arial", 12, "bold")).pack(pady=5)
        
        ctk.CTkLabel(self.dev_frame, text="Internal Mic (Input):", font=("Arial", 10)).pack(anchor="w", padx=5)
        self.input_combo = ctk.CTkComboBox(self.dev_frame, command=self._on_device_change, state="readonly", height=25)
        self.input_combo.pack(fill="x", padx=5, pady=(0, 5))

        ctk.CTkLabel(self.dev_frame, text="Virtual Cable (Output):", font=("Arial", 10)).pack(anchor="w", padx=5)
        self.output_combo = ctk.CTkComboBox(self.dev_frame, command=self._on_device_change, state="readonly", height=25)
        self.output_combo.pack(fill="x", padx=5, pady=(0, 5))
        
        ctk.CTkButton(self.dev_frame, text="Refresh", height=20, command=self._load_devices).pack(pady=5)

        # === Right Col: Voice ===
        self.voice_frame = ctk.CTkFrame(self.config_box)
        self.voice_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        ctk.CTkLabel(self.voice_frame, text="Voice Config", font=("Arial", 12, "bold")).pack(pady=5)
        
        ctk.CTkLabel(self.voice_frame, text="Target Voice:", font=("Arial", 10)).pack(anchor="w", padx=5)
        self.voice_combo = ctk.CTkComboBox(self.voice_frame, command=self._on_voice_change, state="readonly", height=25)
        self.voice_combo.pack(fill="x", padx=5, pady=(0, 5))

        ctk.CTkLabel(self.voice_frame, text="VAD Sensitivity:", font=("Arial", 10)).pack(anchor="w", padx=5)
        self.vad_slider = ctk.CTkSlider(self.voice_frame, from_=0, to=2000, command=self._on_vad_slide, height=20)
        self.vad_slider.set(500)
        self.vad_slider.pack(fill="x", padx=5, pady=(2, 0))
        
        self.vad_label = ctk.CTkLabel(self.voice_frame, text="500", font=("Arial", 10))
        self.vad_label.pack(pady=(0, 5))

        # 3. Controls (Status & Actions)
        self.ctrl_frame = ctk.CTkFrame(self.root)
        self.ctrl_frame.pack(fill="x", padx=10, pady=5)
        
        # Top Row: Status + Visualizer
        self.status_row = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        self.status_row.pack(fill="x", padx=10, pady=5)
        
        self.status_label = ctk.CTkLabel(self.status_row, text="Ready", font=("Arial", 14, "bold"), text_color="gray", anchor="w")
        self.status_label.pack(side="left")
        
        # Waveform Canvas (using standard tkinter Canvas integrated into CustomTkinter)
        # CTk doesn't have a dedicated Canvas, so we mixin standard Canvas 
        # but style it to match dark mode.
        self.wave_canvas = ctk.CTkCanvas(self.status_row, width=150, height=30, bg="#2b2b2b", highlightthickness=0)
        self.wave_canvas.pack(side="right", pady=5)

        # Start Button
        self.start_btn = ctk.CTkButton(self.ctrl_frame, text="START Voice Changer", height=45, font=("Arial", 16, "bold"), fg_color="green", command=self._toggle_streaming)
        self.start_btn.pack(fill="x", padx=10, pady=(0, 10))

        # 4. Console (Fills Rest)
        ctk.CTkLabel(self.root, text="System Logs:", font=("Arial", 11, "bold")).pack(anchor="w", padx=12, pady=(5,0))
        self.console = ctk.CTkTextbox(self.root, font=("Consolas", 10))
        self.console.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        self.console.insert("0.0", "--- System Ready ---\n")
        
        # 5. Footer (Version/Author)
        footer_text = f"Voice Changer v{APP_VERSION} | Author: {APP_AUTHOR}" 
        ctk.CTkLabel(self.root, text=footer_text, font=("Arial", 9), text_color="gray").pack(pady=(0, 5))

    def _log_message(self, msg):
        def _update():
            try:
                self.console.insert("end", f"{msg}\n")
                self.console.see("end")
            except (RuntimeError, AttributeError):
                pass
        self.root.after(0, _update)

    def _update_waveform(self, samples):
        current_time = time.time()
        if current_time - self._last_waveform_update < self._waveform_throttle:
            return
        
        self._last_waveform_update = current_time
        
        def _draw():
            try:
                w, h = 150, 30
                mid = h / 2
                self.wave_canvas.delete("all")
                
                step = w / len(samples)
                coords = []
                for i, s in enumerate(samples):
                    x = i * step
                    y = mid + (s * mid * 0.9)
                    coords.append(x)
                    coords.append(y)
                
                if len(coords) > 4:
                    self.wave_canvas.create_line(coords, fill="#00ff00", width=1, smooth=True)
            except (RuntimeError, AttributeError, TclError):
                pass
        self.root.after(0, _draw)



    def _on_vad_slide(self, value):
        val = int(value)
        self.vad_label.configure(text=str(val))
        if self.processor:
            self.processor.vad_threshold = val

    def _save_api_key(self):
        key = self.api_key_var.get().strip()
        if not key: return
        self.settings.api_key = key
        self.settings.save()
        try:
            self.processor = VoiceProcessor(key)
            self._bind_callbacks()
            self._load_voices_async()
            self._log_message("API Key saved.")
        except Exception as e:
            self._log_message(f"Error init API: {e}")

    def _load_devices(self):
        devices = self.audio_mgr.get_devices()
        input_names = [f"{d['index']}: {d['name']}" for d in devices if d['type'] == 'input']
        output_names = [f"{d['index']}: {d['name']}" for d in devices if d['type'] == 'output']
        
        self.input_combo.configure(values=input_names)
        self.output_combo.configure(values=output_names)
        
        if input_names: self.input_combo.set(input_names[0])
        if output_names: self.output_combo.set(output_names[0])

        # Restore
        if self.settings.input_device_index is not None:
             for s in input_names:
                 if s.startswith(f"{self.settings.input_device_index}:"):
                     self.input_combo.set(s)
        if self.settings.output_device_index is not None:
             for s in output_names:
                 if s.startswith(f"{self.settings.output_device_index}:"):
                     self.output_combo.set(s)

    def _on_device_change(self, choice):
        if not choice:
            return
        try:
            in_val = self.input_combo.get()
            out_val = self.output_combo.get()
            if in_val:
                self.settings.input_device_index = int(in_val.split(":")[0])
            if out_val:
                self.settings.output_device_index = int(out_val.split(":")[0])
            self.settings.save()
        except (ValueError, IndexError, AttributeError):
            pass

    def _load_voices_async(self):
        if not self.processor: return
        def fetch():
            voices = self.processor.get_voices()
            self.root.after(0, lambda: self._update_voice_list(voices))
        threading.Thread(target=fetch, daemon=True).start()

    def _update_voice_list(self, voices):
        self.voices = voices
        names = [v.name for v in voices]
        self.voice_combo.configure(values=names)
        if names: self.voice_combo.set(names[0])
        
        if self.settings.voice_id:
            for v in voices:
                if v.voice_id == self.settings.voice_id:
                    self.voice_combo.set(v.name)
                    self.processor.set_voice(v.voice_id)
                    break 
        else:
             self._on_voice_change(self.voice_combo.get())

    def _on_voice_change(self, name):
        if not hasattr(self, 'voices'): return
        for v in self.voices:
            if v.name == name:
                self.settings.voice_id = v.voice_id
                self.settings.save()
                if self.processor:
                    self.processor.set_voice(v.voice_id)
                break

    def _toggle_streaming(self):
        if not self.processor:
            self._log_message("Error: No API Key")
            return

        if self.audio_mgr.is_running:
            # STOP - Run in background to prevent UI freeze
            self.status_label.configure(text="Stopping...", text_color="orange")
            self.start_btn.configure(state="disabled")  # Prevent double-click
            
            def _stop_async():
                self.processor.stop_processing()
                self.audio_mgr.stop_streams()
                # Update UI from main thread
                self.root.after(0, lambda: self._on_stop_complete())
            
            threading.Thread(target=_stop_async, daemon=True).start()
        else:
            # START - Run in background to prevent UI freeze
            try:
                in_str = self.input_combo.get()
                out_str = self.output_combo.get()
                if not in_str or not out_str:
                    self._log_message("Error: Select devices first")
                    return
                    
                in_idx = int(in_str.split(":")[0])
                out_idx = int(out_str.split(":")[0])
                
                # Update UI immediately
                self.status_label.configure(text="Starting...", text_color="orange")
                self.start_btn.configure(state="disabled")  # Prevent double-click
                
                def _start_async():
                    try:
                        self.audio_mgr.start_streams(in_idx, out_idx)
                        self.processor.start_processing(self.audio_mgr)
                        # Update UI from main thread
                        self.root.after(0, lambda: self._on_start_complete())
                    except Exception as e:
                        self.root.after(0, lambda: self._on_start_error(str(e)))
                
                threading.Thread(target=_start_async, daemon=True).start()
                
            except Exception as e:
                self._log_message(f"Start Error: {e}")
                self.start_btn.configure(state="normal")
    
    def _on_start_complete(self):
        """Called when async start completes"""
        self.start_btn.configure(text="STOP Voice Changer", fg_color="red", state="normal")
        self.status_label.configure(text="ACTIVE (Streaming)", text_color="#00FF00")
    
    def _on_start_error(self, error_msg):
        """Called when async start fails"""
        self._log_message(f"Start Error: {error_msg}")
        self.start_btn.configure(text="START Voice Changer", fg_color="green", state="normal")
        self.status_label.configure(text="Ready", text_color="gray")
    
    def _on_stop_complete(self):
        """Called when async stop completes"""
        self.start_btn.configure(text="START Voice Changer", fg_color="green", state="normal")
        self.status_label.configure(text="Ready", text_color="gray")

    def on_closing(self):
        if self.audio_mgr.is_running:
            self.audio_mgr.stop_streams()
        if self.processor:
            self.processor.stop_processing()
        self.root.destroy()
