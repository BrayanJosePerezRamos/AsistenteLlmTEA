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
                start_btn = gr.Button("▶ Iniciar sesión", variant="primary", scale=1)

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
                placeholder="Escribe tu respuesta aquí…",
                label="",
                lines=2,
                scale=4,
                interactive=False,
            )
            mic_input = gr.Audio(
                sources=["microphone"],
                type="filepath",
                label="🎤 Micrófono",
                scale=1,
                interactive=False,
            )

        with gr.Row():
            send_btn = gr.Button("Enviar", variant="primary", interactive=False, scale=3)
            end_btn = gr.Button("⏹ Terminar sesión", variant="stop", interactive=False, scale=1)

        status_md = gr.Markdown("_Configura un escenario y pulsa **Iniciar sesión** para comenzar._")

        # ================================================================
        # Callbacks
        # ================================================================

        def on_scenario_change(scenario_id):
            choices = role_choices_for_scenario(scenario_id)
            default_role = choices[0][1]
            preview = _scenario_preview(scenario_id, default_role)
            return (
                gr.update(choices=choices, value=default_role),
                preview,
            )

        def on_role_change(scenario_id, role_id):
            return _scenario_preview(scenario_id, role_id)

        def on_start(scenario_id, role_id, state):
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

            # Mensaje de apertura del LLM
            opener_messages = state.messages + [
                {"role": "user", "content": "Hola."}
            ]
            opener = ""
            try:
                for token in llm.chat_stream(opener_messages):
                    opener += token
            except RuntimeError as e:
                opener = f"⚠️ Error al conectar con Ollama: {e}"

            state.messages.append({"role": "user", "content": "Hola."})
            state.add_assistant_message(opener)

            chat_history = [{"role": "assistant", "content": opener}]

            # TTS del opener en background
            audio_path = None
            if tts is not None:
                audio_path = _tts_background(tts, opener, "opener")

            return (
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
            _noop = gr.update()
            if state is None or not state.active:
                yield chat_history, render_semaforo_idle(), gr.update(visible=False), _noop, _noop, state
                return

            # Transcribir audio si viene del micrófono
            if not user_text and audio_path and stt is not None:
                try:
                    user_text = stt.transcribe_or_empty(audio_path)
                except Exception as e:
                    user_text = f"[Error STT: {e}]"

            if not user_text or not user_text.strip():
                if audio_path:
                    err_msg = "❌ No se pudo transcribir el audio. Escribe tu respuesta por texto."
                    chat_history = list(chat_history) + [{"role": "assistant", "content": err_msg}]
                yield chat_history, render_semaforo_idle(), gr.update(visible=False), _noop, gr.update(value=None), state
                return

            user_text = user_text.strip()

            # Mostrar mensaje del usuario de inmediato + limpiar inputs
            chat_history = list(chat_history) + [{"role": "user", "content": user_text}]
            state.add_user_message(user_text)
            yield chat_history, render_semaforo_idle(), gr.update(visible=False), gr.update(value=""), gr.update(value=None), state

            # Análisis de tono (CPU, rápido) — en paralelo al streaming
            tone_result = None
            if tone_analyzer is not None:
                try:
                    tone_result = tone_analyzer.analizar(user_text)
                    state.add_tone_result(tone_result)
                except Exception as e:
                    print(f"[on_send] Error en tone_analyzer: {e}")

            semaforo_html_val = render_semaforo(tone_result)

            # Streaming de la respuesta del LLM
            partial = ""
            chat_history = list(chat_history) + [{"role": "assistant", "content": ""}]
            try:
                for token in llm.chat_stream(state.messages):
                    partial += token
                    chat_history[-1] = {"role": "assistant", "content": partial}
                    yield chat_history, semaforo_html_val, gr.update(visible=False), _noop, _noop, state
            except RuntimeError as e:
                partial = f"⚠️ Error: {e}"
                chat_history[-1] = {"role": "assistant", "content": partial}

            state.add_assistant_message(partial)

            # TTS en background tras finalizar streaming
            audio_val = gr.update(visible=False)
            if tts is not None and partial:
                wav = _tts_background(tts, partial, f"turn_{state.turn_count}")
                if wav:
                    audio_val = gr.update(value=wav, visible=True)

            yield chat_history, semaforo_html_val, audio_val, _noop, _noop, state

        def on_end(state, chat_history):
            if state is None:
                state = SessionState()
            state.active = False
            return (
                state,
                chat_history,
                gr.update(interactive=False),  # text_input
                gr.update(interactive=False),  # mic_input
                gr.update(interactive=False),  # send_btn
                gr.update(interactive=False),  # end_btn
                gr.update(interactive=True),   # start_btn
                "_Sesión finalizada. Ve a la pestaña **Historia Social** para ver el resumen._",
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

    return tab, session_state


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
