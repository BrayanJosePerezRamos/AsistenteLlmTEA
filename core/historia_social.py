"""
Orquestador de la Historia Social (RF4).
Coordina:
  1. Generación de texto (LLM, Carol Gray)
  2. Síntesis de audio (TTS, Piper)
  3. Esquema visual estructurado (HTML/SVG, sin modelo IA)

NOTA: la antigua generación de imagen con Tiny-SD ha sido reemplazada
por un esquema visual construido en código (ver ui.components.
render_esquema_carol_gray). El swap de VRAM ya no es necesario porque
no hay ningún modelo de imagen en juego.
"""

import json
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from config.scenarios import get_scenario, get_role
from config.prompts import build_historia_prompt, format_conversation_for_prompt
from core.session import SessionState


@dataclass
class HistoriaSocial:
    scenario_nombre: str
    role_nombre: str
    fecha: str

    descripcion: str
    perspectiva: str
    directiva: str

    texto_completo: str
    audio_path: str
    # imagen_path se mantiene por compatibilidad con código anterior,
    # pero siempre vacío. El nuevo visual es esquema_html generado en
    # ui.components.render_esquema_carol_gray() desde esta dataclass.
    imagen_path: str = ""

    resumen_semaforo: Dict[str, int] = field(default_factory=dict)
    num_turnos: int = 0


class HistoriaSocialGenerator:
    """
    Genera la Historia Social completa al finalizar una sesión.

    Args:
        llm: LLMEngine
        tts: TTSEngine
        image_gen: ImageGenEngine
        tone_analyzer: ToneAnalyzer (para el resumen del semáforo)
    """

    def __init__(self, llm, tts, image_gen, tone_analyzer):
        self.llm = llm
        self.tts = tts
        self.image_gen = image_gen
        self.tone_analyzer = tone_analyzer

    def generar(
        self,
        session_state: SessionState,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> HistoriaSocial:
        """
        Genera la Historia Social completa.

        Args:
            session_state: Estado de la sesión finalizada.
            progress_callback: Función opcional (mensaje, porcentaje) para la UI.

        Returns:
            HistoriaSocial con todos los campos completados.
        """
        from datetime import datetime

        def _progress(msg: str, pct: float) -> None:
            if progress_callback:
                progress_callback(msg, pct)

        scenario = get_scenario(session_state.scenario_id)
        role = get_role(session_state.role_id)

        # ---- Paso 1: Generar texto (LLM) ----
        _progress("Generando texto de la Historia Social…", 0.1)
        texto_secciones = self._generar_texto(session_state, scenario, role)

        descripcion = texto_secciones.get("descripcion", "No disponible.")
        perspectiva = texto_secciones.get("perspectiva", "No disponible.")
        directiva = texto_secciones.get("directiva", "No disponible.")

        texto_completo = (
            f"Descripción. {descripcion} "
            f"Perspectiva. {perspectiva} "
            f"Directiva. {directiva}"
        )

        # ---- Paso 2: TTS ----
        _progress("Sintetizando narración de audio…", 0.45)
        audio_path = ""
        if self.tts is not None:
            try:
                tts_result = self.tts.sintetizar_historia(texto_completo)
                audio_path = tts_result.audio_path if tts_result.exito else ""
            except Exception:
                audio_path = ""

        # ---- Paso 3: Resumen del semáforo ----
        # (Antes había un paso "Generar imagen Tiny-SD" con swap VRAM.
        #  Reemplazado por esquema visual HTML construido en la UI a
        #  partir de esta misma dataclass — más rápido y sin "imágenes
        #  raras".)
        _progress("Calculando resumen del semáforo social…", 0.9)
        resumen_semaforo: Dict[str, int] = {"verde": 0, "amarillo": 0, "rojo": 0}
        if self.tone_analyzer is not None:
            resumen_semaforo = self.tone_analyzer.analizar_historial(session_state.tone_history)

        _progress("Historia Social completada.", 1.0)

        return HistoriaSocial(
            scenario_nombre=scenario["nombre"],
            role_nombre=role["nombre"],
            fecha=datetime.now().strftime("%d/%m/%Y %H:%M"),
            descripcion=descripcion,
            perspectiva=perspectiva,
            directiva=directiva,
            texto_completo=texto_completo,
            audio_path=audio_path,
            imagen_path="",
            resumen_semaforo=resumen_semaforo,
            num_turnos=session_state.turn_count,
        )

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _generar_texto(
        self, session_state: SessionState, scenario: dict, role: dict
    ) -> Dict[str, str]:
        """Usa el LLM para generar las tres secciones de Carol Gray como JSON."""
        conversation_text = format_conversation_for_prompt(session_state.messages)
        prompt_content = build_historia_prompt(scenario, role, conversation_text)

        messages = [{"role": "user", "content": prompt_content}]

        try:
            raw = self.llm.chat_once(messages, format_json=True)
            parsed = json.loads(raw)
            # Validar que las claves esperadas están presentes
            if all(k in parsed for k in ("descripcion", "perspectiva", "directiva")):
                return parsed
        except (json.JSONDecodeError, Exception):
            pass

        # Fallback si el modelo no devolvió JSON válido
        return {
            "descripcion": "La sesión de práctica no pudo ser analizada correctamente.",
            "perspectiva": "No disponible.",
            "directiva": "Inténtalo de nuevo con una sesión más larga.",
        }

    # Método _generar_imagen_con_swap eliminado — sustituido por el
    # esquema visual HTML generado en ui.components.render_esquema_carol_gray
    # que se construye desde la propia dataclass HistoriaSocial.
