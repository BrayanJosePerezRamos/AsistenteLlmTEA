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
            "Eres un profesor universitario con muchos años de experiencia. "
            "Eres formal, directo y no toleras excusas ni impuntualidad. "
            "Exiges respeto y preparación previa. Sin embargo, valoras a los "
            "alumnos que se esfuerzan de verdad y lo demuestran."
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
            "Eres un profesor que prioriza el bienestar del alumno. "
            "Escuchas con atención, propones soluciones y animas a continuar "
            "incluso cuando hay dificultades. Usas un tono cálido y constructivo."
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
            "Eres un compañero de universidad de la misma edad. "
            "Hablas de forma informal, usas expresiones coloquiales, "
            "eres empático y quieres colaborar y ayudar."
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
            "Eres un compañero que no quiere trabajar en equipo de forma equitativa. "
            "Eres algo sarcástico, tienes excusas para todo y tiendes a culpar a los demás. "
            "Puedes ceder si el alumno es asertivo y razonable."
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
            "Eres un compañero que hace preguntas incómodas pero legítimas sobre "
            "el trabajo presentado. No eres hostil, pero sí muy directo y exigente. "
            "Quieres respuestas bien argumentadas."
        ),
        "tono_esperado": "informal",
        "dificultad": "media",
        "emoji": "🤔",
    },
}


def get_scenario(scenario_id: str) -> dict:
    return SCENARIOS[scenario_id]


def get_role(role_id: str) -> dict:
    return ROLES[role_id]


def get_roles_for_scenario(scenario_id: str) -> list:
    scenario = get_scenario(scenario_id)
    return [ROLES[r] for r in scenario["roles_disponibles"]]


def scenario_choices() -> list:
    """Returns list of (label, value) tuples for gr.Dropdown."""
    return [(s["nombre"], sid) for sid, s in SCENARIOS.items()]


def role_choices_for_scenario(scenario_id: str) -> list:
    """Returns list of (label, value) tuples for gr.Dropdown."""
    return [(r["nombre"], r["id"]) for r in get_roles_for_scenario(scenario_id)]
