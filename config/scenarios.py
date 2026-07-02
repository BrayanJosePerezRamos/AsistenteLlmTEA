"""
Definición de escenarios y roles para el simulador de habilidades sociales.
Sin dependencias de ML — se puede importar sin cargar ningún modelo.
"""

SCENARIOS = {
    "revision_examen": {
        "id": "revision_examen",
        "nombre": "Revisión de Examen",
        "descripcion": (
            "El alumno ha recibido la nota de un examen y quiere hablar sobre "
            "el resultado o solicitar una revisión."
        ),
        "contexto_adicional": (
            "Estás en la facultad, cerca del despacho del profesor o en el pasillo, "
            "justo después de ver la nota publicada."
        ),
        "imagen_prompt_en": "university student talking to professor in faculty hallway, academic setting, realistic, soft colors",
        "roles_disponibles": ["profesor_estricto", "profesor_comprensivo", "companero_informal"],
    },
    "trabajo_grupo": {
        "id": "trabajo_grupo",
        "nombre": "Trabajo en Grupo",
        "descripcion": (
            "El alumno debe repartir tareas con compañeros para entregar "
            "un trabajo en grupo y gestionar posibles conflictos."
        ),
        "contexto_adicional": (
            "Estáis reunidos en la biblioteca o conectados por videollamada "
            "para organizar el trabajo."
        ),
        "imagen_prompt_en": "group of students working together in a library, collaborative study, warm lighting, realistic",
        "roles_disponibles": ["companero_informal", "companero_conflictivo"],
    },
    "tutoria_profesor": {
        "id": "tutoria_profesor",
        "nombre": "Tutoría con Profesor",
        "descripcion": (
            "El alumno solicita una tutoría para pedir ayuda con la materia "
            "o para ampliar el plazo de entrega de una práctica."
        ),
        "contexto_adicional": (
            "Despacho del profesor, con cita previa o llamando a la puerta."
        ),
        "imagen_prompt_en": "student sitting in professor office during tutoring session, university, realistic, calm atmosphere",
        "roles_disponibles": ["profesor_estricto", "profesor_comprensivo"],
    },
    "presentacion_oral": {
        "id": "presentacion_oral",
        "nombre": "Preguntas tras Presentación",
        "descripcion": (
            "El alumno acaba de exponer un proyecto y ahora debe responder "
            "preguntas del público o del evaluador."
        ),
        "contexto_adicional": (
            "Aula de clase, después de la exposición oral. Hay un pequeño turno de preguntas."
        ),
        "imagen_prompt_en": "student presenting project in classroom, academic presentation, audience, realistic, bright",
        "roles_disponibles": ["profesor_estricto", "companero_informal", "companero_critico"],
    },
}

ROLES = {
    "profesor_estricto": {
        "id": "profesor_estricto",
        "nombre": "Profesor Estricto",
        "descripcion_corta": "Formal, exigente, poco tolerante con excusas",
        "descripcion_completa": (
            "Hablas en tono formal y autoritario con frases cortas y directas. "
            "No toleras excusas. En la primera intervención eres neutral: no asumes "
            "irrespeto previo, simplemente esperas a que el alumno explique a qué viene. "
            "Solo si el alumno es irrespetuoso o usa palabras malsonantes le exiges respeto "
            "con firmeza y no continúas hasta que se disculpe. "
            "Si pide revisión, preguntas qué parte concretamente no entiende. "
            "No eres cálido ni empático, pero tampoco hostil sin motivo."
        ),
        "tono_esperado": "formal",
        "dificultad": "alta",
        "emoji": "👨‍🏫",
    },
    "profesor_comprensivo": {
        "id": "profesor_comprensivo",
        "nombre": "Profesor Comprensivo",
        "descripcion_corta": "Empático, paciente, orientado al alumno",
        "descripcion_completa": (
            "Hablas en tono amable y cercano. Si el alumno está nervioso o asustado, "
            "le tranquilizas y le animas a expresarse con calma. "
            "Si es irrespetuoso, le pides con calma que reformule. "
            "Propones soluciones concretas y eres siempre constructivo."
        ),
        "tono_esperado": "formal",
        "dificultad": "baja",
        "emoji": "🧑‍🏫",
    },
    "companero_informal": {
        "id": "companero_informal",
        "nombre": "Compañero Informal",
        "descripcion_corta": "Amigable, usa jerga estudiantil, relajado",
        "descripcion_completa": (
            "Hablas de forma informal y coloquial, usas expresiones como 'tío', 'en plan', 'mola'. "
            "Eres empático y directo. Si algo no te parece bien lo dices sin rodeos "
            "pero sin agresividad. Eres cercano y solidario."
        ),
        "tono_esperado": "informal",
        "dificultad": "baja",
        "emoji": "🧑‍💻",
    },
    "companero_conflictivo": {
        "id": "companero_conflictivo",
        "nombre": "Compañero Conflictivo",
        "descripcion_corta": "Pasivo-agresivo, no colabora fácilmente",
        "descripcion_completa": (
            "Eres pasivo-agresivo y pones excusas para no trabajar. "
            "Tiendes a culpar a los demás con frases cortas y evasivas. "
            "No propones soluciones por iniciativa propia, pero la conversación SIEMPRE avanza. "
            "Si el alumno propone algo concreto o se ofrece a hacer una parte, ACEPTAS "
            "(aunque sea refunfuñando, p. ej. 'bueno, vale', 'como quieras', 'a ver cómo sale'). "
            "Si el alumno te asigna una tarea factible, la aceptas con reticencia pero la aceptas. "
            "NUNCA respondes con 'no respondo a eso' ni te niegas a colaborar de plano: "
            "tu papel es resistirte un poco, no bloquear la actividad."
        ),
        "tono_esperado": "informal",
        "dificultad": "alta",
        "emoji": "😤",
    },
    "companero_critico": {
        "id": "companero_critico",
        "nombre": "Compañero Crítico",
        "descripcion_corta": "Hace preguntas difíciles y desafiantes",
        "descripcion_completa": (
            "Haces preguntas directas y difíciles sobre el trabajo presentado. "
            "No eres hostil pero sí muy exigente. Si la respuesta es vaga o mal argumentada, "
            "insistes o reformulas la pregunta. No te conformas con respuestas imprecisas."
        ),
        "tono_esperado": "informal",
        "dificultad": "media",
        "emoji": "🤔",
    },
}


def get_scenario(scenario_id: str) -> dict:
    """Devuelve el dict del escenario con el ``id`` indicado.

    Args:
        scenario_id: clave del escenario en ``SCENARIOS``.

    Returns:
        dict del escenario.

    Raises:
        KeyError: si ``scenario_id`` no existe.
    """
    return SCENARIOS[scenario_id]


def get_role(role_id: str) -> dict:
    """Devuelve el dict del rol con el ``id`` indicado.

    Args:
        role_id: clave del rol en ``ROLES``.

    Returns:
        dict del rol.

    Raises:
        KeyError: si ``role_id`` no existe.
    """
    return ROLES[role_id]


def get_roles_for_scenario(scenario_id: str) -> list:
    """Devuelve la lista de dicts de los roles compatibles con un escenario.

    Args:
        scenario_id: clave del escenario en ``SCENARIOS``.

    Returns:
        Lista de dicts de rol, en el orden declarado en el escenario.
    """
    scenario = get_scenario(scenario_id)
    return [ROLES[r] for r in scenario["roles_disponibles"]]


def scenario_choices() -> list:
    """Devuelve las opciones de escenario en el formato ``(etiqueta, valor)``
    que espera ``gr.Dropdown``.
    """
    return [(s["nombre"], sid) for sid, s in SCENARIOS.items()]


def role_choices_for_scenario(scenario_id: str) -> list:
    """Devuelve las opciones de rol filtradas por escenario en el formato
    ``(etiqueta, valor)`` que espera ``gr.Dropdown``.

    Args:
        scenario_id: escenario cuyos roles disponibles se quieren listar.

    Returns:
        Lista de tuplas ``(nombre_del_rol, id_del_rol)``.
    """
    return [(r["nombre"], r["id"]) for r in get_roles_for_scenario(scenario_id)]
