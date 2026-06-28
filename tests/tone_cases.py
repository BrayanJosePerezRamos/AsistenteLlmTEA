"""
Dataset etiquetado a mano para validar el ToneAnalyzer.
30 ejemplos balanceados (10 por color) cubriendo los casos detectados
durante el desarrollo + variantes morfológicas + ironía + monosílabos.

Formato: (texto, semaforo_esperado, motivo_etiqueta)
"""

CASES = [
    # ---- VERDE (10) ----
    ("Hola, buenos días, ¿qué tal?", "verde", "saludo cordial"),
    ("Gracias por la explicación.", "verde", "agradecimiento"),
    ("Estoy contento con el resultado.", "verde", "emoción positiva"),
    ("Perfecto, lo entiendo.", "verde", "aceptación neutra"),
    ("Me parece bien, podemos seguir.", "verde", "acuerdo"),
    ("Voy a estudiar más para la próxima.", "verde", "compromiso"),
    ("Tienes razón, no había pensado en eso.", "verde", "reconocimiento"),
    ("Entiendo tu punto de vista.", "verde", "empatía"),
    ("Mañana repaso el tema en casa.", "verde", "plan concreto"),
    ("Buenas tardes profesor, vengo a la tutoría.", "verde", "saludo formal"),

    # ---- AMARILLO (10) ----
    ("Me da vergüenza preguntar.", "amarillo", "vergüenza/sadness"),
    ("Tengo miedo de equivocarme.", "amarillo", "miedo/fear"),
    ("No sé qué hacer en esta situación.", "amarillo", "confusión"),
    ("Es que no entiendo nada de la materia.", "amarillo", "frustración suave"),
    ("Estoy bloqueado y no avanzo.", "amarillo", "bloqueo"),
    ("Vale.", "amarillo", "monosílabo cortante"),
    ("Bueno.", "amarillo", "monosílabo cortante"),
    ("Mmm.", "amarillo", "monosílabo cortante"),
    ("No me parece justo el resultado.", "amarillo", "disconformidad"),
    ("Me siento triste por la nota.", "amarillo", "tristeza"),

    # ---- ROJO (10) ----
    ("Eres un idiota.", "rojo", "insulto directo"),
    ("¡Imbecil!", "rojo", "insulto puntuación"),
    ("Sois unos cabronazos.", "rojo", "insulto plural/aumentativo"),
    ("Esta asignatura es una mierda.", "rojo", "vulgar"),
    ("CÁLLATE de una vez.", "rojo", "imperativo hostil + mayúsculas"),
    ("¡¡¡Estoy harto!!!", "rojo", "exclamaciones múltiples"),
    ("Idiotas, todos vosotros.", "rojo", "insulto plural"),
    ("Vete a tomar por culo.", "rojo", "vulgar imperativo"),
    ("Sois unos tarados.", "rojo", "insulto plural"),
    ("Menudo gilipuertas el profesor.", "rojo", "insulto variante"),
]
