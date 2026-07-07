"""
Asistente — Simulador multimodal de habilidades sociales (TEA/NEAE).
Punto de entrada principal. Instancia los módulos y lanza la interfaz Gradio.

Uso:
    cd AsistenteTEA
    python app.py

Requisitos previos:
    1. Ollama corriendo con el modelo descargado:
       ollama pull qwen2.5:3b
    2. Modelo de voz Piper descargado en models/piper/ (ver core/tts.py)
    3. Dependencias instaladas:  pip install -r requirements.txt
"""

import os
import sys

# Silenciar warning de onnxruntime sobre detección de GPU en WSL2/headless
# ("GPU device discovery failed"). No afecta funcionalidad — todo va por CPU.
os.environ.setdefault("ORT_LOGGING_LEVEL", "3")

import gradio as gr

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
from core.historia_social import HistoriaSocialGenerator
# core.image_gen eliminado — la antigua generación Tiny-SD producía
# imágenes raras y poco útiles. Sustituida por esquema Carol Gray
# estructurado en ui.components.render_esquema_carol_gray().

from ui.tab_chat import build_chat_tab
from ui.tab_historia import build_historia_tab

# ======================================================================
# Configuración
# ======================================================================

LLM_MODEL = os.environ.get("TEA_LLM_MODEL", "qwen2.5:3b")
STT_MODEL = os.environ.get("TEA_STT_MODEL", "small")

CSS_PATH = os.path.join(os.path.dirname(__file__), "ui", "styles.css")
JS_PATH  = os.path.join(os.path.dirname(__file__), "ui", "scripts.js")

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

historia_generator = HistoriaSocialGenerator(
    llm=llm,
    tts=tts,
    image_gen=None,  # ya no se usa; param mantenido por firma actual
    tone_analyzer=tone_analyzer,
)

print("[Asistente] Módulos listos.")

# ======================================================================
# Construcción de la interfaz Gradio
# ======================================================================

css = open(CSS_PATH).read() if os.path.exists(CSS_PATH) else ""
# El JS debe ser una ÚNICA función arrow `() => {...}`. Gradio la ejecuta
# al cargar la página. El parámetro `head` no sirve para <script> porque
# Gradio lo inyecta con innerHTML y los scripts no se ejecutan así.
js_code = open(JS_PATH).read() if os.path.exists(JS_PATH) else None

with gr.Blocks(
    title="Asistente — Habilidades Sociales",
    theme=gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="green",
        font=gr.themes.GoogleFont("Inter"),
    ),
    css=css,
    js=js_code,
) as demo:

    gr.Markdown(
        "# ❖  Asistente\n"
        "Simulador de habilidades sociales para estudiantes universitarios. "
        "Practica situaciones reales en un entorno seguro y privado."
    )

    # ---- Accesibilidad: toggles globales (sin callback Python) ----
    # Definidos a nivel raíz (fuera de Tabs) para que apliquen en todas
    # las pestañas. JS los lee por elem_id y aplica clases body.*
    # persistidas en localStorage.
    with gr.Row():
        gr.Checkbox(
            label="T+  Texto grande",
            info="Aumenta el tamaño de toda la tipografía",
            value=False,
            interactive=True,
            elem_id="cfg-large-text",
            scale=1,
        )
        gr.Checkbox(
            label="◐  Alto contraste",
            info="Fondo negro + texto amarillo, ideal para baja visión",
            value=False,
            interactive=True,
            elem_id="cfg-high-contrast",
            scale=1,
        )

    with gr.Tabs():
        with gr.Tab("✉  Practicar escenario"):
            chat_col, session_state, start_btn, end_btn, reset_btn = build_chat_tab(
                llm=llm,
                tone_analyzer=tone_analyzer,
                stt=stt,
                tts=tts,
            )

        with gr.Tab("◫  Historia Social"):
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
                    generate_btn,  # se deshabilita durante la generación
                ],
            )

    # ---- Wiring cross-tab: enable/disable de "Generar Historia" ----
    # generate_btn empieza deshabilitado (interactive=False). Se habilita
    # al terminar la sesión y se vuelve a deshabilitar al iniciar/reiniciar.
    end_btn.click(
        lambda: gr.update(interactive=True),
        outputs=[generate_btn],
    )
    start_btn.click(
        lambda: gr.update(interactive=False),
        outputs=[generate_btn],
    )
    reset_btn.click(
        lambda: gr.update(interactive=False),
        outputs=[generate_btn],
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
    import threading
    import time

    # Warmup PARALELO de todos los motores (LLM + STT + TTS + Tone).
    # Antes: LLM síncrono + STT/TTS/Tone lazy en primer turno → suma de
    # tiempos (~10s típico). Ahora: todos cargan a la vez → tiempo total
    # ≈ max(motores). Cada hilo logea su duración para métricas TFG.
    def _warm(name, fn):
        t0 = time.time()
        try:
            fn()
            print(f"[Warmup] {name} OK ({time.time() - t0:.1f}s)")
        except Exception as e:
            print(f"[Warmup] {name} FAIL ({time.time() - t0:.1f}s): {e}")

    warmup_specs = [
        ("LLM",  llm.warmup),
        ("STT",  stt._ensure_loaded),
        ("TTS",  tts._ensure_loaded),
        ("Tone", tone_analyzer._ensure_loaded),
    ]
    print("[Asistente] Precargando motores en paralelo…")
    t_global = time.time()
    threads = [threading.Thread(target=_warm, args=(n, f)) for n, f in warmup_specs]
    for t in threads: t.start()
    for t in threads: t.join()
    print(f"[Asistente] Warmup total: {time.time() - t_global:.1f}s. Abriendo interfaz…")

    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True,
        inbrowser=True,
    )
