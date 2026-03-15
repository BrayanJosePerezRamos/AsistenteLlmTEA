"""
Componentes reutilizables de Gradio y funciones de renderizado HTML.
"""

from typing import Optional
from core.session import SemaforoColor, ToneResult

# ------------------------------------------------------------------
# Semáforo Social — HTML renderizado
# ------------------------------------------------------------------

_SEMAFORO_TEMPLATE = """
<div style="
    padding: 12px 16px;
    border-radius: 10px;
    border: 2px solid {border};
    background: {bg};
    text-align: center;
    font-family: sans-serif;
    min-width: 160px;
">
  <div style="font-size: 2em; margin-bottom: 4px;">{emoji}</div>
  <div style="font-weight: bold; color: {text_color}; font-size: 0.9em;">{titulo}</div>
  <div style="color: #444; font-size: 0.8em; margin-top: 6px; line-height: 1.4;">{consejo}</div>
</div>
"""

_SEMAFORO_IDLE = """
<div style="
    padding: 12px 16px;
    border-radius: 10px;
    border: 2px solid #ccc;
    background: #f8f8f8;
    text-align: center;
    font-family: sans-serif;
    min-width: 160px;
    color: #999;
">
  <div style="font-size: 2em; margin-bottom: 4px;">⚪</div>
  <div style="font-size: 0.85em;">Semáforo social</div>
  <div style="font-size: 0.75em; margin-top: 4px;">Esperando mensaje…</div>
</div>
"""

_SEMAFORO_CONFIG: dict = {
    "verde": {
        "emoji": "🟢",
        "titulo": "Tono adecuado",
        "border": "#28a745",
        "bg": "#d4edda",
        "text_color": "#155724",
    },
    "amarillo": {
        "emoji": "🟡",
        "titulo": "Tono mejorable",
        "border": "#ffc107",
        "bg": "#fff3cd",
        "text_color": "#856404",
    },
    "rojo": {
        "emoji": "🔴",
        "titulo": "Tono brusco",
        "border": "#dc3545",
        "bg": "#f8d7da",
        "text_color": "#721c24",
    },
}


def render_semaforo_idle() -> str:
    return _SEMAFORO_IDLE


def render_semaforo(result: Optional[ToneResult]) -> str:
    if result is None:
        return render_semaforo_idle()
    cfg = _SEMAFORO_CONFIG[result.semaforo]
    return _SEMAFORO_TEMPLATE.format(**cfg, consejo=result.consejo)


# ------------------------------------------------------------------
# Historia Social — HTML de resumen de semáforos
# ------------------------------------------------------------------

def render_semaforo_resumen(resumen: dict) -> str:
    verde = resumen.get("verde", 0)
    amarillo = resumen.get("amarillo", 0)
    rojo = resumen.get("rojo", 0)
    total = verde + amarillo + rojo or 1
    return (
        f"**Resumen del semáforo social:**  "
        f"🟢 {verde} ({verde*100//total}%)  "
        f"🟡 {amarillo} ({amarillo*100//total}%)  "
        f"🔴 {rojo} ({rojo*100//total}%)"
    )
