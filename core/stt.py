"""
Motor de Speech-to-Text usando faster-whisper (CTranslate2).
Optimizado para inferencia en CPU con cuantización int8.

Modelos disponibles: "tiny", "base", "small", "medium"
  "tiny"   — más rápido, menor precisión (~72 MB)
  "small"  — buen equilibrio precisión/velocidad (~460 MB, int8)
  "medium" — más preciso, más lento (~1.5 GB, int8)

faster-whisper gestiona internamente la decodificación de audio
(vía la librería 'av'), por lo que no necesita ffmpeg, soundfile
ni numpy para leer ficheros de audio.
"""

from dataclasses import dataclass
from typing import Optional
import os
import wave

# Límite duro de duración del audio entrante. Un audio largo bloquea el
# hilo de inferencia y consume mucha RAM/CPU. Para uso conversacional
# 60 s cubre con margen un turno típico (frases de 10–20 s).
_MAX_AUDIO_SECONDS = 60.0


@dataclass
class TranscriptionResult:
    texto: str
    exito: bool
    error: Optional[str] = None


def _audio_duration_seconds(path: str) -> Optional[float]:
    """Devuelve la duración del WAV en segundos leyendo solo la cabecera.
    None si no es WAV o no se puede leer (no aborta — el caller decide).
    Gradio mic produce WAV; otros formatos pasan sin chequeo de duración."""
    try:
        with wave.open(path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate <= 0:
                return None
            return frames / float(rate)
    except (wave.Error, EOFError, FileNotFoundError):
        return None


class STTEngine:
    """Lazy-loading wrapper de faster-whisper (CTranslate2)."""

    def __init__(self, model_name: str = "small"):
        self._model = None
        self.model_name = model_name

    def _ensure_loaded(self) -> None:
        """Carga el modelo en memoria la primera vez que se necesita.

        - device="cpu": ejecución íntegra en CPU (sin CUDA).
        - compute_type="int8": cuantización de pesos para reducir
          uso de memoria y acelerar la inferencia en CPU.
        """
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8",
            )

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        """
        Transcribe un fichero de audio a texto.

        Args:
            audio_path: Ruta absoluta al fichero de audio (WAV, MP3, etc.).
                        Gradio proporciona esto desde gr.Audio(type="filepath").

        Returns:
            TranscriptionResult con .texto y .exito.
        """
        if not audio_path or not os.path.exists(audio_path):
            return TranscriptionResult(
                texto="", exito=False, error="Fichero de audio no encontrado."
            )

        # Chequeo de duración antes de cargar el modelo: si el audio es
        # demasiado largo, no merece la pena ni iniciar la transcripción.
        dur = _audio_duration_seconds(audio_path)
        if dur is not None and dur > _MAX_AUDIO_SECONDS:
            return TranscriptionResult(
                texto="", exito=False,
                error=f"Audio demasiado largo ({dur:.0f}s). Máximo {int(_MAX_AUDIO_SECONDS)}s.",
            )

        try:
            self._ensure_loaded()

            # faster-whisper acepta directamente la ruta del fichero;
            # decodifica el audio internamente con la librería 'av'.
            # beam_size=5 mejora la precisión a costa de algo más de tiempo.
            segments, _info = self._model.transcribe(
                audio_path,
                language="es",
                beam_size=5,
            )

            # Los segmentos se generan de forma lazy (generador);
            # los recorremos para construir el texto completo.
            texto = " ".join(seg.text for seg in segments).strip()
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
        if not result.exito:
            print(f"[STT] Transcripción fallida: {result.error}")
        return result.texto if result.exito else ""

    def is_available(self) -> bool:
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False
