"""
Wrapper sobre el cliente Python de Ollama.
Gestiona streaming de chat y el ciclo de vida del modelo en VRAM.
"""

import threading
import time
from typing import Iterator, List, Dict

import ollama


def _truncate_for_llm(messages: List[Dict[str, str]], max_turns: int = 12) -> List[Dict[str, str]]:
    """Devuelve el system prompt + los últimos `max_turns` mensajes
    user/assistant. NO modifica la lista original — Historia Social
    necesita la conversación completa, solo el LLM recibe la versión
    recortada para evitar degradación del LLM en contextos
    largos y mantener la latencia baja a partir del turno ~7."""
    if not messages:
        return messages
    system = [m for m in messages if m.get("role") == "system"]
    others = [m for m in messages if m.get("role") != "system"]
    return system + others[-max_turns:]


def _estimate_tokens(messages: List[Dict[str, str]]) -> int:
    """Estimación rápida de tokens (chars/4). Solo para log/métricas."""
    return sum(len(m.get("content", "")) for m in messages) // 4


class LLMEngine:
    """
    Singleton reutilizable para interactuar con Ollama.

    Atributos públicos:
        vram_lock: threading.Lock compartido con ImageGenEngine para
                   garantizar que LLM e imagen nunca ocupan VRAM a la vez.
    """

    def __init__(
        self,
        model_name: str = "qwen2.5:3b",
        keep_alive: str = "10m",
        max_tokens: int = 150,
    ):
        self.model_name = model_name
        self.keep_alive = keep_alive
        self.max_tokens = max_tokens
        self.vram_lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # Chat principal
    # ------------------------------------------------------------------

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
    ) -> Iterator[str]:
        """
        Hace streaming de una respuesta del LLM token a token.

        Args:
            messages: Lista de mensajes en formato Ollama.
                      El system prompt debe estar en messages[0].

        Yields:
            Fragmentos de texto (tokens) a medida que llegan.

        Raises:
            RuntimeError: Si Ollama no está disponible o el modelo no existe.
        """
        # Truncar contexto para mantener latencia baja en conversaciones largas
        msgs_llm = _truncate_for_llm(messages)
        tokens_ctx = _estimate_tokens(msgs_llm)
        t0 = time.time()
        first_token_ms = None

        with self.vram_lock:
            try:
                stream = ollama.chat(
                    model=self.model_name,
                    messages=msgs_llm,
                    stream=True,
                    keep_alive=self.keep_alive,
                    options={"num_predict": self.max_tokens},
                )
                for chunk in stream:
                    token = chunk["message"]["content"]
                    if token:
                        if first_token_ms is None:
                            first_token_ms = int((time.time() - t0) * 1000)
                            # Métrica para informe TFG: latencia primer token + tamaño contexto
                            print(
                                f"[LLM] tokens_ctx~{tokens_ctx} "
                                f"(msgs_total={len(messages)}, msgs_enviados={len(msgs_llm)}) "
                                f"first_token_ms={first_token_ms}"
                            )
                        yield token
            except Exception as exc:
                raise RuntimeError(
                    f"Error al comunicarse con Ollama (modelo '{self.model_name}'): {exc}"
                ) from exc

    def chat_once(self, messages: List[Dict[str, str]], format_json: bool = False) -> str:
        """
        Petición de chat sin streaming. Útil para generar la Historia Social.

        Args:
            messages: Lista de mensajes en formato Ollama.
            format_json: Si True, le indica a Ollama que devuelva JSON válido.

        Returns:
            El contenido completo de la respuesta como string.
        """
        with self.vram_lock:
            kwargs = dict(
                model=self.model_name,
                messages=messages,
                stream=False,
                keep_alive=self.keep_alive,
                options={"num_predict": 512},
            )
            if format_json:
                kwargs["format"] = "json"
            try:
                response = ollama.chat(**kwargs)
                return response["message"]["content"]
            except Exception as exc:
                raise RuntimeError(
                    f"Error al comunicarse con Ollama (modelo '{self.model_name}'): {exc}"
                ) from exc

    # ------------------------------------------------------------------
    # Gestión de VRAM
    # ------------------------------------------------------------------

    def evict_from_vram(self) -> None:
        """
        Expulsa el modelo de la VRAM inmediatamente usando keep_alive=0.
        Llamar antes de cargar el modelo de generación de imágenes.

        Este método NO adquiere vram_lock intencionadamente — debe ser llamado
        por el código que ya posee el lock (historia_social.py).
        """
        try:
            ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": " "}],
                stream=False,
                keep_alive=0,
                options={"num_predict": 1},
            )
        except Exception:
            pass  # Si el modelo no estaba cargado, no hay nada que hacer

    def warmup(self) -> None:
        """
        Pre-carga el modelo en VRAM con un prompt trivial.
        Llamar al arrancar la app y tras generar la Historia Social.
        """
        try:
            ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hola"}],
                stream=False,
                keep_alive=self.keep_alive,
                options={"num_predict": 1},
            )
            print(f"[LLM] Modelo '{self.model_name}' cargado en VRAM.")
        except Exception as e:
            print(f"[LLM] Advertencia: no se pudo precargar el modelo '{self.model_name}': {e}")

    def is_available(self) -> bool:
        """Comprueba si Ollama está corriendo y el modelo existe."""
        try:
            models = ollama.list()
            names = [m.model for m in models.models]
            return any(self.model_name in n for n in names)
        except Exception:
            return False
