Streaming

Copy page

Learn how to stream real-time audio from the ElevenLabs API using chunked transfer encoding

The ElevenLabs API supports real-time audio streaming for select endpoints, returning raw audio bytes (e.g., MP3 data) directly over HTTP using chunked transfer encoding. This allows clients to process or play audio incrementally as it is generated.

Our official Node and Python libraries include utilities to simplify handling this continuous audio stream.

Streaming is supported for the Text to Speech API, Voice Changer API & Audio Isolation API. This section focuses on how streaming works for requests made to the Text to Speech API.

In Python, a streaming request looks like:

from elevenlabs import stream
from elevenlabs.client import ElevenLabs
elevenlabs = ElevenLabs()
audio_stream = elevenlabs.text_to_speech.stream(
text="This is a test",
voice_id="JBFqnCBsd6RMkjVDRZzb",
model_id="eleven_multilingual_v2"
)

# option 1: play the streamed audio locally

stream(audio_stream)

# option 2: process the audio bytes manually

for chunk in audio_stream:
if isinstance(chunk, bytes):
print(chunk)
