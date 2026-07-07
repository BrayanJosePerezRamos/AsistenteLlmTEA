"""
Pestaña de Historia Social (RF4).
Muestra el resumen generado al finalizar la sesión.
"""

import gradio as gr

from core.session import SessionState
from ui.components import render_semaforo_resumen, render_esquema_carol_gray


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

        # Botón deshabilitado al inicio: solo se activa cuando hay una
        # sesión válida (≥3 mensajes). El estado se cambia desde
        # tab_chat.on_end() / on_start() / on_reset() via wiring en app.py.
        generate_btn = gr.Button(
            "Generar Historia Social",
            variant="primary",
            size="lg",
            interactive=False,
            elem_id="generate-historia-btn",
        )

        with gr.Group(visible=False) as result_group:
            # El esquema Carol Gray (3 paneles + resumen semáforo)
            # sustituye a las antiguas secciones Markdown separadas
            # + Image. Es un único HTML estructurado y accesible.
            esquema_html = gr.HTML()

            # Campos individuales (descripcion/perspectiva/directiva/
            # resumen) se mantienen ocultos por compatibilidad con el
            # wiring actual — sus valores van DENTRO del esquema HTML.
            descripcion_md = gr.Markdown(visible=False)
            perspectiva_md = gr.Markdown(visible=False)
            directiva_md = gr.Markdown(visible=False)
            resumen_md = gr.Markdown(visible=False)

            gr.Markdown("### 🔊 Narración")
            narration_audio = gr.Audio(
                label="Escuchar Historia Social",
                interactive=False,
                autoplay=False,
            )

        status_md = gr.Markdown(
            "_Termina una sesión de práctica para habilitar este botón._"
        )
        progress_bar = gr.Progress()

        # ----------------------------------------------------------------
        # on_generate yields tuplas con el botón como ÚLTIMO output,
        # para poder deshabilitarlo durante la generación y restaurarlo
        # al final (incluso en caso de error). El wiring en app.py incluye
        # generate_btn como output.
        _BTN_BUSY = gr.update(value="⏳ Generando…", interactive=False)
        _BTN_IDLE = gr.update(value="Generar Historia Social", interactive=True)

        # Orden de outputs (debe coincidir con el wiring en app.py):
        # result_group, descripcion_md, perspectiva_md, directiva_md,
        # resumen_md, narration_audio, esquema_html, status_md, generate_btn
        def on_generate(session_state: SessionState, progress=gr.Progress()):
            """Callback de «Generar Historia Social».

            Valida que la sesión tenga suficientes turnos, invoca al
            :class:`~core.historia_social.HistoriaSocialGenerator`, renderiza
            el esquema Carol Gray y actualiza el estado del botón (ocupado
            durante la generación, restaurado al terminar aunque falle).

            Es un generador que hace ``yield`` de tuplas alineadas con el
            wiring de ``app.py``.

            Args:
                session_state: estado de sesión compartido con la pestaña de chat.
                progress: barra de progreso inyectada por Gradio.
            """
            if historia_generator is None:
                yield (
                    gr.update(visible=False),
                    "", "", "", "",  # campos legacy ocultos
                    None,            # narration_audio
                    "",              # esquema_html
                    "⚠️ El generador de Historia Social no está disponible.",
                    _BTN_IDLE,
                )
                return

            # session_state es None al inicio (gr.State(value=None)) y solo se
            # rellena tras "Iniciar sesión" en la pestaña de chat.
            if session_state is None or not session_state.messages or len(session_state.messages) < 3:
                yield (
                    gr.update(visible=False),
                    "", "", "", "", None, "",
                    "⚠️ La sesión no tiene suficientes turnos. Practica al menos 2 intercambios.",
                    _BTN_IDLE,
                )
                return

            # Botón ocupado mientras se genera
            yield (
                gr.update(visible=False),
                "", "", "", "", None, "",
                "⏳ Generando Historia Social…",
                _BTN_BUSY,
            )

            try:
                historia = historia_generator.generar(
                    session_state,
                    progress_callback=lambda msg, pct: progress(pct, desc=msg),
                )
                esquema = render_esquema_carol_gray(historia)
                resumen_texto = render_semaforo_resumen(historia.resumen_semaforo)

                yield (
                    gr.update(visible=True),
                    historia.descripcion,
                    historia.perspectiva,
                    historia.directiva,
                    resumen_texto,
                    historia.audio_path or None,
                    esquema,
                    "Historia Social generada correctamente.",
                    _BTN_IDLE,
                )
            except Exception as e:
                yield (
                    gr.update(visible=False),
                    "", "", "", "", None, "",
                    f"⚠️ Error al generar la Historia Social: {e}",
                    _BTN_IDLE,
                )

        # ---- Wiring ----
        # session_state se pasa desde app.py como input externo
        # (se conecta en app.py tras construir ambas pestañas)

    # Mantenemos la tupla de retorno con los mismos elementos para no
    # romper el wiring de app.py. illustration_img ya no existe —
    # devolvemos esquema_html en su posición.
    return (
        tab, generate_btn, result_group,
        descripcion_md, perspectiva_md, directiva_md, resumen_md,
        narration_audio, esquema_html, status_md, on_generate,
    )
