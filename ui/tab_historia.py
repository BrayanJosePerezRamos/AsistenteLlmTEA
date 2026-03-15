"""
Pestaña de Historia Social (RF4).
Muestra el resumen generado al finalizar la sesión.
"""

import gradio as gr

from core.session import SessionState
from ui.components import render_semaforo_resumen


def build_historia_tab(historia_generator):
    """
    Construye y devuelve el bloque Gradio de la pestaña Historia Social.

    Args:
        historia_generator: HistoriaSocialGenerator (puede ser None si no está disponible)

    Returns:
        gr.Column
    """
    with gr.Column() as tab:
        gr.Markdown(
            "## Historia Social\n"
            "Genera un resumen estructurado de tu ensayo interactivo "
            "siguiendo el método de Carol Gray."
        )

        generate_btn = gr.Button(
            "Generar Historia Social",
            variant="primary",
            size="lg",
        )

        with gr.Group(visible=False) as result_group:
            gr.Markdown("### 📋 Descripción")
            descripcion_md = gr.Markdown()

            gr.Markdown("### 💭 Perspectiva")
            perspectiva_md = gr.Markdown()

            gr.Markdown("### ✅ Directiva")
            directiva_md = gr.Markdown()

            gr.Markdown("---")
            resumen_md = gr.Markdown()

            gr.Markdown("### 🔊 Narración")
            narration_audio = gr.Audio(
                label="Escuchar Historia Social",
                interactive=False,
                autoplay=False,
            )

            gr.Markdown("### 🖼️ Ilustración")
            illustration_img = gr.Image(
                label="Ilustración del escenario",
                interactive=False,
            )

        status_md = gr.Markdown(
            "_Termina una sesión de práctica para habilitar este botón._"
        )
        progress_bar = gr.Progress()

        # ----------------------------------------------------------------
        def on_generate(session_state: SessionState, progress=gr.Progress()):
            if historia_generator is None:
                yield (
                    gr.update(visible=False),
                    "", "", "", "", None, None,
                    "⚠️ El generador de Historia Social no está disponible.",
                )
                return

            if not session_state.messages or len(session_state.messages) < 3:
                yield (
                    gr.update(visible=False),
                    "", "", "", "", None, None,
                    "⚠️ La sesión no tiene suficientes turnos. Practica al menos 2 intercambios.",
                )
                return

            yield (
                gr.update(visible=False),
                "", "", "", "", None, None,
                "⏳ Generando Historia Social…",
            )

            try:
                historia = historia_generator.generar(
                    session_state,
                    progress_callback=lambda msg, pct: progress(pct, desc=msg),
                )
                resumen_texto = render_semaforo_resumen(historia.resumen_semaforo)

                yield (
                    gr.update(visible=True),
                    historia.descripcion,
                    historia.perspectiva,
                    historia.directiva,
                    resumen_texto,
                    historia.audio_path or None,
                    historia.imagen_path or None,
                    "Historia Social generada correctamente.",
                )
            except Exception as e:
                yield (
                    gr.update(visible=False),
                    "", "", "", "", None, None,
                    f"⚠️ Error al generar la Historia Social: {e}",
                )

        # ---- Wiring ----
        # session_state se pasa desde app.py como input externo
        # (se conecta en app.py tras construir ambas pestañas)

    return tab, generate_btn, result_group, descripcion_md, perspectiva_md, directiva_md, resumen_md, narration_audio, illustration_img, status_md, on_generate
