"""
Dataset etiquetado a mano para validar el ToneAnalyzer.

Cobertura:
  - 30 casos "fáciles" (10 por color): casos con marcadores léxicos
    claros (saludos, palabras emocionales explícitas, insultos directos
    con variantes morfológicas).
  - 30 casos "difíciles" (10 por color): casos sin marcadores léxicos
    fuertes que tensionan las heurísticas: frustración académica plana,
    sarcasmo con vocabulario positivo, pasivo-agresivo, ironía sutil,
    petición indirecta larga, mayúsculas legítimas (no gritos), etc.

Estos casos difíciles afloran las limitaciones de pysentimiento
(entrenado mayoritariamente sobre Twitter, peor en frases planas) y
permiten reportar accuracy desglosado para la sección de validación
y limitaciones del TFG.

Formato: (texto, semaforo_esperado, motivo_etiqueta, dificultad)
  dificultad: "facil" | "dificil"
"""

CASES = [
    # ============================================================
    # CASOS FÁCILES (30) — marcadores léxicos claros
    # ============================================================

    # ---- VERDE fácil (10) ----
    ("Hola, buenos días, ¿qué tal?",                  "verde", "saludo cordial",            "facil"),
    ("Gracias por la explicación.",                    "verde", "agradecimiento",             "facil"),
    ("Estoy contento con el resultado.",               "verde", "emoción positiva",           "facil"),
    ("Perfecto, lo entiendo.",                         "verde", "aceptación neutra",          "facil"),
    ("Me parece bien, podemos seguir.",                "verde", "acuerdo",                    "facil"),
    ("Voy a estudiar más para la próxima.",            "verde", "compromiso",                 "facil"),
    ("Tienes razón, no había pensado en eso.",         "verde", "reconocimiento",             "facil"),
    ("Entiendo tu punto de vista.",                    "verde", "empatía",                    "facil"),
    ("Mañana repaso el tema en casa.",                 "verde", "plan concreto",              "facil"),
    ("Buenas tardes profesor, vengo a la tutoría.",    "verde", "saludo formal",              "facil"),

    # ---- AMARILLO fácil (10) ----
    ("Me da vergüenza preguntar.",                     "amarillo", "vergüenza/sadness",       "facil"),
    ("Tengo miedo de equivocarme.",                    "amarillo", "miedo/fear",              "facil"),
    ("No sé qué hacer en esta situación.",             "amarillo", "confusión",               "facil"),
    ("Es que no entiendo nada de la materia.",         "amarillo", "frustración suave",       "facil"),
    ("Estoy bloqueado y no avanzo.",                   "amarillo", "bloqueo",                 "facil"),
    ("Vale.",                                          "amarillo", "monosílabo cortante",     "facil"),
    ("Bueno.",                                         "amarillo", "monosílabo cortante",     "facil"),
    ("Mmm.",                                           "amarillo", "monosílabo cortante",     "facil"),
    ("No me parece justo el resultado.",               "amarillo", "disconformidad",          "facil"),
    ("Me siento triste por la nota.",                  "amarillo", "tristeza",                "facil"),

    # ---- ROJO fácil (10) ----
    ("Eres un idiota.",                                "rojo", "insulto directo",             "facil"),
    ("¡Imbecil!",                                      "rojo", "insulto puntuación",          "facil"),
    ("Sois unos cabronazos.",                          "rojo", "insulto plural/aumentativo",  "facil"),
    ("Esta asignatura es una mierda.",                 "rojo", "vulgar",                      "facil"),
    ("CÁLLATE de una vez.",                            "rojo", "imperativo hostil + mayús.",  "facil"),
    ("¡¡¡Estoy harto!!!",                              "rojo", "exclamaciones múltiples",     "facil"),
    ("Idiotas, todos vosotros.",                       "rojo", "insulto plural",              "facil"),
    ("Vete a tomar por culo.",                         "rojo", "vulgar imperativo",           "facil"),
    ("Sois unos tarados.",                             "rojo", "insulto plural",              "facil"),
    ("Menudo gilipuertas el profesor.",                "rojo", "insulto variante",            "facil"),

    # ============================================================
    # CASOS DIFÍCILES (30) — sin marcadores léxicos fuertes
    # ============================================================

    # ---- VERDE difícil (10) ----
    ("Buenos días, ¿podría revisar mi examen cuando le venga bien?",  "verde", "petición cortés larga",          "dificil"),
    ("Le agradezco mucho su paciencia con mis preguntas.",            "verde", "gratitud formal larga",          "dificil"),
    ("No estoy de acuerdo, pero respeto su decisión.",                "verde", "disconformidad cortés",          "dificil"),
    ("He estado revisando los apuntes y creo que ya lo entiendo mejor.","verde", "proceso positivo neutro",       "dificil"),
    ("¿Podríamos quedar otro día? Es que ese no puedo.",              "verde", "negativa cortés justificada",    "dificil"),
    ("HOLA PROFESOR, ¿está disponible?",                              "verde", "mayúsculas legítimas",           "dificil"),
    ("Si no es mucha molestia, ¿podría aclararme este apartado?",     "verde", "petición indirecta cortés",      "dificil"),
    ("Por mi parte sin problema, lo que decidáis está bien.",         "verde", "consenso flexible",              "dificil"),
    ("Gracias por avisar, lo tendré en cuenta para la próxima.",      "verde", "cierre cortés",                  "dificil"),
    ("Disculpe el retraso, llegué lo antes que pude.",                "verde", "disculpa formal neutra",         "dificil"),

    # ---- AMARILLO difícil (10) ----
    ("No avanzo con el trabajo, llevo dos semanas con el mismo apartado.","amarillo", "frustración académica plana",    "dificil"),
    ("Llevo intentándolo y no me sale.",                              "amarillo", "bloqueo plano",                  "dificil"),
    ("Me cuesta mucho concentrarme últimamente.",                     "amarillo", "malestar plano",                 "dificil"),
    ("No estoy seguro de cómo plantearlo.",                           "amarillo", "duda formal",                    "dificil"),
    ("Esto se me está haciendo cuesta arriba.",                       "amarillo", "frustración metafórica",         "dificil"),
    ("Sí.",                                                           "amarillo", "monosílabo afirmativo sin cortesía","dificil"),
    ("Ok.",                                                           "amarillo", "monosílabo informal",            "dificil"),
    ("Estoy un poco abrumado con tantas entregas.",                   "amarillo", "saturación leve",                "dificil"),
    ("No tengo claro si he aprobado o no.",                           "amarillo", "incertidumbre académica",        "dificil"),
    ("Necesitaría algo más de tiempo, si fuera posible.",             "amarillo", "petición incómoda",              "dificil"),

    # ---- ROJO difícil (10) ----
    ("Claro, como tú digas.",                                         "rojo", "pasivo-agresivo",                "dificil"),
    ("Buenísimo, otra vez sin entregar.",                             "rojo", "sarcasmo vocabulario positivo",  "dificil"),
    ("Qué bien me has explicado eso, en serio.",                      "rojo", "sarcasmo falsa gratitud",        "dificil"),
    ("Vaya genio que tiene el profesor hoy.",                         "rojo", "insulto velado",                 "dificil"),
    ("Ya estamos otra vez con lo mismo.",                             "rojo", "despectivo neutro",              "dificil"),
    ("Pero qué te crees, ¿que no me he dado cuenta?",                 "rojo", "confrontación retórica",         "dificil"),
    ("Pues vaya nivelazo.",                                           "rojo", "sarcasmo aumentativo",           "dificil"),
    ("Anda ya, hombre.",                                              "rojo", "despectivo cortante",            "dificil"),
    ("No te aguanto más.",                                            "rojo", "rechazo directo sin insulto",    "dificil"),
    ("Eres el peor profesor que he tenido.",                          "rojo", "insulto sin palabras vulgares",  "dificil"),
]
