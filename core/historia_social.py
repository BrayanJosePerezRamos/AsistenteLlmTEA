"""
Orquestador de la Historia Social (RF4).
Coordina:
  1. Generación de texto (LLM, Carol Gray)
  2. Síntesis de audio (TTS, Piper)
  3. Generación de imagen (Tiny-SD, con swap de VRAM)

La secuencia de VRAM es:
  Adquirir vram_lock → evictar LLM → cargar Tiny-SD → generar imagen
  → descargar Tiny-SD → liberar vram_lock → [LLM vuelve a cargarse lazy]
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
    imagen_path: str

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

        # ---- Paso 3: Imagen (con swap de VRAM) ----
        _progress("Generando ilustración (intercambiando modelos en VRAM)…", 0.6)
        imagen_path = ""
        if self.image_gen is not None and self.image_gen.is_available():
            imagen_path = self._generar_imagen_con_swap(scenario, role)

        # ---- Paso 4: Resumen del semáforo ----
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
            imagen_path=imagen_path,
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

    def _generar_imagen_con_swap(self, scenario: dict, role: dict) -> str:
        """
        Ejecuta el ciclo completo de swap de VRAM:
        evictar LLM → cargar Tiny-SD → generar → descargar Tiny-SD.

        Devuelve la ruta al PNG generado, o cadena vacía si falla.
        """
        prompt_en = scenario.get("imagen_prompt_en", "university campus, realistic, soft colors")

        # El vram_lock del LLM garantiza exclusividad
        with self.llm.vram_lock:
            # 1. Expulsar LLM (sin lock porque ya lo tenemos)
            self.llm.evict_from_vram()

            # 2. Cargar imagen y generar
            imagen_path = ""
            try:
                self.image_gen.cargar()
                result = self.image_gen.generar(prompt_en, "historia_social_ilustracion")
                imagen_path = result.imagen_path if result.exito else ""
            except Exception:
                imagen_path = ""
            finally:
                # 3. Siempre descargar la imagen, pase lo que pase
                self.image_gen.descargar()

        # El LLM se recargará lazy en la próxima petición de chat
        return imagen_path
