import numpy as np

class VAD:
    """
    Voice Activity Detection helper.
    """
    def __init__(self, threshold: float = 500.0):
        self.threshold = threshold

    def is_speech(self, chunk: bytes) -> tuple[bool, float]:
        """
        Check if audio chunk contains speech.
        Returns: (is_speech, rms_value)
        """
        if not chunk:
            return False, 0.0

        try:
            # Assumes 16-bit PCM
            audio_np = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
            rms = np.sqrt(np.mean(audio_np**2))
            return rms > self.threshold, float(rms)
        except Exception:
            return False, 0.0

    @staticmethod
    def process_for_visualization(chunk: bytes) -> list[float]:
        """Convert raw PCM bytes to normalized float list for UI."""
        try:
            pts = np.frombuffer(chunk, dtype=np.int16)[::50]
            norm_pts = pts.astype(np.float32) / 32768.0
            return norm_pts.tolist()
        except Exception:
            return []
