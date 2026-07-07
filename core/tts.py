"""
Motor de Text-to-Speech usando Piper TTS (voces es_ES locales).
Ejecuta en CPU. El modelo ONNX se carga de forma lazy.

Instalación:
    pip install piper-tts onnxruntime

Voces disponibles en models/piper/:
    - es_ES-sharvard-medium.onnx   (22050 Hz, calidad media — VOZ PRINCIPAL)
    - es_ES-mls_9972-low.onnx      (16000 Hz, calidad baja  — fallback ligero)
"""

import os
import wave
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class TTSResult:
    audio_path: str
    duracion_segundos: float
    exito: bool
    error: Optional[str] = None


class TTSEngine:
    """Lazy-loading wrapper de Piper TTS."""

    DEFAULT_MODEL = os.path.join(
        os.path.dirname(__file__), "..", "models", "piper",
        "es_ES-sharvard-medium.onnx"
    )
    FALLBACK_MODEL = os.path.join(
        os.path.dirname(__file__), "..", "models", "piper",
        "es_ES-mls_9972-low.onnx"
    )

    def __init__(
        self,
        modelo_onnx: Optional[str] = None,
        output_dir: Optional[str] = None,
    ):
        self.modelo_onnx = os.path.abspath(modelo_onnx or self.DEFAULT_MODEL)
        self.output_dir = os.path.abspath(
            output_dir or os.path.join(os.path.dirname(__file__), "..", "output")
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self._voice = None

    def _ensure_loaded(self) -> None:
        if self._voice is not None:
            return
        from piper.voice import PiperVoice

        # Intenta el modelo principal; si no existe, usa el fallback
        if not os.path.exists(self.modelo_onnx):
            fallback = os.path.abspath(self.FALLBACK_MODEL)
            if os.path.exists(fallback):
                self.modelo_onnx = fallback
            else:
                raise FileNotFoundError(
                    f"No se encontró ningún modelo Piper en models/piper/.\n"
                    f"Esperados: {os.path.basename(self.DEFAULT_MODEL)} "
                    f"o {os.path.basename(self.FALLBACK_MODEL)}"
                )
        self._voice = PiperVoice.load(self.modelo_onnx)

    def sintetizar(self, texto: str, nombre_archivo: Optional[str] = None) -> TTSResult:
        """
        Sintetiza texto en español a un fichero WAV.

        Args:
            texto: Texto a sintetizar (máx. ~500 chars para uso en tiempo real).
            nombre_archivo: Nombre base del fichero de salida (sin extensión).
                            Si es None, se genera un UUID.

        Returns:
            TTSResult con .audio_path apuntando al WAV generado.
        """
        if not texto or not texto.strip():
            return TTSResult(audio_path="", duracion_segundos=0.0, exito=False,
                             error="Texto vacío.")
        try:
            self._ensure_loaded()
        except FileNotFoundError as e:
            return TTSResult(audio_path="", duracion_segundos=0.0, exito=False,
                             error=str(e))

        if nombre_archivo is None:
            nombre_archivo = str(uuid.uuid4())[:8]

        output_path = os.path.join(self.output_dir, f"{nombre_archivo}.wav")

        try:
            with wave.open(output_path, "wb") as wav_file:
                # synthesize_wav() configura internamente channels/sampwidth/framerate
                # del wave.Wave_write antes de escribir. La API antigua synthesize()
                # exigía hacerlo manualmente y rompía con "channels not specified".
                self._voice.synthesize_wav(texto, wav_file)

            # Calcular duración
            with wave.open(output_path, "rb") as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duracion = frames / float(rate) if rate > 0 else 0.0

            return TTSResult(audio_path=output_path, duracion_segundos=duracion, exito=True)

        except Exception as exc:
            return TTSResult(audio_path="", duracion_segundos=0.0, exito=False,
                             error=str(exc))

    def sintetizar_historia(self, texto_completo: str) -> TTSResult:
        """Sintetiza el texto completo de una Historia Social."""
        return self.sintetizar(texto_completo, "historia_social")

    def is_available(self) -> bool:
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False
