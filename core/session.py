"""
Estructuras de datos de sesión. Sin dependencias de ML.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Literal, Optional

SemaforoColor = Literal["verde", "amarillo", "rojo"]


@dataclass
class ToneResult:
    """Resultado del análisis de tono de un mensaje del alumno.

    Attributes:
        texto_original: texto tal cual lo introdujo el alumno.
        emocion: etiqueta devuelta por pysentimiento
            (``joy``, ``anger``, ``sadness``, ``fear``, ``surprise``,
            ``disgust``, ``others``).
        confianza: probabilidad devuelta por el modelo para ``emocion``,
            en el rango ``[0.0, 1.0]``.
        semaforo: color asignado tras la decisión final del
            :class:`~core.tone_analyzer.ToneAnalyzer`.
        consejo: mensaje breve dirigido al alumno para guiar la reformulación.
        timestamp: marca ISO 8601 del momento en que se registró el análisis.
    """

    texto_original: str
    emocion: str
    confianza: float
    semaforo: SemaforoColor
    consejo: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SessionState:
    """Estado completo de una sesión de práctica.

    Los ``messages`` siguen el formato Ollama
    (``[{"role": "system"|"user"|"assistant", "content": "..."}]``) para
    poder pasarse directamente al motor de LLM.

    Attributes:
        scenario_id: identificador del escenario activo.
        role_id: identificador del rol/interlocutor activo.
        messages: historial completo en formato Ollama (incluye system prompt).
        tone_history: lista de :class:`ToneResult` — un elemento por turno del alumno.
        started_at: marca ISO 8601 del inicio de la sesión.
        turn_count: número de turnos del alumno acumulados.
        active: ``True`` mientras hay una sesión en curso; se pone a
            ``False`` al finalizar o reiniciar.
    """

    scenario_id: str = ""
    role_id: str = ""
    messages: List[Dict[str, str]] = field(default_factory=list)
    tone_history: List[ToneResult] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    turn_count: int = 0
    active: bool = False

    def reset(self) -> None:
        """Vacía el estado y lo devuelve a la configuración inicial.

        Se usa al pulsar «Reiniciar» y al arrancar una nueva sesión.
        """
        self.scenario_id = ""
        self.role_id = ""
        self.messages = []
        self.tone_history = []
        self.started_at = datetime.now().isoformat()
        self.turn_count = 0
        self.active = False

    def add_user_message(self, content: str) -> None:
        """Añade un mensaje del alumno al historial e incrementa ``turn_count``.

        Args:
            content: texto tal cual lo introdujo el alumno.
        """
        self.messages.append({"role": "user", "content": content})
        self.turn_count += 1

    def add_assistant_message(self, content: str) -> None:
        """Añade una respuesta del interlocutor al historial.

        Args:
            content: texto devuelto por el LLM.
        """
        self.messages.append({"role": "assistant", "content": content})

    def add_tone_result(self, result: ToneResult) -> None:
        """Registra el resultado del análisis de tono del último turno.

        Args:
            result: :class:`ToneResult` producido por el
                :class:`~core.tone_analyzer.ToneAnalyzer`.
        """
        self.tone_history.append(result)

    @property
    def last_tone(self) -> Optional[ToneResult]:
        """Devuelve el último :class:`ToneResult`, o ``None`` si no hay ninguno."""
        return self.tone_history[-1] if self.tone_history else None
