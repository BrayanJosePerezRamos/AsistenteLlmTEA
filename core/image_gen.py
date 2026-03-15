"""
Generación de imágenes con Segmind/tiny-sd (modelo de difusión ligero).
Se carga SOLO cuando es necesario (Historia Social) y se descarga inmediatamente
después para liberar VRAM. Nunca coexiste con el LLM en VRAM.

Instalación:
    pip install diffusers==0.27.2 accelerate

Uso de VRAM: ~0.8 GB (fp16, con attention_slicing)
"""

import os
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class ImageGenResult:
    imagen_path: str
    prompt_usado: str
    exito: bool
    error: Optional[str] = None


class ImageGenEngine:
    """
    Wrapper de Tiny-SD. Diseñado para carga/descarga dinámica.
    No usar como singleton persistente — cargar, usar y descargar.
    """

    def __init__(
        self,
        model_id: str = "segmind/tiny-sd",
        output_dir: Optional[str] = None,
    ):
        self.model_id = model_id
        self.output_dir = os.path.abspath(
            output_dir or os.path.join(os.path.dirname(__file__), "..", "output")
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self._pipeline = None

    def cargar(self) -> None:
        """
        Carga el pipeline en VRAM (fp16).
        Llamar DESPUÉS de que el LLM haya sido expulsado de VRAM.
        """
        import torch
        from diffusers import DiffusionPipeline

        self._pipeline = DiffusionPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            safety_checker=None,       # Ahorra ~300MB VRAM
            requires_safety_checker=False,
        ).to("cuda")
        self._pipeline.enable_attention_slicing()  # Reduce pico de VRAM ~15-20%

    def descargar(self) -> None:
        """
        Descarga el pipeline de VRAM y libera memoria.
        Llamar SIEMPRE tras generar la imagen.
        """
        import torch
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
            torch.cuda.empty_cache()

    def generar(
        self,
        prompt_en: str,
        nombre_archivo: Optional[str] = None,
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
    ) -> ImageGenResult:
        """
        Genera una ilustración para la Historia Social.

        Args:
            prompt_en: Prompt en inglés (los modelos de difusión funcionan mejor en inglés).
            nombre_archivo: Nombre base del fichero de salida (sin extensión).
            num_inference_steps: 20 pasos es suficiente para tiny-sd.
            guidance_scale: 7.5 es el valor estándar.

        Returns:
            ImageGenResult con .imagen_path apuntando al PNG generado.

        Nota: El pipeline debe estar cargado con cargar() antes de llamar a este método.
        """
        if self._pipeline is None:
            return ImageGenResult(
                imagen_path="", prompt_usado=prompt_en, exito=False,
                error="Pipeline no cargado. Llama a cargar() primero."
            )

        if nombre_archivo is None:
            nombre_archivo = str(uuid.uuid4())[:8]

        output_path = os.path.join(self.output_dir, f"{nombre_archivo}.png")

        try:
            result = self._pipeline(
                prompt=prompt_en,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
            )
            imagen = result.images[0]
            imagen.save(output_path)
            return ImageGenResult(imagen_path=output_path, prompt_usado=prompt_en, exito=True)
        except Exception as exc:
            return ImageGenResult(
                imagen_path="", prompt_usado=prompt_en, exito=False, error=str(exc)
            )

    def is_available(self) -> bool:
        """Comprueba si CUDA está disponible (requisito para este módulo)."""
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False
