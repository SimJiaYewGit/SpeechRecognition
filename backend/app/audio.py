"""Bounded MP3 decoding to mono float32 at Whisper's 16 kHz sample rate."""

from dataclasses import dataclass
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

SAMPLE_RATE = 16000


class AudioError(ValueError):
    code = "invalid_audio"


class UnsupportedAudioFormat(AudioError):
    code = "unsupported_audio_format"


class AudioTooLong(AudioError):
    code = "audio_too_long"


@dataclass(frozen=True)
class DecodedAudio:
    samples: np.ndarray
    source_sample_rate: int
    source_channels: int
    duration_seconds: float


def decode_audio(path, max_duration_seconds=600):
    """Decode within the duration budget, or raise a public AudioError.

    The caller owns the file. Return mono float32 samples at SAMPLE_RATE plus
    source metadata without modifying the recording.
    """
    path = Path(path)
    if path.suffix.lower() != ".mp3":
        raise UnsupportedAudioFormat("Only MP3 recordings are supported.")
    if max_duration_seconds <= 0:
        raise ValueError("Audio duration limit must be positive")
    try:
        with sf.SoundFile(path) as source:
            if source.format != "MP3" or source.subtype != "MPEG_LAYER_III":
                raise UnsupportedAudioFormat("The file does not contain MP3 audio.")
            rate, channels = source.samplerate, source.channels
            limit = int(max_duration_seconds * rate)
            if source.frames > limit:
                raise AudioTooLong("Recording exceeds the configured duration limit.")
            chunks, frames = [], 0
            # Read at most one sample beyond the limit, even if metadata is wrong.
            while frames <= limit:
                block = source.read(min(65536, limit + 1 - frames), dtype="float32", always_2d=True)
                if not len(block):
                    break
                frames += len(block)
                if frames > limit:
                    raise AudioTooLong("Recording exceeds the configured duration limit.")
                chunks.append(block.mean(axis=1))
    except sf.LibsndfileError as error:
        raise AudioError("The recording is empty, corrupt, or cannot be decoded.") from error
    if not chunks:
        raise AudioError("The recording contains no audio samples.")
    samples = np.concatenate(chunks)
    if not np.isfinite(samples).all():
        raise AudioError("The recording contains invalid audio samples.")
    if rate != SAMPLE_RATE:
        divisor = gcd(rate, SAMPLE_RATE)
        samples = resample_poly(samples, SAMPLE_RATE // divisor, rate // divisor)
    return DecodedAudio(np.ascontiguousarray(samples, dtype=np.float32), rate, channels, frames / rate)
