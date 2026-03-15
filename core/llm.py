"""
Wrapper sobre el cliente Python de Ollama.
Gestiona streaming de chat y el ciclo de vida del modelo en VRAM.
"""

import threading
from typing import Iterator, List, Dict, Optional

import ollama


class LLMEngine:
    """
    Singleton reutilizable para interactuar con Ollama.

    Atributos públicos:
        vram_lock: threading.Lock compartido con ImageGenEngine para
                   garantizar que LLM e imagen nunca ocupan VRAM a la vez.
    """

    def __init__(
        self,
        model_name: str = "qwen2.5:1.5b",
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
        with self.vram_lock:
            try:
                stream = ollama.chat(
                    model=self.model_name,
                    messages=messages,
                    stream=True,
                    keep_alive=self.keep_alive,
                    options={"num_predict": self.max_tokens},
                )
                for chunk in stream:
                    token = chunk["message"]["content"]
                    if token:
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
        except Exception:
            pass

    def is_available(self) -> bool:
        """Comprueba si Ollama está corriendo y el modelo existe."""
        try:
            models = ollama.list()
            names = [m.model for m in models.models]
            return any(self.model_name in n for n in names)
        except Exception:
            return False
