"""
Estructuras de datos de sesión. Sin dependencias de ML.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Literal, Optional

SemaforoColor = Literal["verde", "amarillo", "rojo"]


@dataclass
class ToneResult:
    texto_original: str
    emocion: str            # etiqueta devuelta por pysentimiento (joy, anger, sadness…)
    confianza: float        # 0.0-1.0
    semaforo: SemaforoColor
    consejo: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SessionState:
    scenario_id: str = ""
    role_id: str = ""
    # messages en formato Ollama: [{"role": "system"|"user"|"assistant", "content": "..."}]
    messages: List[Dict[str, str]] = field(default_factory=list)
    tone_history: List[ToneResult] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    turn_count: int = 0
    active: bool = False  # True cuando hay una sesión en curso

    def reset(self) -> None:
        self.scenario_id = ""
        self.role_id = ""
        self.messages = []
        self.tone_history = []
        self.started_at = datetime.now().isoformat()
        self.turn_count = 0
        self.active = False

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})
        self.turn_count += 1

    def add_assistant_message(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def add_tone_result(self, result: ToneResult) -> None:
        self.tone_history.append(result)

    @property
    def last_tone(self) -> Optional[ToneResult]:
        return self.tone_history[-1] if self.tone_history else None
