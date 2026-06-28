"""
Analizador de tono usando pysentimiento.
Carga los modelos de forma lazy. Ejecuta en CPU.

Capas de detección (en orden de prioridad):
  1. Léxico de insultos por raíz (stem matching)         → rojo directo
  2. Detector de ironía (pysentimiento task="irony")     → rojo si confianza alta
  3. Umbral acumulado anger+disgust + señales (gritos/!) → rojo
  4. Umbral acumulado fear+sadness+surprise              → amarillo
  5. Monosílabos / respuestas cortantes (≤2 palabras)    → amarillo
  6. Fallback: emoción top del modelo                    → según mapeo

La capa léxica usa STEM MATCHING: comprueba si cualquier token del
texto EMPIEZA POR una raíz conocida. Esto cubre variantes morfológicas
("idiotas", "imbeciloide", "cabronazo") sin enumerar cada flexión.
"""

import re
import unicodedata
from typing import Optional

from core.session import ToneResult, SemaforoColor

_EMOTION_TO_SEMAFORO: dict = {
    "anger":   ("rojo",    "Revisa el tono, puede parecer brusco o agresivo."),
    "disgust": ("rojo",    "Revisa el tono, puede parecer despectivo."),
    "joy":     ("verde",   "Tono adecuado, sigue así."),
    "others":  ("verde",   "Tono adecuado, sigue así."),
    "fear":    ("amarillo", "Tranquilo/a, respira y exprésate con calma."),
    "sadness": ("amarillo", "Es válido sentirse así. Expresa tus emociones con calma."),
    "surprise":("amarillo", "Tono adecuado, aunque puede sorprender al interlocutor."),
}

_ROJO_EMOTIONS    = {"anger", "disgust"}
_AMARILLO_EMOTIONS = {"fear", "sadness", "surprise"}

_UMBRAL_ROJO     = 0.55
_UMBRAL_AMARILLO = 0.15  # Bajado de 0.20 → 0.15: vergüenza/frustración leve
                          # como "no entiendo nada" tiene p_amarillo ~0.16; el
                          # umbral anterior las clasificaba como verde y las
                          # marcaba como falsos negativos en la matriz.

# Confianza mínima para fiarse del detector de ironía.
# pysentimiento marca como irónico bastante texto neutro; >0.70
# limita a casos claros (filtra falsos positivos de "menudo día").
_UMBRAL_IRONIA = 0.70

# Lista de RAÍCES (no palabras completas) de insultos. El matcher
# acepta cualquier token que EMPIECE por una raíz, cubriendo flexión
# (femenino/plural/aumentativo/derivados) sin enumerar cada forma.
# Todas las raíces ya están sin acentos — se normaliza el texto antes
# de comparar con _normaliza_acentos().
_RAICES_INSULTO = {
    # Generales / despectivos
    "idiot", "imbecil", "estupid", "subnormal", "inutil",
    "tont", "payas", "capull", "pringa", "memo", "tarad",
    "mongol", "palet", "cretin",
    # Vulgares
    "cabron", "gilipoll", "gilipuert", "putada", "put",
    "jod", "mierd", "cono", "hosti", "zorra", "basura", "asco",
    "hijoputa", "hdp",
    # Imperativos hostiles
    "callat", "largat", "vete", "fuera",
}

# Saludos / palabras cortas que NO son tono frío — el filtro
# de monosílabos debe ignorarlas.
_PALABRAS_CORTAS_OK = {
    # Solo saludos/cierres explícitos — palabras como "vale", "ok",
    # "claro", "sí" pueden ser cortantes en contexto conversacional
    # (respuesta lacónica a una pregunta abierta), por lo que NO se
    # consideran OK por sí solas — las marca amarillo el filtro de
    # monosílabos.
    "hola", "buenas", "adios", "gracias", "graciasportodo",
    "perdon", "perdona", "disculpa", "disculpe",
}


def _normaliza_acentos(s: str) -> str:
    """Quita marcas combinantes (tildes, diéresis) para comparar texto
    independientemente de acentuación. "imbécil" → "imbecil"."""
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if not unicodedata.combining(c))


def _tokeniza(texto: str) -> list:
    """Lista de tokens en minúsculas y sin acentos. Usa regex para
    ignorar puntuación pegada ("idiota!" → ["idiota"])."""
    limpio = _normaliza_acentos(texto.lower())
    return re.findall(r"[a-zñ]+", limpio)


def _contiene_insulto(texto: str) -> bool:
    """True si algún token EMPIEZA POR una raíz de insulto conocida.
    Stem matching → cubre variantes morfológicas con una sola entrada.
    Ejemplos: "idiotas" → match "idiot"; "imbeciloide" → match "imbecil";
              "cabronazo" → match "cabron"; "putada" → match "put"."""
    tokens = _tokeniza(texto)
    return any(tok.startswith(raiz) for tok in tokens for raiz in _RAICES_INSULTO)


def _es_monosilabo_cortante(texto: str) -> bool:
    """True si la respuesta es muy breve (≤2 palabras significativas)
    y NO contiene ningún marcador de cortesía. En conversación social una
    respuesta de una sola palabra suele percibirse como cortante, pero la
    presencia de un saludo/agradecimiento/disculpa anula esa percepción
    (p. ej. 'gracias profesor', 'hola Ana')."""
    tokens = _tokeniza(texto)
    if len(tokens) == 0 or len(tokens) > 2:
        return False
    # Si CUALQUIER palabra es marcador de cortesía, no es cortante
    if any(t in _PALABRAS_CORTAS_OK for t in tokens):
        return False
    return True


def _senales_secundarias(texto: str) -> float:
    """Devuelve un incremento de p_rojo basado en heurísticas de forma:
      - >80% letras en mayúsculas con texto largo → +0.15 ("GRITAR")
      - 3+ signos de exclamación consecutivos → +0.15

    No fuerza rojo directamente; suma a la probabilidad acumulada para
    que entre dentro del flujo de umbrales normal. Cap en 0.30."""
    boost = 0.0
    letras = [c for c in texto if c.isalpha()]
    if len(letras) > 5:
        mays = sum(1 for c in letras if c.isupper())
        if mays / len(letras) > 0.8:
            boost += 0.15
    if re.search(r"[!¡]{3,}", texto):
        boost += 0.15
    return min(boost, 0.30)


class ToneAnalyzer:
    """Lazy-loading wrapper de pysentimiento.
    Carga DOS analizadores: emoción (principal) e ironía (señal extra).
    Ambos comparten lazy-loading por el warmup paralelo en app.py."""

    def __init__(self):
        self._analyzer = None       # task="emotion"
        self._irony_analyzer = None  # task="irony"

    def _ensure_loaded(self) -> None:
        if self._analyzer is None:
            from pysentimiento import create_analyzer
            self._analyzer = create_analyzer(task="emotion", lang="es")
        if self._irony_analyzer is None:
            try:
                from pysentimiento import create_analyzer
                self._irony_analyzer = create_analyzer(task="irony", lang="es")
            except Exception as e:
                # Si el modelo de ironía falla (red, etc.), el análisis
                # principal sigue funcionando — degradamos sin romper.
                print(f"[ToneAnalyzer] No se pudo cargar 'irony' (se omitirá): {e}")
                self._irony_analyzer = False  # marca de "no disponible"

    def _detectar_ironia(self, texto: str) -> tuple:
        """Devuelve (es_ironico: bool, confianza: float).
        Si el analyzer de ironía no está disponible, (False, 0.0)."""
        if not self._irony_analyzer:
            return (False, 0.0)
        try:
            r = self._irony_analyzer.predict(texto)
            label = str(r.output).lower()
            conf = float(r.probas.get(r.output, 0.0)) if r.probas else 0.0
            return (label == "irony" and conf >= _UMBRAL_IRONIA, conf)
        except Exception:
            return (False, 0.0)

    def analizar(self, texto: str) -> ToneResult:
        """Analiza el tono emocional de un texto en español."""
        self._ensure_loaded()
        try:
            result = self._analyzer.predict(texto)
            emocion_top = str(result.output).lower()
            probas = {k.lower(): float(v) for k, v in result.probas.items()} if result.probas else {}

            p_rojo     = sum(probas.get(e, 0.0) for e in _ROJO_EMOTIONS)
            p_amarillo = sum(probas.get(e, 0.0) for e in _AMARILLO_EMOTIONS)
            boost = _senales_secundarias(texto)
            p_rojo_ajustado = p_rojo + boost

            insulto = _contiene_insulto(texto)
            es_ironico, conf_ironia = self._detectar_ironia(texto)
            monosilabo = _es_monosilabo_cortante(texto)

            probas_fmt = {k: round(v, 3) for k, v in probas.items()}
            print(
                f"[ToneAnalyzer] '{texto[:80]}' → top={emocion_top} | "
                f"probas={probas_fmt} | "
                f"p_rojo={p_rojo:.3f}(+boost={boost:.2f}={p_rojo_ajustado:.3f}) "
                f"p_amarillo={p_amarillo:.3f} | "
                f"insulto_lexico={insulto} ironia={es_ironico}(conf={conf_ironia:.2f}) "
                f"monosilabo={monosilabo}"
            )

            # Decisión del semáforo — orden de prioridad:
            # 1) Léxico de insultos por raíz → rojo directo
            if insulto:
                emocion = "anger"
                confianza = max(probas.get("anger", 0.0), probas.get("disgust", 0.0), 0.8)

            # 2) Ironía detectada con alta confianza → rojo
            #    En TEA detectar ironía es crítico — suele ser hostil.
            elif es_ironico:
                emocion = "disgust"
                confianza = conf_ironia

            # 3) Umbral acumulado emociones rojas + señales secundarias
            elif p_rojo_ajustado >= _UMBRAL_ROJO:
                emocion = max(_ROJO_EMOTIONS, key=lambda e: probas.get(e, 0.0))
                confianza = probas.get(emocion, 0.5)

            # 4) Umbral acumulado emociones amarillas
            elif p_amarillo >= _UMBRAL_AMARILLO:
                emocion = max(_AMARILLO_EMOTIONS, key=lambda e: probas.get(e, 0.0))
                confianza = probas.get(emocion, 0.5)

            # 5) Monosílabo / respuesta muy breve → amarillo con consejo específico
            elif monosilabo:
                # Forzamos amarillo via un consejo custom; la emoción se
                # registra como "sadness" para que mapee a amarillo en el dict.
                return ToneResult(
                    texto_original=texto,
                    emocion="sadness",
                    confianza=0.5,
                    semaforo="amarillo",
                    consejo="Las respuestas muy breves pueden parecer cortantes. Intenta dar más contexto.",
                )

            # 6) Fallback: emoción top del modelo
            else:
                emocion = emocion_top
                confianza = probas.get(emocion, 0.5)

        except Exception as e:
            print(f"[ToneAnalyzer] Error en predict(): {e}")
            emocion = "others"
            confianza = 0.5

        semaforo, consejo = _EMOTION_TO_SEMAFORO.get(
            emocion, ("verde", "Tono adecuado, sigue así.")
        )

        return ToneResult(
            texto_original=texto,
            emocion=emocion,
            confianza=confianza,
            semaforo=semaforo,
            consejo=consejo,
        )

    def analizar_historial(self, tone_history: list) -> dict:
        """Agrega el historial de tone results en conteos por color."""
        counts: dict = {"verde": 0, "amarillo": 0, "rojo": 0}
        for t in tone_history:
            counts[t.semaforo] = counts.get(t.semaforo, 0) + 1
        return counts

    def is_available(self) -> bool:
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False
