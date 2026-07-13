"""
Pestaña principal de práctica de escenarios.
Implementa RF1 (selección), RF2 (multimodalidad texto+voz), RF3 (semáforo).
"""

import threading
from typing import Optional

import gradio as gr

from config.scenarios import (
    SCENARIOS,
    ROLES,
    scenario_choices,
    role_choices_for_scenario,
    get_scenario,
    get_role,
)
from config.prompts import build_system_prompt
from core.session import SessionState, ToneResult
from ui.components import render_semaforo, render_semaforo_idle

# Límite duro de caracteres por mensaje. Evita que un texto largo
# (p.ej. pegado por accidente) sature el contexto del LLM o bloquee
# el análisis de tono. ~1500 chars cubre ~300 palabras, mucho más
# que un turno conversacional típico.
_MAX_INPUT_CHARS = 1500


def build_chat_tab(llm, tone_analyzer, stt, tts):
    """
    Construye y devuelve el bloque Gradio de la pestaña de chat.

    Args:
        llm: LLMEngine
        tone_analyzer: ToneAnalyzer (puede ser None si no está instalado)
        stt: STTEngine (puede ser None si no está instalado)
        tts: TTSEngine (puede ser None si no está instalado)

    Returns:
        (gr.Column, gr.State) — el componente y el estado de sesión compartido.
    """
    session_state = gr.State(value=None)  # None evita el crash de JSON schema en Gradio 4.44

    with gr.Column() as tab:

        # ---- Configuración del escenario ----
        with gr.Group():
            gr.Markdown("### Configurar escenario")
            with gr.Row():
                scenario_dd = gr.Dropdown(
                    choices=scenario_choices(),
                    label="Escenario",
                    value=list(SCENARIOS.keys())[0],
                    interactive=True,
                    scale=2,
                )
                role_dd = gr.Dropdown(
                    choices=role_choices_for_scenario(list(SCENARIOS.keys())[0]),
                    label="Rol del interlocutor",
                    value=role_choices_for_scenario(list(SCENARIOS.keys())[0])[0][1],
                    interactive=True,
                    scale=2,
                )
                start_btn = gr.Button("▶  Iniciar sesión", variant="primary", scale=1)

            scenario_desc = gr.Markdown(
                _scenario_preview(list(SCENARIOS.keys())[0], role_choices_for_scenario(list(SCENARIOS.keys())[0])[0][1]),
                visible=True,
            )

        # ---- Chat + semáforo ----
        with gr.Row(equal_height=True):
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    label="Conversación",
                    type="messages",
                    height=420,
                    show_copy_button=True,
                    bubble_full_width=False,
                    elem_id="main-chatbot",
                )
            with gr.Column(scale=1, min_width=180):
                semaforo_html = gr.HTML(
                    value=render_semaforo_idle(),
                    label="Semáforo social",
                )

        # ---- Área de respuesta del bot en audio (TTS, sin autoplay) ----
        bot_audio = gr.Audio(
            label="Escuchar respuesta del interlocutor",
            interactive=False,
            autoplay=False,
            visible=False,
        )

        # ---- Entrada del usuario ----
        with gr.Row():
            text_input = gr.Textbox(
                placeholder="Escribe tu respuesta aquí… (Enter para enviar, Ctrl+Enter para nueva línea)",
                label="",
                lines=2,
                max_lines=8,           # Crece hasta 8 líneas, luego scroll interno
                scale=4,
                interactive=False,
                elem_id="chat-text-input",
            )
            mic_input = gr.Audio(
                sources=["microphone"],
                type="filepath",
                label="◉  Micrófono",
                scale=1,
                interactive=False,
            )

        with gr.Row():
            send_btn = gr.Button("Enviar", variant="primary", interactive=False, scale=3, elem_id="chat-send-btn")
            end_btn = gr.Button("■  Terminar sesión", variant="stop", interactive=False, scale=1)
            reset_btn = gr.Button("↻  Reiniciar", variant="secondary", interactive=True, scale=1, elem_id="chat-reset-btn")

        status_md = gr.Markdown("_Configura un escenario y pulsa **Iniciar sesión** para comenzar._")

        # Cartel desplegable con los atajos de teclado disponibles. Cerrado
        # por defecto para no entorpecer; el usuario lo abre si lo necesita.
        with gr.Accordion("⌨  Atajos y trucos", open=False):
            gr.Markdown(
                "- **Enter** → Enviar mensaje\n"
                "- **Ctrl+Enter** (o **Shift+Enter**) → Insertar salto de línea\n"
                "- **»** junto a cada audio → Alternar reproducción 1× / 1.5×\n"
                "- Los toggles **T+** y **◐** del encabezado se recuerdan entre sesiones"
            )

        # ================================================================
        # Callbacks
        # ================================================================

        def on_scenario_change(scenario_id):
            """Al cambiar de escenario: recarga los roles compatibles y la
            previsualización con el primero de ellos como valor por defecto."""
            choices = role_choices_for_scenario(scenario_id)
            default_role = choices[0][1]
            preview = _scenario_preview(scenario_id, default_role)
            return (
                gr.update(choices=choices, value=default_role),
                preview,
            )

        def on_role_change(scenario_id, role_id):
            """Actualiza la previsualización cuando el usuario elige otro rol."""
            return _scenario_preview(scenario_id, role_id)

        def on_start(scenario_id, role_id, state):
            """Callback de «Iniciar sesión»: configura el estado, pide al LLM
            el mensaje de apertura y activa los controles de chat.

            Es un generador: el mensaje de apertura aparece token a token
            en cuanto el LLM lo emite (la latencia percibida coincide así
            con el primer token del RNF-01) y el TTS se sintetiza después
            de mostrar el texto, sin retrasar su aparición.
            """
            _noop = gr.update()
            if state is None:
                state = SessionState()
            state.reset()
            state.scenario_id = scenario_id
            state.role_id = role_id
            state.active = True

            scenario = get_scenario(scenario_id)
            role = get_role(role_id)
            system_prompt = build_system_prompt(scenario, role)
            state.messages = [{"role": "system", "content": system_prompt}]

            # Feedback inmediato: burbuja vacía y botón de inicio
            # deshabilitado mientras llega el primer token.
            chat_history = [{"role": "assistant", "content": ""}]
            yield (
                state,
                chat_history,
                render_semaforo_idle(),
                gr.update(value=None, visible=False),
                _noop, _noop, _noop, _noop,
                gr.update(interactive=False),  # start_btn
                "_Generando apertura…_",
            )

            # Mensaje de apertura del LLM, en streaming hacia la UI
            opener_messages = state.messages + [
                {"role": "user", "content": "Hola."}
            ]
            opener = ""
            try:
                for token in llm.chat_stream(opener_messages):
                    opener += token
                    chat_history[-1] = {"role": "assistant", "content": opener}
                    yield (
                        state, chat_history,
                        _noop, _noop, _noop, _noop, _noop, _noop, _noop, _noop,
                    )
            except RuntimeError as e:
                opener = f"⚠️ Error al conectar con Ollama: {e}"
                chat_history[-1] = {"role": "assistant", "content": opener}

            state.messages.append({"role": "user", "content": "Hola."})
            state.add_assistant_message(opener)

            # TTS del opener, una vez el texto ya está en pantalla
            audio_path = None
            if tts is not None:
                audio_path = _tts_background(tts, opener, "opener")

            yield (
                state,
                chat_history,
                render_semaforo_idle(),
                gr.update(value=audio_path, visible=audio_path is not None),
                gr.update(interactive=True),   # text_input
                gr.update(interactive=True),   # mic_input
                gr.update(interactive=True),   # send_btn
                gr.update(interactive=True),   # end_btn
                gr.update(interactive=False),  # start_btn
                f"_Sesión activa: **{scenario['nombre']}** con **{role['nombre']}**_",
            )

        def on_send(user_text, audio_path, chat_history, state):
            """Callback de «Enviar»: transcribe audio si procede, analiza el
            tono, invoca al LLM en streaming y añade los turnos al historial.

            Es un generador que hace ``yield`` de tuplas para actualizar la
            UI de forma incremental (mensaje del alumno visible inmediatamente,
            luego el streaming del LLM y por último el audio TTS de la respuesta).
            """
            _noop = gr.update()
            if state is None or not state.active:
                yield chat_history, render_semaforo_idle(), gr.update(visible=False), _noop, _noop, state
                return

            # Transcribir audio si viene del micrófono. Usamos transcribe()
            # directo (no transcribe_or_empty) para diferenciar el motivo
            # del fallo y dar feedback específico al usuario.
            if not user_text and audio_path and stt is not None:
                try:
                    result = stt.transcribe(audio_path)
                    if result.exito:
                        user_text = result.texto
                    else:
                        # Distinguir audio demasiado largo de otros fallos
                        err = (result.error or "").lower()
                        if "demasiado largo" in err:
                            gr.Warning(result.error)
                        else:
                            gr.Warning("No se pudo transcribir el audio. Vuelve a intentarlo o escribe tu respuesta.")
                        yield chat_history, render_semaforo_idle(), gr.update(visible=False), _noop, _noop, state
                        return
                except Exception as exc:
                    print(f"[on_send] Excepción STT: {exc}")
                    gr.Warning("Error al transcribir el audio.")
                    yield chat_history, render_semaforo_idle(), gr.update(visible=False), _noop, _noop, state
                    return

            if not user_text or not user_text.strip():
                yield chat_history, render_semaforo_idle(), gr.update(visible=False), _noop, _noop, state
                return

            user_text = user_text.strip()

            # Validación de longitud — protege LLM y tone_analyzer.
            if len(user_text) > _MAX_INPUT_CHARS:
                gr.Warning(
                    f"Mensaje demasiado largo ({len(user_text)} caracteres). "
                    f"Máximo {_MAX_INPUT_CHARS}."
                )
                yield chat_history, render_semaforo_idle(), gr.update(visible=False), _noop, _noop, state
                return

            # Mostrar mensaje del usuario de inmediato + limpiar inputs
            chat_history = list(chat_history) + [{"role": "user", "content": user_text}]
            state.add_user_message(user_text)
            yield chat_history, render_semaforo_idle(), gr.update(visible=False), gr.update(value=""), gr.update(value=None), state

            # Análisis de tono en un hilo aparte, en paralelo real al
            # streaming del LLM: el semáforo se actualiza en cuanto hay
            # resultado, sin retrasar el primer token de la respuesta.
            tone_holder = {}
            tone_thread = None
            if tone_analyzer is not None:
                def _analizar_tono():
                    try:
                        tone_holder["result"] = tone_analyzer.analizar(user_text)
                    except Exception as e:
                        print(f"[on_send] Error en tone_analyzer: {e}")
                        tone_holder["result"] = None
                tone_thread = threading.Thread(target=_analizar_tono, daemon=True)
                tone_thread.start()
                semaforo_html_val = render_semaforo_idle()  # pendiente de resultado
            else:
                semaforo_html_val = render_semaforo(None)

            tone_pendiente = tone_thread is not None

            def _refrescar_semaforo():
                """Incorpora el resultado del tono cuando el hilo termina."""
                nonlocal semaforo_html_val, tone_pendiente
                if tone_pendiente and "result" in tone_holder:
                    tone_result = tone_holder["result"]
                    if tone_result is not None:
                        state.add_tone_result(tone_result)
                    semaforo_html_val = render_semaforo(tone_result)
                    tone_pendiente = False

            # Streaming de la respuesta del LLM
            partial = ""
            chat_history = list(chat_history) + [{"role": "assistant", "content": ""}]
            try:
                for token in llm.chat_stream(state.messages):
                    partial += token
                    chat_history[-1] = {"role": "assistant", "content": partial}
                    _refrescar_semaforo()
                    yield chat_history, semaforo_html_val, gr.update(visible=False), _noop, _noop, state
            except RuntimeError as e:
                partial = f"⚠️ Error: {e}"
                chat_history[-1] = {"role": "assistant", "content": partial}

            # Garantizar que el resultado del tono queda registrado aunque
            # el streaming haya terminado antes que el análisis.
            if tone_thread is not None:
                tone_thread.join(timeout=5.0)
                _refrescar_semaforo()

            state.add_assistant_message(partial)

            # TTS en background tras finalizar streaming
            audio_val = gr.update(visible=False)
            if tts is not None and partial:
                wav = _tts_background(tts, partial, f"turn_{state.turn_count}")
                if wav:
                    audio_val = gr.update(value=wav, visible=True)

            yield chat_history, semaforo_html_val, audio_val, _noop, _noop, state

        def on_end(state, chat_history):
            """Callback de «Terminar sesión»: desactiva controles de chat,
            reactiva el botón de inicio y muestra el banner que indica al
            usuario que vaya a la pestaña de Historia Social."""
            if state is None:
                state = SessionState()
            state.active = False
            # Mensaje destacado: el JS también detecta este texto para
            # poner el badge ● en la pestaña Historia Social.
            # Color explícito (texto oscuro sobre fondo claro) para que
            # se lea sin importar el tema activo de Gradio.
            banner = (
                "<div class='session-ended-banner' style='"
                "background:#ecfdf5;"
                "color:#064e3b;"
                "border-left:4px solid #10b981;"
                "padding:14px 18px;"
                "border-radius:6px;"
                "font-size:1.05em;"
                "'>"
                "<strong style='color:#064e3b;'>✓ Sesión finalizada.</strong><br>"
                "<span style='color:#064e3b;'>"
                "Ve a la pestaña <strong style='color:#064e3b;'>Historia Social</strong> "
                "(arriba) para generar tu resumen."
                "</span>"
                "</div>"
            )
            return (
                state,
                chat_history,
                gr.update(interactive=False),  # text_input
                gr.update(interactive=False),  # mic_input
                gr.update(interactive=False),  # send_btn
                gr.update(interactive=False),  # end_btn
                gr.update(interactive=True),   # start_btn
                banner,
            )

        def on_reset(state):
            """Vuelve al estado inicial: limpia chat, vacía sesión y
            deja al usuario en la pantalla de selección de escenario."""
            if state is None:
                state = SessionState()
            state.reset()
            return (
                state,
                [],                              # chatbot vacío
                render_semaforo_idle(),          # semáforo a estado idle
                gr.update(value=None, visible=False),  # bot_audio
                gr.update(value="", interactive=False),  # text_input
                gr.update(value=None, interactive=False),  # mic_input
                gr.update(interactive=False),    # send_btn
                gr.update(interactive=False),    # end_btn
                gr.update(interactive=True),     # start_btn
                "_Configura un escenario y pulsa **Iniciar sesión** para comenzar._",
            )

        # ---- Wiring ----
        scenario_dd.change(
            on_scenario_change,
            inputs=[scenario_dd],
            outputs=[role_dd, scenario_desc],
        )
        role_dd.change(
            on_role_change,
            inputs=[scenario_dd, role_dd],
            outputs=[scenario_desc],
        )
        start_btn.click(
            on_start,
            inputs=[scenario_dd, role_dd, session_state],
            outputs=[
                session_state, chatbot, semaforo_html, bot_audio,
                text_input, mic_input, send_btn, end_btn, start_btn, status_md,
            ],
        )
        send_btn.click(
            on_send,
            inputs=[text_input, mic_input, chatbot, session_state],
            outputs=[chatbot, semaforo_html, bot_audio, text_input, mic_input, session_state],
        )
        # Enviar también con Enter en el textbox
        text_input.submit(
            on_send,
            inputs=[text_input, mic_input, chatbot, session_state],
            outputs=[chatbot, semaforo_html, bot_audio, text_input, mic_input, session_state],
        )
        end_btn.click(
            on_end,
            inputs=[session_state, chatbot],
            outputs=[
                session_state, chatbot,
                text_input, mic_input, send_btn, end_btn, start_btn, status_md,
            ],
        )
        reset_btn.click(
            on_reset,
            inputs=[session_state],
            outputs=[
                session_state, chatbot, semaforo_html, bot_audio,
                text_input, mic_input, send_btn, end_btn, start_btn, status_md,
            ],
        )

    # Exponemos start/end/reset_btn para que app.py pueda añadir un
    # .then() que habilite/deshabilite el botón "Generar Historia"
    # de la otra pestaña (wiring cross-tab).
    return tab, session_state, start_btn, end_btn, reset_btn


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _scenario_preview(scenario_id: str, role_id: str) -> str:
    from config.scenarios import SCENARIOS, ROLES
    s = SCENARIOS.get(scenario_id, {})
    r = ROLES.get(role_id, {})
    emoji = r.get("emoji", "")
    dificultad = r.get("dificultad", "")
    return (
        f"**{s.get('nombre', '')}** · {s.get('descripcion', '')}  \n"
        f"Interlocutor: {emoji} **{r.get('nombre', '')}** — "
        f"{r.get('descripcion_corta', '')} _(dificultad: {dificultad})_"
    )


def _tts_background(tts, text: str, name: str) -> Optional[str]:
    """Genera el WAV de TTS en el hilo actual (Gradio ya lo llama desde un thread)."""
    try:
        result = tts.sintetizar(text, name)
        return result.audio_path if result.exito else None
    except Exception:
        return None
