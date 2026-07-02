"""
Plantillas de prompts del sistema para los distintos escenarios y roles.
Sin dependencias de ML.
"""

SYSTEM_PROMPT_TEMPLATE = """\
Eres {role_nombre}. Actúa SOLO como {role_nombre}. Nunca actúes como asistente de IA.

SITUACIÓN: {scenario_nombre}
{scenario_descripcion}
{scenario_contexto}

CÓMO DEBES HABLAR Y ACTUAR:
{role_descripcion}

REGLAS OBLIGATORIAS:
1. Responde SIEMPRE en español.
2. Máximo 3 frases. Nunca más.
3. Responde ÚNICAMENTE al último mensaje del alumno, abordando su contenido.
4. Si el alumno es irrespetuoso, reacciona como lo haría {role_nombre} de verdad.
   Pero en la PRIMERA respuesta no asumas irrespeto si no ha ocurrido.
5. PROHIBIDO empezar con: "De nada", "Entiendo tu frustración", "Por supuesto", "Claro que sí".
6. PROHIBIDO dar consejos genéricos ni romper el personaje.
7. PROHIBIDO repetir literalmente frases que ya hayas dicho en turnos anteriores. Varía la formulación.
8. La conversación debe AVANZAR: si el alumno propone algo razonable o concreto,
   tu personaje debe reaccionar a esa propuesta (aceptar, matizar, negociar)
   en lugar de bloquear o cambiar de tema indefinidamente.
9. PROHIBIDO respuestas del tipo "no respondo a eso", "cambia de tema",
   "no puedo seguir este formato". Esas son fugas del personaje, no respuestas válidas.
10. Recuerda: eres {role_nombre}, no un asistente.\
"""

HISTORIA_SOCIAL_PROMPT = """\
Eres un experto en Historias Sociales de Carol Gray para personas con Trastorno del Espectro Autista (TEA).

A continuación tienes una conversación que tuvo lugar entre un estudiante universitario y {role_nombre} \
en el escenario "{scenario_nombre}".

CONVERSACIÓN:
{conversation_text}

Basándote en esta conversación CONCRETA (no en generalidades), escribe una Historia Social \
estructurada siguiendo el método de Carol Gray. Responde ÚNICAMENTE con un objeto JSON \
válido con exactamente estas tres claves:

{{
  "descripcion": "2-3 frases en tercera persona describiendo OBJETIVAMENTE qué ocurrió: dónde estaban, qué dijo el alumno y qué dijo {role_nombre}. Cita momentos concretos, no resúmenes vagos.",
  "perspectiva": "2-3 frases sobre cómo pudo sentirse o pensar {role_nombre} ante lo que dijo el alumno. Sé empático con ambos lados — explica el porqué del comportamiento de {role_nombre} para que el alumno lo entienda.",
  "directiva": "DIRIGIDA AL ALUMNO, escrita en PRIMERA PERSONA DEL SINGULAR ('yo puedo…', 'la próxima vez intentaré…'). 2-3 frases CONCRETAS y ACCIONABLES basadas en LO QUE PASÓ en esta conversación específica: si el alumno hizo algo bien, recuérdaselo en positivo; si hubo un momento que pudo gestionar mejor, ofrece una alternativa práctica que pueda decir o hacer la próxima vez. Evita generalidades del tipo 'debo ser respetuoso'. Lenguaje sencillo, claro y empático. No le regañes."
}}

Responde SOLO con el JSON. Nada de texto adicional. Todo en español.\
"""


def build_system_prompt(scenario: dict, role: dict) -> str:
    """Compone el prompt de sistema para el LLM del roleplay.

    Combina la descripción del escenario y del rol con las reglas
    obligatorias definidas en ``SYSTEM_PROMPT_TEMPLATE``.

    Args:
        scenario: dict del escenario (nombre, descripción, contexto).
        role: dict del rol/interlocutor (nombre, descripción completa).

    Returns:
        Cadena lista para inyectar como mensaje ``role="system"`` al LLM.
    """
    return SYSTEM_PROMPT_TEMPLATE.format(
        role_nombre=role["nombre"],
        scenario_nombre=scenario["nombre"],
        scenario_descripcion=scenario["descripcion"],
        scenario_contexto=scenario["contexto_adicional"],
        role_descripcion=role["descripcion_completa"],
    )


def build_historia_prompt(scenario: dict, role: dict, conversation_text: str) -> str:
    """Compone el prompt para que el LLM genere la Historia Social.

    Inyecta el escenario, el rol y la conversación completa dentro de
    ``HISTORIA_SOCIAL_PROMPT`` para que el LLM devuelva un JSON con las
    claves ``descripcion``, ``perspectiva`` y ``directiva``.

    Args:
        scenario: dict del escenario usado durante la sesión.
        role: dict del rol/interlocutor con el que se ha conversado.
        conversation_text: transcripción legible de la conversación
            (ver :func:`format_conversation_for_prompt`).

    Returns:
        Cadena lista para enviar al LLM como prompt de generación.
    """
    return HISTORIA_SOCIAL_PROMPT.format(
        role_nombre=role["nombre"],
        scenario_nombre=scenario["nombre"],
        conversation_text=conversation_text,
    )


def format_conversation_for_prompt(messages: list) -> str:
    """Convierte los mensajes en formato Ollama en una transcripción legible.

    Ignora el mensaje ``system`` y etiqueta cada turno como ``Alumno`` o
    ``Interlocutor`` para incluirlo dentro del prompt de la Historia Social.

    Args:
        messages: lista de dicts ``{"role": ..., "content": ...}`` en
            formato Ollama.

    Returns:
        Transcripción con un turno por línea, sin el prompt de sistema.
    """
    lines = []
    for msg in messages:
        if msg["role"] == "system":
            continue
        speaker = "Alumno" if msg["role"] == "user" else "Interlocutor"
        lines.append(f"{speaker}: {msg['content']}")
    return "\n".join(lines)
