"""Process-local CPU Whisper inference with explicit loading and bounded concurrency."""

from functools import lru_cache
from pathlib import Path
from threading import Lock

from .audio import SAMPLE_RATE, decode_audio

MODEL_ID = "openai/whisper-tiny"


class ServiceUnavailable(RuntimeError):
    code = "service_unavailable"


class ServiceBusy(RuntimeError):
    code = "service_busy"


class WhisperTranscriber:
    def __init__(self, cache_dir, max_duration_seconds=600):
        self.cache_dir = str(Path(cache_dir).resolve())
        self.max_duration_seconds = max_duration_seconds
        self._model = None
        self._processor = None
        self._load_lock = Lock()
        self._inference_lock = Lock()

    @property
    def ready(self):
        return self._model is not None

    def load(self, *, local_files_only=False):
        """Load once, with failed loads remaining retryable and not ready."""
        with self._load_lock:
            if self.ready:
                return
            try:
                import torch
                from huggingface_hub import snapshot_download
                from transformers import WhisperForConditionalGeneration, WhisperProcessor

                # Load the snapshot path directly: Transformers 4.56 otherwise
                # probes a remote custom_generate file even with local-only set.
                source = snapshot_download(
                    MODEL_ID, cache_dir=self.cache_dir, local_files_only=True,
                ) if local_files_only else MODEL_ID
                processor = WhisperProcessor.from_pretrained(
                    source, cache_dir=self.cache_dir, local_files_only=local_files_only,
                )
                model = WhisperForConditionalGeneration.from_pretrained(
                    source, cache_dir=self.cache_dir, local_files_only=local_files_only,
                    use_safetensors=True,
                ).to(device="cpu", dtype=torch.float32)
                model.eval()
            except Exception as error:
                raise ServiceUnavailable("The transcription model could not be loaded.") from error
            self._processor = processor
            self._model = model

    def transcribe(self, path):
        if not self.ready:
            raise ServiceUnavailable("The transcription model is not ready.")
        if not self._inference_lock.acquire(blocking=False):
            raise ServiceBusy("The transcription service is processing another recording.")
        try:
            audio = decode_audio(path, self.max_duration_seconds)
            return self._generate(audio.samples)
        finally:
            self._inference_lock.release()

    def _generate(self, samples):
        import torch

        long_form = len(samples) > 30 * SAMPLE_RATE
        inputs = self._processor(
            samples, sampling_rate=SAMPLE_RATE, return_tensors="pt",
            truncation=False, padding="longest" if long_form else "max_length",
            return_attention_mask=True,
        )
        with torch.inference_mode():
            tokens = self._model.generate(
                **inputs, task="transcribe", language=None,
                return_timestamps=long_form, do_sample=False,
            )
        return self._processor.batch_decode(tokens, skip_special_tokens=True)[0].strip()


@lru_cache(maxsize=None)
def get_transcriber(cache_dir, max_duration_seconds=600):
    """Share one service for app factories using the same process configuration."""
    return WhisperTranscriber(cache_dir, max_duration_seconds)
