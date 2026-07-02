"""
Componentes reutilizables de Gradio y funciones de renderizado HTML.
"""

from typing import Optional
from core.session import SemaforoColor, ToneResult

# ------------------------------------------------------------------
# Semáforo Social — HTML renderizado
# ------------------------------------------------------------------
#
# Accesibilidad:
#   - role="status" + aria-live="polite" → los lectores de pantalla
#     anuncian automáticamente el cambio de color al usuario.
#   - aria-label completo con la descripción → para usuarios que no
#     pueden ver los emojis (modo solo-texto) o tienen daltonismo.
#   - Glyph alternativo (✓/⚠/✗) junto al emoji de color: no se depende
#     SOLO del color ni SOLO del emoji circular para distinguir estado.
#   - data-tooltip → al hacer hover muestra explicación detallada
#     (estilado en styles.css con [data-tooltip]:hover::after).

_SEMAFORO_TEMPLATE = """
<div role="status" aria-live="polite"
     aria-label="{aria_label}"
     data-tooltip="{tooltip}"
     style="
    padding: 12px 16px;
    border-radius: 10px;
    border: 3px solid {border};
    background: {bg};
    text-align: center;
    font-family: sans-serif;
    min-width: 160px;
    position: relative;
">
  <div style="font-size: 2em; margin-bottom: 4px; color: {text_color}; font-weight: bold;" aria-hidden="true">{emoji} {glyph}</div>
  <div style="font-weight: bold; color: {text_color}; font-size: 0.9em;">{titulo}</div>
  <div style="color: #444; font-size: 0.8em; margin-top: 6px; line-height: 1.4;">{consejo}</div>
</div>
"""

_SEMAFORO_IDLE = """
<div role="status" aria-live="polite"
     aria-label="Semáforo social: en espera del primer mensaje"
     data-tooltip="El semáforo evaluará el tono de cada mensaje que envíes."
     style="
    padding: 12px 16px;
    border-radius: 10px;
    border: 2px dashed #aaa;
    background: #f8f8f8;
    text-align: center;
    font-family: sans-serif;
    min-width: 160px;
    color: #777;
    position: relative;
">
  <div style="font-size: 2em; margin-bottom: 4px;" aria-hidden="true">⚪</div>
  <div style="font-size: 0.85em;">Semáforo social</div>
  <div style="font-size: 0.75em; margin-top: 4px;">Esperando mensaje…</div>
</div>
"""

# Glyph adicional para que usuarios daltónicos puedan distinguir el
# color por la forma además del emoji. ✓ verde, ⚠ amarillo, ✗ rojo.
_SEMAFORO_CONFIG: dict = {
    "verde": {
        "emoji": "🟢",
        "glyph": "✓",
        "titulo": "Tono adecuado",
        "border": "#28a745",
        "bg": "#d4edda",
        "text_color": "#155724",
        "tooltip": "Verde: tu mensaje tiene un tono adecuado para esta situación social.",
    },
    "amarillo": {
        "emoji": "🟡",
        "glyph": "⚠",
        "titulo": "Tono mejorable",
        "border": "#ffc107",
        "bg": "#fff3cd",
        "text_color": "#856404",
        "tooltip": "Amarillo: tu emoción es válida, pero el interlocutor puede necesitar más contexto o calma.",
    },
    "rojo": {
        "emoji": "🔴",
        "glyph": "✗",
        "titulo": "Tono brusco",
        "border": "#dc3545",
        "bg": "#f8d7da",
        "text_color": "#721c24",
        "tooltip": "Rojo: tu mensaje puede parecer agresivo, despectivo u hostil. Considera reformularlo.",
    },
}


def render_semaforo_idle() -> str:
    """Devuelve el HTML del semáforo en estado inicial (círculo blanco)."""
    return _SEMAFORO_IDLE


def render_semaforo(result: Optional[ToneResult]) -> str:
    """Devuelve el HTML del semáforo con el color, título y consejo del
    último análisis de tono.

    Args:
        result: :class:`~core.session.ToneResult` a mostrar; si es ``None``
            se devuelve el estado idle.

    Returns:
        Fragmento HTML listo para ``gr.HTML``.
    """
    if result is None:
        return render_semaforo_idle()
    cfg = _SEMAFORO_CONFIG[result.semaforo]
    aria_label = f"Tono detectado: {cfg['titulo']}. {result.consejo}"
    return _SEMAFORO_TEMPLATE.format(
        **cfg,
        consejo=result.consejo,
        aria_label=aria_label,
    )


# ------------------------------------------------------------------
# Historia Social — HTML de resumen de semáforos
# ------------------------------------------------------------------

def render_semaforo_resumen(resumen: dict) -> str:
    """Devuelve una línea Markdown con el recuento total y el porcentaje
    de cada color del semáforo durante la sesión.

    Args:
        resumen: dict con las claves ``verde``, ``amarillo`` y ``rojo``.

    Returns:
        Cadena Markdown con los tres contadores y sus porcentajes.
    """
    verde = resumen.get("verde", 0)
    amarillo = resumen.get("amarillo", 0)
    rojo = resumen.get("rojo", 0)
    total = verde + amarillo + rojo or 1
    return (
        f"**Resumen del semáforo social:**  "
        f"🟢✓ {verde} ({verde*100//total}%)  "
        f"🟡⚠ {amarillo} ({amarillo*100//total}%)  "
        f"🔴✗ {rojo} ({rojo*100//total}%)"
    )


# ------------------------------------------------------------------
# Esquema Carol Gray — visual estructurado sin modelo IA
# ------------------------------------------------------------------
#
# Reemplaza la antigua ilustración generada por Tiny-SD (que producía
# imágenes raras y poco útiles) por un esquema HTML/SVG construido en
# código. Sigue el método Carol Gray: 3 paneles claros con código de
# color, iconos y contenido procesable. Siempre legible, escala con
# texto grande, respeta alto contraste.

def render_esquema_carol_gray(historia) -> str:
    """Devuelve HTML con un esquema visual estructurado de la Historia
    Social. Reusa las clases CSS .historia-* (azul/morado/verde) ya
    definidas en styles.css.

    Args:
        historia: instancia HistoriaSocial con descripcion/perspectiva/
                  directiva y resumen_semaforo.
    """
    # La directiva suele venir como un párrafo; si contiene puntos,
    # extraemos como pasos numerados para procesamiento visual.
    # Forzamos color #064e3b en cada elemento (los <ol><li> no heredan
    # automáticamente del padre si el tema Gradio dark los pone claros).
    pasos = _extraer_pasos(historia.directiva)
    if pasos:
        directiva_html = "<ol style='margin:6px 0 0 18px; padding:0; color:#064e3b;'>" + \
            "".join(f"<li style='margin:4px 0; color:#064e3b;'>{p}</li>" for p in pasos) + "</ol>"
    else:
        directiva_html = f"<p style='margin:6px 0 0 0; color:#064e3b;'>{historia.directiva}</p>"

    # Resumen del semáforo como pequeñas píldoras coloreadas
    sem = historia.resumen_semaforo or {}
    verde = sem.get("verde", 0)
    amarillo = sem.get("amarillo", 0)
    rojo = sem.get("rojo", 0)
    total = verde + amarillo + rojo or 1
    sem_html = (
        "<div style='display:flex; gap:8px; justify-content:center; "
        "flex-wrap:wrap; margin-top:14px;'>"
        f"{_pildora('#d4edda', '#155724', f'🟢✓ {verde} ({verde*100//total}%)')}"
        f"{_pildora('#fff3cd', '#856404', f'🟡⚠ {amarillo} ({amarillo*100//total}%)')}"
        f"{_pildora('#f8d7da', '#721c24', f'🔴✗ {rojo} ({rojo*100//total}%)')}"
        "</div>"
    )

    return f"""
    <div class="esquema-carol-gray" role="img"
         aria-label="Esquema Carol Gray de la Historia Social"
         style="font-family: sans-serif; max-width: 760px; margin: 0 auto;">

      <!-- Cabecera con escenario y rol -->
      <div class="esquema-cabecera"
           style="text-align:center; margin-bottom:14px; padding:10px;
                  background:#f3f4f6; border-radius:6px;">
        <div style="font-size:0.9em; text-transform:uppercase;
                    letter-spacing:1px; color:#1f2937; font-weight:600;">
          Historia Social — {historia.fecha}
        </div>
        <div style="font-size:1.2em; font-weight:700; margin-top:6px; color:#000;">
          {historia.scenario_nombre} · {historia.role_nombre}
        </div>
      </div>

      <!-- Panel 1: DESCRIPCIÓN -->
      <div class="historia-descripcion"
           style="border-left:5px solid #3b82f6; background:#eff6ff;
                  padding:14px 18px; border-radius:6px; margin-bottom:12px;
                  color:#1e3a8a;">
        <div style="font-size:0.85em; font-weight:700; text-transform:uppercase;
                    letter-spacing:1px; color:#1e3a8a;">📋  Descripción</div>
        <p style="margin:6px 0 0 0; color:#1e3a8a;">{historia.descripcion}</p>
      </div>

      <!-- Panel 2: PERSPECTIVA -->
      <div class="historia-perspectiva"
           style="border-left:5px solid #8b5cf6; background:#f5f3ff;
                  padding:14px 18px; border-radius:6px; margin-bottom:12px;
                  color:#5b21b6;">
        <div style="font-size:0.85em; font-weight:700; text-transform:uppercase;
                    letter-spacing:1px; color:#5b21b6;">💭  Perspectiva</div>
        <p style="margin:6px 0 0 0; color:#5b21b6;">{historia.perspectiva}</p>
      </div>

      <!-- Panel 3: DIRECTIVA -->
      <div class="historia-directiva"
           style="border-left:5px solid #10b981; background:#ecfdf5;
                  padding:14px 18px; border-radius:6px; margin-bottom:12px;
                  color:#064e3b;">
        <div style="font-size:0.85em; font-weight:700; text-transform:uppercase;
                    letter-spacing:1px; color:#064e3b;">✓  Directiva</div>
        <div style="color:#064e3b;">{directiva_html}</div>
      </div>

      <!-- Resumen semáforo -->
      {sem_html}

      <div style="text-align:center; margin-top:10px; font-size:0.8em; color:#6b7280;">
        Total de turnos analizados: {historia.num_turnos}
      </div>
    </div>
    """


def _pildora(bg: str, fg: str, texto: str) -> str:
    """Mini badge coloreado para el resumen del semáforo."""
    return (
        f"<span style='background:{bg}; color:{fg}; "
        f"padding:6px 14px; border-radius:14px; font-size:0.95em; "
        f"font-weight:600;'>{texto}</span>"
    )


def _extraer_pasos(texto: str) -> list:
    """Si el texto contiene 2+ frases separadas por '.', '?' o '!',
    las devuelve como lista de pasos. Si no, devuelve lista vacía
    (el caller renderiza como párrafo único)."""
    if not texto:
        return []
    import re
    frases = [f.strip() for f in re.split(r"[.!?]+\s+", texto) if f.strip()]
    return frases if len(frases) >= 2 else []

