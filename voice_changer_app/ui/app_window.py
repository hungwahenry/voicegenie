import customtkinter as ctk
import threading
import time
from tkinter import messagebox
from utils.settings import Settings
from utils.constants import APP_VERSION, APP_AUTHOR, APP_TITLE
from utils.device_guide import get_device_guide_text
from core.audio_manager import AudioManager
from core.sts_processor import STSProcessor

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AppWindow:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("500x600") # Compact height, fits all screens
        self.root.resizable(False, True) # Allow vertical resize for logs
        
        # Init components
        self.settings = Settings()
        self.audio_mgr = AudioManager(max_buffer_size=self.settings.playback_buffer_size)
        
        # Processor init
        self.sts_processor = None
        
        if self.settings.api_key:
            try:
                self.sts_processor = STSProcessor(self.settings.api_key)
                # Apply saved settings
                self.sts_processor.vad_threshold = 500 # Default/Saved val usually managed via UI
                self.sts_processor.vad_pause = self.settings.vad_pause
                self.sts_processor.max_duration = self.settings.max_duration
                self.sts_processor.latency = self.settings.latency
                self.sts_processor.stability = self.settings.stability
                self.sts_processor.similarity = self.settings.similarity
                self.sts_processor.remove_background_noise = self.settings.remove_background_noise
                
                self._bind_callbacks()
            except Exception as e:
                print(e)
        
        self._setup_ui()
        self._load_devices()
        self._load_voices_async()

    def _bind_callbacks(self):
        if self.sts_processor:
            self.sts_processor.on_log = self._log_message
            self.sts_processor.on_vad_level = None # Unused now
            self.sts_processor.on_audio_data = self._update_waveform
            
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

        # 2. Tabs for Configuration
        # 2. Tabs for Configuration
        # 2. Tabs for Configuration
        self.tab_view = ctk.CTkTabview(self.root, height=280)
        self.tab_view.pack(fill="x", padx=10, pady=2)
        
        self.tab_io = self.tab_view.add("Input / Output")
        self.tab_voice = self.tab_view.add("Voice & Quality")
        
        # === TAB 1: Input / Output (Grid Layout) ===
        self.tab_io.grid_columnconfigure(0, weight=1)
        self.tab_io.grid_columnconfigure(1, weight=1)
        
        # Row 0: Device Labels
        ctk.CTkLabel(self.tab_io, text="Input (Mic):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=(5,0))
        ctk.CTkLabel(self.tab_io, text="Output (Cable):", font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", padx=5, pady=(5,0))
        
        # Row 1: Device Combos
        self.input_combo = ctk.CTkComboBox(self.tab_io, command=self._on_device_change, state="readonly", height=24)
        self.input_combo.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        
        self.output_combo = ctk.CTkComboBox(self.tab_io, command=self._on_device_change, state="readonly", height=24)
        self.output_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=(0, 5))
        
        # Row 2: Refresh + Help
        ctk.CTkButton(self.tab_io, text="Refresh Devices", height=20, font=("Arial", 10), command=self._load_devices).grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.tab_io, text="Help / Guide", height=20, font=("Arial", 10, "bold"), width=80, fg_color="gray", command=self._show_guide).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        # Row 3: Noise Checkbox (Spanning)
        self.noise_chk = ctk.CTkCheckBox(self.tab_io, text="AI Noise Removal", font=("Arial", 10), height=20, command=self._on_noise_chk)
        if self.settings.remove_background_noise: self.noise_chk.select()
        else: self.noise_chk.deselect()
        self.noise_chk.grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        
        # Row 4: VAD & Silence Labels
        self.vad_label = ctk.CTkLabel(self.tab_io, text="VAD Threshold: 500", font=("Arial", 10), anchor="w")
        self.vad_label.grid(row=4, column=0, sticky="w", padx=5)
        
        self.pause_label = ctk.CTkLabel(self.tab_io, text=f"Silence Wait: {self.settings.vad_pause:.1f}s", font=("Arial", 10), anchor="w")
        self.pause_label.grid(row=4, column=1, sticky="w", padx=5)
        
        # Row 5: VAD & Silence Sliders
        self.vad_slider = ctk.CTkSlider(self.tab_io, from_=0, to=2000, command=self._on_vad_slide, height=16)
        self.vad_slider.set(500)
        self.vad_slider.grid(row=5, column=0, sticky="ew", padx=5, pady=(0, 5))
        
        self.pause_slider = ctk.CTkSlider(self.tab_io, from_=0.1, to=3.0, number_of_steps=29, command=self._on_pause_slide, height=16)
        self.pause_slider.set(self.settings.vad_pause)
        self.pause_slider.grid(row=5, column=1, sticky="ew", padx=5, pady=(0, 5))

        # Row 6: Buffer Size Label & Slider
        self.buf_label = ctk.CTkLabel(self.tab_io, text=f"Playback Buffer: {self.settings.playback_buffer_size} chunks", font=("Arial", 10), anchor="w")
        self.buf_label.grid(row=6, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0))
        
        self.buf_slider = ctk.CTkSlider(self.tab_io, from_=100, to=5000, number_of_steps=49, command=self._on_buf_slide, height=16)
        self.buf_slider.set(self.settings.playback_buffer_size)
        self.buf_slider.grid(row=7, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 5))


        # === TAB 2: Voice & Quality (Grid Layout) ===
        self.tab_voice.grid_columnconfigure(0, weight=1)
        self.tab_voice.grid_columnconfigure(1, weight=1)
        
        # Row 0: Voice Selection (Spanning)
        ctk.CTkLabel(self.tab_voice, text="Target Voice:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(5,0))
        self.voice_combo = ctk.CTkComboBox(self.tab_voice, command=self._on_voice_change, state="readonly", height=24)
        self.voice_combo.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 10))
        
        # Row 2: Stability & Similarity Labels
        self.stab_label = ctk.CTkLabel(self.tab_voice, text=f"Stability: {self.settings.stability:.2f}", font=("Arial", 10), anchor="w")
        self.stab_label.grid(row=2, column=0, sticky="w", padx=5)
        
        self.sim_label = ctk.CTkLabel(self.tab_voice, text=f"Similarity: {self.settings.similarity:.2f}", font=("Arial", 10), anchor="w")
        self.sim_label.grid(row=2, column=1, sticky="w", padx=5)
        
        # Row 3: Stability & Similarity Sliders
        self.stab_slider = ctk.CTkSlider(self.tab_voice, from_=0.0, to=1.0, command=self._on_stab_slide, height=16)
        self.stab_slider.set(self.settings.stability)
        self.stab_slider.grid(row=3, column=0, sticky="ew", padx=5, pady=(0, 10))
        
        self.sim_slider = ctk.CTkSlider(self.tab_voice, from_=0.0, to=1.0, command=self._on_sim_slide, height=16)
        self.sim_slider.set(self.settings.similarity)
        self.sim_slider.grid(row=3, column=1, sticky="ew", padx=5, pady=(0, 10))
        
        # Row 4: Latency (Spanning)
        self.latency_label = ctk.CTkLabel(self.tab_voice, text=f"Latency Opt: Level {self.settings.latency}", font=("Arial", 10), anchor="w")
        self.latency_label.grid(row=4, column=0, columnspan=2, sticky="w", padx=5)
        
        self.latency_slider = ctk.CTkSlider(self.tab_voice, from_=0, to=4, number_of_steps=4, command=self._on_latency_slide, height=16)
        self.latency_slider.set(self.settings.latency)
        self.latency_slider.grid(row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 5))

        # 3. Controls (Status & Actions)
        self.ctrl_frame = ctk.CTkFrame(self.root)
        self.ctrl_frame.pack(fill="x", padx=10, pady=5)
        
        # Top Row: Status + Visualizer
        self.status_row = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        self.status_row.pack(fill="x", padx=10, pady=5)
        
        self.status_label = ctk.CTkLabel(self.status_row, text="Ready", font=("Arial", 14, "bold"), text_color="gray", anchor="w")
        self.status_label.pack(side="left")
        
        # Waveform Canvas
        self.wave_canvas = ctk.CTkCanvas(self.status_row, width=150, height=30, bg="#2b2b2b", highlightthickness=0)
        self.wave_canvas.pack(side="right", pady=5)

        # Start Button
        self.start_btn = ctk.CTkButton(self.ctrl_frame, text="START Voice Changer", height=45, font=("Arial", 16, "bold"), fg_color="green", command=self._toggle_streaming)
        self.start_btn.pack(fill="x", padx=10, pady=(0, 10))

        # 5. Footer (Version/Author)
        footer_text = f"{APP_TITLE} | Author: {APP_AUTHOR}" 
        ctk.CTkLabel(self.root, text=footer_text, font=("Arial", 9), text_color="gray").pack(side="bottom", pady=(0, 5))

        # 4. Console (Fills Rest)
        ctk.CTkLabel(self.root, text="System Logs:", font=("Arial", 11, "bold")).pack(anchor="w", padx=12, pady=(5,0))
        self.console = ctk.CTkTextbox(self.root, font=("Consolas", 10))
        self.console.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        self.console.insert("0.0", "--- System Ready ---\n")

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
        if current_time - self._last_waveform_update < 0.05:
            return
        
        self._last_waveform_update = current_time
        
        def _draw():
            # Check existence to prevent errors on closing
            if not self.root or not self.wave_canvas.winfo_exists():
                return

            try:
                w = self.wave_canvas.winfo_width() # Dynamic width
                h = self.wave_canvas.winfo_height()
                mid = h / 2
                
                self.wave_canvas.delete("all")
                
                limit = max(10, int(w / 2))
                if len(samples) > limit:
                     step_size = len(samples) // limit
                     draw_samples = samples[::step_size]
                else:
                     draw_samples = samples

                step = w / len(draw_samples)
                coords = []
                for i, s in enumerate(draw_samples):
                    x = i * step
                    y = mid + (s * mid * 0.8)
                    coords.append(x)
                    coords.append(y)
                
                if len(coords) > 4:
                    self.wave_canvas.create_line(coords, fill="#00ff00", width=1.5, smooth=True)
                    
            except Exception:
                pass
                
        self.root.after(0, _draw)



    def _on_vad_slide(self, value):
        val = int(value)
        self.vad_label.configure(text=f"VAD Threshold: {val}")
        if self.sts_processor:
            self.sts_processor.vad_threshold = val

    def _on_pause_slide(self, value):
        val = round(float(value), 1)
        self.pause_label.configure(text=f"Silence Wait: {val}s")
        self.settings.vad_pause = val
        self.settings.save()
        if self.sts_processor:
            self.sts_processor.vad_pause = val

    def _on_buf_slide(self, value):
        val = int(value)
        self.buf_label.configure(text=f"Playback Buffer: {val} chunks")
        self.settings.playback_buffer_size = val
        self.settings.save()
        if not self.audio_mgr.is_running:
            self.audio_mgr.set_buffer_size(val)

    def _on_latency_slide(self, value):
        val = int(value)
        self.latency_label.configure(text=f"Latency Opt: Level {val}")
        self.settings.latency = val
        self.settings.save()
        if self.sts_processor:
            self.sts_processor.latency = val

    def _on_noise_chk(self):
        val = bool(self.noise_chk.get())
        self.settings.remove_background_noise = val
        self.settings.save()
        if self.sts_processor:
            self.sts_processor.remove_background_noise = val

    def _on_stab_slide(self, value):
        val = round(float(value), 2)
        self.stab_label.configure(text=f"Stability: {val:.2f}")
        self.settings.stability = val
        self.settings.save()
        if self.sts_processor:
            self.sts_processor.stability = val

    def _on_sim_slide(self, value):
        val = round(float(value), 2)
        self.sim_label.configure(text=f"Similarity: {val:.2f}")
        self.settings.similarity = val
        self.settings.save()
        if self.sts_processor:
            self.sts_processor.similarity = val
    
    def _save_api_key(self):
        key = self.api_key_var.get().strip()
        if not key: return
        self.settings.api_key = key
        self.settings.save()
        try:
            self.sts_processor = STSProcessor(key)
            self.sts_processor.vad_pause = self.settings.vad_pause
            self.sts_processor.max_duration = self.settings.max_duration
            self.sts_processor.latency = self.settings.latency
            self.sts_processor.stability = self.settings.stability
            self.sts_processor.similarity = self.settings.similarity
            self.sts_processor.remove_background_noise = self.settings.remove_background_noise
            
            self._bind_callbacks()
            self._load_voices_async()
            self._log_message("API Key saved.")
        except Exception as e:
            self._log_message(f"Error init API: {e}")

    def _show_guide(self):
        """Show audio setup guide in a modal window"""
        guide_window = ctk.CTkToplevel(self.root)
        guide_window.title("Audio Setup Guide")
        guide_window.geometry("500x450")
        
        # Make modal
        guide_window.transient(self.root) 
        guide_window.grab_set()
        
        textbox = ctk.CTkTextbox(guide_window, font=("Consolas", 11))
        textbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        text = get_device_guide_text()
        textbox.insert("0.0", text)
        textbox.configure(state="disabled") # Read-only
        
        ctk.CTkButton(guide_window, text="Close", command=guide_window.destroy).pack(pady=10)

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
        if not self.sts_processor: return
        def fetch():
            voices = self.sts_processor.get_voices()
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
                    self.sts_processor.set_voice(v.voice_id)
                    break 
        else:
             self._on_voice_change(self.voice_combo.get())

    def _on_voice_change(self, name):
        if not hasattr(self, 'voices'): return
        for v in self.voices:
            if v.name == name:
                self.settings.voice_id = v.voice_id
                self.settings.save()
                if self.sts_processor:
                    self.sts_processor.set_voice(v.voice_id)
                break

    def _toggle_streaming(self):
        if not self.sts_processor:
            self._log_message("Error: No API Key")
            return

        if self.audio_mgr.is_running:
            self.status_label.configure(text="Stopping...", text_color="orange")
            self.start_btn.configure(state="disabled")
            
            def _stop_async():
                self.sts_processor.stop_processing()
                self.audio_mgr.stop_streams()
                self.root.after(0, lambda: self._on_stop_complete())
            
            threading.Thread(target=_stop_async, daemon=True).start()
        else:
            try:
                in_str = self.input_combo.get()
                out_str = self.output_combo.get()
                if not in_str or not out_str:
                    self._log_message("Error: Select devices first")
                    return
                    
                in_idx = int(in_str.split(":")[0])
                out_idx = int(out_str.split(":")[0])
                
                self.status_label.configure(text="Starting...", text_color="orange")
                self.start_btn.configure(state="disabled")
                
                def _start_async():
                    try:
                        self.audio_mgr.start_streams(in_idx, out_idx)
                        self.sts_processor.start_processing(self.audio_mgr)
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
        if self.sts_processor:
            self.sts_processor.stop_processing()
        self.root.destroy()
