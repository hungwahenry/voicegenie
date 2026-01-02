import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CONFIG_FILE = Path("config.json")

class Settings:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "")
        self.input_device_index = None
        self.output_device_index = None
        self.voice_id = None
        self.load()

    def load(self):
        """Load settings from JSON file if it exists."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.api_key = data.get("api_key", self.api_key)
                    self.input_device_index = data.get("input_device_index")
                    self.output_device_index = data.get("output_device_index")
                    self.voice_id = data.get("voice_id")
            except Exception as e:
                print(f"Error loading settings: {e}")

    def save(self):
        """Save current settings to JSON file."""
        data = {
            "api_key": self.api_key,
            "input_device_index": self.input_device_index,
            "output_device_index": self.output_device_index,
            "voice_id": self.voice_id
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
