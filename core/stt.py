"""
Motor de Speech-to-Text usando Moonshine (useful-sensors/moonshine).
Python puro, sin dependencias de cuDNN. Ejecuta en CPU.

Instalación:
    pip install moonshine-onnx

Modelos disponibles: "moonshine/tiny" o "moonshine/base"
"""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class TranscriptionResult:
    texto: str
    exito: bool
    error: Optional[str] = None


class STTEngine:
    """Lazy-loading wrapper de Moonshine ONNX."""

    def __init__(self, model_name: str = "moonshine/tiny"):
        """
        Args:
            model_name: "moonshine/tiny" (más rápido) o "moonshine/base" (más preciso).
                        Moonshine está optimizado para inglés, pero funciona con español
                        en frases cortas y claras (suficiente para este caso de uso).
        """
        self._model = None
        self.model_name = model_name

    def _ensure_loaded(self) -> None:
        if self._model is None:
            from moonshine_onnx import MoonshineOnnxModel
            self._model = MoonshineOnnxModel(model_name=self.model_name)

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        """
        Transcribe un fichero de audio a texto.

        Args:
            audio_path: Ruta absoluta al fichero WAV/MP3.
                        Gradio proporciona esto desde gr.Audio(type="filepath").

        Returns:
            TranscriptionResult con .texto.
        """
        if not audio_path or not os.path.exists(audio_path):
            return TranscriptionResult(texto="", exito=False, error="Fichero de audio no encontrado.")

        try:
            self._ensure_loaded()
            import numpy as np
            import soundfile as sf

            audio_data, sample_rate = sf.read(audio_path, dtype="float32")

            # Moonshine espera mono a 16 kHz
            if audio_data.ndim > 1:
                audio_data = audio_data.mean(axis=1)

            if sample_rate != 16000:
                audio_data = _resample(audio_data, sample_rate, 16000)

            tokens = self._model.generate(audio_data[np.newaxis, :])
            texto = self._model.tokenizer.decode_batch(tokens)[0].strip()

            return TranscriptionResult(texto=texto, exito=True)

        except Exception as exc:
            return TranscriptionResult(texto="", exito=False, error=str(exc))

    def transcribe_or_empty(self, audio_path: Optional[str]) -> str:
        """
        Conveniencia: devuelve string vacío si audio_path es None o hay error.
        """
        if not audio_path:
            return ""
        result = self.transcribe(audio_path)
        return result.texto if result.exito else ""

    def is_available(self) -> bool:
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False


def _resample(audio: "np.ndarray", orig_sr: int, target_sr: int) -> "np.ndarray":
    """Remuestreo simple mediante interpolación lineal (sin scipy)."""
    import numpy as np
    ratio = target_sr / orig_sr
    new_length = int(len(audio) * ratio)
    x_old = np.linspace(0, 1, len(audio))
    x_new = np.linspace(0, 1, new_length)
    return np.interp(x_new, x_old, audio).astype(np.float32)
