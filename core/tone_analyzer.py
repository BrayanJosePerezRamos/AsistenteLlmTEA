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

# Emociones que pertenecen a cada color (para la lógica de probabilidades acumuladas)
_ROJO_EMOTIONS    = {"anger", "disgust"}
_AMARILLO_EMOTIONS = {"fear", "sadness", "surprise"}

# Umbrales: si la suma de probabilidades de un color supera el umbral,
# se usa ese color aunque "others"/"joy" sea el top individual.
_UMBRAL_ROJO     = 0.07   # calibrado con datos reales: neutros ~0.02, insultos ~0.08+
_UMBRAL_AMARILLO = 0.20


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
            emocion_top = str(result.output).lower()
            # Normalizar claves de probas a minúsculas para comparaciones seguras
            probas = {k.lower(): float(v) for k, v in result.probas.items()} if result.probas else {}

            print(f"[ToneAnalyzer] '{texto[:50]}' → top={emocion_top} | {probas}")

            # Probabilidad acumulada por color
            p_rojo     = sum(probas.get(e, 0.0) for e in _ROJO_EMOTIONS)
            p_amarillo = sum(probas.get(e, 0.0) for e in _AMARILLO_EMOTIONS)

            # Elegir emoción representativa según umbrales
            if p_rojo >= _UMBRAL_ROJO:
                emocion = max(_ROJO_EMOTIONS, key=lambda e: probas.get(e, 0.0))
            elif p_amarillo >= _UMBRAL_AMARILLO:
                emocion = max(_AMARILLO_EMOTIONS, key=lambda e: probas.get(e, 0.0))
            else:
                emocion = emocion_top

            confianza = probas.get(emocion, 0.5)

        except Exception as e:
            print(f"[ToneAnalyzer] Error en predict(): {e}")
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
