"""
Asistente — Simulador multimodal de habilidades sociales (TEA/NEAE).
Punto de entrada principal. Instancia los módulos y lanza la interfaz Gradio.

Uso:
    cd AsistenteTEA
    python app.py

Requisitos previos:
    1. Ollama corriendo con el modelo descargado:
       ollama pull qwen2.5:1.5b
    2. Modelo de voz Piper descargado en models/piper/ (ver core/tts.py)
    3. Dependencias instaladas:  pip install -r requirements.txt
"""

import os
import sys

import gradio as gr

# ── Hotfix gradio_client 1.3.0 ────────────────────────────────────────────────
# _json_schema_to_python_type() falla con AttributeError cuando schema es un
# booleano Python (True/False), lo que ocurre con additionalProperties:false en
# los schemas de gr.Chatbot(type="messages").
# La función recursiva necesita tolerar schemas no-dict devolviendo "Any".
import gradio_client.utils as _gc_utils
_orig_json_schema_to_python_type = _gc_utils._json_schema_to_python_type
def _safe_json_schema_to_python_type(schema, defs=None):
    if not isinstance(schema, dict):
        return "Any"
    return _orig_json_schema_to_python_type(schema, defs)
_gc_utils._json_schema_to_python_type = _safe_json_schema_to_python_type
# ──────────────────────────────────────────────────────────────────────────────

# Aseguramos que el directorio raíz del proyecto esté en el path
sys.path.insert(0, os.path.dirname(__file__))

from core.llm import LLMEngine
from core.tone_analyzer import ToneAnalyzer
from core.stt import STTEngine
from core.tts import TTSEngine
from core.image_gen import ImageGenEngine
from core.historia_social import HistoriaSocialGenerator

from ui.tab_chat import build_chat_tab
from ui.tab_historia import build_historia_tab

# ======================================================================
# Configuración
# ======================================================================

LLM_MODEL = os.environ.get("TEA_LLM_MODEL", "qwen2.5:1.5b")
STT_MODEL = os.environ.get("TEA_STT_MODEL", "moonshine/tiny")

CSS_PATH = os.path.join(os.path.dirname(__file__), "ui", "styles.css")

# ======================================================================
# Instanciación de módulos (lazy-loading interno)
# ======================================================================

print("[Asistente] Inicializando módulos…")

llm = LLMEngine(model_name=LLM_MODEL)

# Verificar Ollama al arranque
if not llm.is_available():
    print(
        f"[ADVERTENCIA] Ollama no disponible o el modelo '{LLM_MODEL}' no está descargado.\n"
        f"  Ejecuta:  ollama pull {LLM_MODEL}"
    )

tone_analyzer = ToneAnalyzer()
stt = STTEngine(model_name=STT_MODEL)
tts = TTSEngine()
image_gen = None  # Desactivado temporalmente — descomentar para rehabilitar:
# image_gen = ImageGenEngine()

historia_generator = HistoriaSocialGenerator(
    llm=llm,
    tts=tts,
    image_gen=image_gen,
    tone_analyzer=tone_analyzer,
)

print("[Asistente] Módulos listos.")

# ======================================================================
# Construcción de la interfaz Gradio
# ======================================================================

css = open(CSS_PATH).read() if os.path.exists(CSS_PATH) else ""

with gr.Blocks(
    title="Asistente — Habilidades Sociales",
    theme=gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="green",
        font=gr.themes.GoogleFont("Inter"),
    ),
    css=css,
) as demo:

    gr.Markdown(
        "# 🎓 Asistente\n"
        "Simulador de habilidades sociales para estudiantes universitarios. "
        "Practica situaciones reales en un entorno seguro y privado."
    )

    with gr.Tabs():
        with gr.Tab("💬 Practicar escenario"):
            chat_col, session_state = build_chat_tab(
                llm=llm,
                tone_analyzer=tone_analyzer,
                stt=stt,
                tts=tts,
            )

        with gr.Tab("📖 Historia Social"):
            (
                historia_col,
                generate_btn,
                result_group,
                descripcion_md,
                perspectiva_md,
                directiva_md,
                resumen_md,
                narration_audio,
                illustration_img,
                historia_status_md,
                on_generate,
            ) = build_historia_tab(historia_generator)

            # Conectar el botón con la función generadora y el session_state
            # que viene de la pestaña de chat
            generate_btn.click(
                on_generate,
                inputs=[session_state],
                outputs=[
                    result_group,
                    descripcion_md,
                    perspectiva_md,
                    directiva_md,
                    resumen_md,
                    narration_audio,
                    illustration_img,
                    historia_status_md,
                ],
            )

    gr.Markdown(
        "<small>Todos los datos se procesan **localmente** en tu dispositivo. "
        "Ningún mensaje sale de tu ordenador.</small>",
        elem_id="privacy-note",
    )

# ======================================================================
# Lanzamiento
# ======================================================================

if __name__ == "__main__":
    # Warmup del LLM en segundo plano (no bloquea el arranque de la UI)
    import threading
    threading.Thread(target=llm.warmup, daemon=True).start()

    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True,
        inbrowser=True,
    )
