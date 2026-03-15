"""
Analizador de tono usando pysentimiento (task="emotion").
Carga el modelo de forma lazy. Ejecuta en CPU.

Mapeo de emociones a semáforo (alineado con psicología TEA):
  anger / disgust  → rojo   (tono brusco/hostil)
  joy / others     → verde  (tono adecuado)
  fear / sadness   → amarillo (emoción válida pero requiere apoyo)
  surprise         → amarillo (puede sorprender al interlocutor)
"""

from typing import Optional
from core.session import ToneResult, SemaforoColor

_EMOTION_TO_SEMAFORO: dict = {
    "anger":   ("rojo",    "Revisa el tono, puede parecer brusco o agresivo."),
    "disgust": ("rojo",    "Revisa el tono, puede parecer despectivo."),
    "joy":     ("verde",   "Tono adecuado, sigue así."),
    "others":  ("verde",   "Tono adecuado, sigue así."),
    "fear":    ("amarillo", "Tranquilo/a, respira y exprésate con calma."),
    "sadness": ("amarillo", "Es válido sentirse así. Expresa tus emociones con calma."),
    "surprise":("amarillo", "Tono adecuado, aunque puede sorprender al interlocutor."),
}


class ToneAnalyzer:
    """Lazy-loading wrapper de pysentimiento."""

    def __init__(self):
        self._analyzer = None

    def _ensure_loaded(self) -> None:
        if self._analyzer is None:
            from pysentimiento import create_analyzer
            self._analyzer = create_analyzer(task="emotion", lang="es")

    def analizar(self, texto: str) -> ToneResult:
        """
        Analiza el tono emocional de un texto en español.

        Args:
            texto: Mensaje del usuario (ya transcrito si vino de audio).

        Returns:
            ToneResult con semáforo y consejo.
        """
        self._ensure_loaded()
        try:
            result = self._analyzer.predict(texto)
            emocion = result.output.lower()
            confianza = float(max(result.probas.values())) if result.probas else 0.5
        except Exception:
            emocion = "others"
            confianza = 0.5

        semaforo, consejo = _EMOTION_TO_SEMAFORO.get(
            emocion, ("verde", "Tono adecuado, sigue así.")
        )

        return ToneResult(
            texto_original=texto,
            emocion=emocion,
            confianza=confianza,
            semaforo=semaforo,
            consejo=consejo,
        )

    def analizar_historial(self, tone_history: list) -> dict:
        """Agrega el historial de tone results en conteos por color."""
        counts: dict = {"verde": 0, "amarillo": 0, "rojo": 0}
        for t in tone_history:
            counts[t.semaforo] = counts.get(t.semaforo, 0) + 1
        return counts

    def is_available(self) -> bool:
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False
