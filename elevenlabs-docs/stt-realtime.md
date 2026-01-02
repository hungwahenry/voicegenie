Realtime
Realtime speech-to-text transcription service. This WebSocket API enables streaming audio input and receiving transcription results.

Event Flow
Audio chunks are sent as input_audio_chunk messages
Transcription results are streamed back in various formats (partial, committed, with timestamps)
Supports manual commit or VAD-based automatic commit strategies
Authentication is done either by providing a valid API key in the xi-api-key header or by providing a valid token in the token query parameter. Tokens can be generated from the single use token endpoint. Use tokens if you want to transcribe audio from the client side.

Handshake
URL wss://api.elevenlabs.io/v1/speech-to-text/realtime
Method GET
Status 101 Switching Protocols
Try it
Messages

{ "message_type": "session_started", "session_id": "0b0a72b57fd743ebbed6555d44836cf2", "config": { "sample_rate": 16000, "audio_format": "pcm_16000", "language_code": "en", "timestamps_granularity": "word", "vad_commit_strategy": false, "vad_silence_threshold_secs": 1.5, "vad_threshold": 0.4, "min_speech_duration_ms": 100, "min_silence_duration_ms": 100, "max_tokens_to_recompute": 5, "model_id": "scribe_v2_realtime", "disable_logging": false, "include_timestamps": true, "include_language_detection": false } }
subscribe

{ "message_type": "input_audio_chunk", "audio_base_64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAAB9AAACABAAZGF0YQAAAAA=", "commit": true, "sample_rate": 16000, "previous_text": "Previous text to provide context to the model." }
publish

{ "message_type": "partial_transcript", "text": "The first move is what sets everything in" }
subscribe

{ "message_type": "committed_transcript", "text": "The first move is what sets everything in motion." }
subscribe

{ "message_type": "committed_transcript_with_timestamps", "text": "The first move is what sets everything in motion.", "language_code": "en", "words": [ { "text": "The", "start": 0, "end": 0.12, "type": "word", "logprob": -0.05, "characters": [ "T", "h", "e" ] }, { "text": " ", "start": 0.12, "end": 0.14, "type": "spacing" }, { "text": "first", "start": 0.14, "end": 0.42, "type": "word", "logprob": -0.03, "characters": [ "f", "i", "r", "s", "t" ] }, { "text": " ", "start": 0.42, "end": 0.44, "type": "spacing" }, { "text": "move", "start": 0.44, "end": 0.68, "type": "word", "logprob": -0.02, "characters": [ "m", "o", "v", "e" ] }, { "text": " ", "start": 0.68, "end": 0.7, "type": "spacing" }, { "text": "is", "start": 0.7, "end": 0.82, "type": "word", "logprob": -0.01, "characters": [ "i", "s" ] }, { "text": " ", "start": 0.82, "end": 0.84, "type": "spacing" }, { "text": "what", "start": 0.84, "end": 1.06, "type": "word", "logprob": -0.04, "characters": [ "w", "h", "a", "t" ] }, { "text": " ", "start": 1.06, "end": 1.08, "type": "spacing" }, { "text": "sets", "start": 1.08, "end": 1.34, "type": "word", "logprob": -0.02, "characters": [ "s", "e", "t", "s" ] }, { "text": " ", "start": 1.34, "end": 1.36, "type": "spacing" }, { "text": "everything", "start": 1.36, "end": 1.84, "type": "word", "logprob": -0.03, "characters": [ "e", "v", "e", "r", "y", "t", "h", "i", "n", "g" ] }, { "text": " ", "start": 1.84, "end": 1.86, "type": "spacing" }, { "text": "in", "start": 1.86, "end": 1.96, "type": "word", "logprob": -0.01, "characters": [ "i", "n" ] }, { "text": " ", "start": 1.96, "end": 1.98, "type": "spacing" }, { "text": "motion", "start": 1.98, "end": 2.38, "type": "word", "logprob": -0.02, "characters": [ "m", "o", "t", "i", "o", "n" ] } ] }
subscribe

Handshake
Try it
WSS
/v1/speech-to-text/realtime

Headers
xi-api-key
string
Required
Query parameters
model_id
string
Required
ID of the model to use for transcription.
token
string
Optional
Your authorization bearer token.
include_timestamps
boolean
Optional
Defaults to false
Whether to receive the committed_transcript_with_timestamps event, which includes word-level timestamps.

include_language_detection
boolean
Optional
Defaults to false
Whether to include the detected language code in the committed_transcript_with_timestamps event.

audio_format
enum
Optional
Defaults to pcm_16000
Audio encoding format for speech-to-text.

Show 7 enum values
language_code
string
Optional
Language code in ISO 639-1 or ISO 639-3 format.

commit_strategy
enum
Optional
Defaults to manual
Strategy for committing transcriptions.
Allowed values:
manual
vad
vad_silence_threshold_secs
double
Optional
Defaults to 1.5
Silence threshold in seconds for VAD.
vad_threshold
double
Optional
Defaults to 0.4
Threshold for voice activity detection.
min_speech_duration_ms
integer
Optional
Defaults to 250
Minimum speech duration in milliseconds.
min_silence_duration_ms
integer
Optional
Defaults to 2500
Minimum silence duration in milliseconds.
enable_logging
boolean
Optional
Defaults to true
When enable_logging is set to false zero retention mode will be used for the request. This will mean history features are unavailable for this request. Zero retention mode may only be used by enterprise customers.

Send
inputAudioChunk
object
Required

Show 5 properties
Receive
sessionStarted
object
Required

Show 3 properties
OR
partialTranscript
object
Required

Show 2 properties
OR
committedTranscript
object
Required

Show 2 properties
OR
committedTranscriptWithTimestamps
object
Required

Show 4 properties
OR
scribeError
object
Required

Show 2 properties
OR
scribeAuthError
object
Required

Show 2 properties
OR
scribeQuotaExceededError
object
Required

Show 2 properties
OR
scribeThrottledError
object
Required

Show 2 properties
OR
scribeUnacceptedTermsError
object
Required

Show 2 properties
OR
scribeRateLimitedError
object
Required

Show 2 properties
OR
scribeQueueOverflowError
object
Required

Show 2 properties
OR
scribeResourceExhaustedError
object
Required

Show 2 properties
OR
scribeSessionTimeLimitExceededError
object
Required

Show 2 properties
OR
scribeInputError
object
Required

Show 2 properties
OR
scribeChunkSizeExceededError
object
Required

Show 2 properties
OR
scribeInsufficientAudioActivityError
object
Required

Show 2 properties
OR
scribeTranscriberError
object
Required

Show 2 properties
