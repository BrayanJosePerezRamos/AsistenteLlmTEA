"""
Test del ToneAnalyzer contra el dataset etiquetado a mano.

Reporta:
  - Accuracy global, por clase y por dificultad (facil/dificil).
  - Matriz de confusión global y desglosada.
  - Lista de fallos con texto, esperado, predicho y motivo.

Uso:
    cd AsistenteTEA
    python -m tests.test_tone

Útil para el informe TFG — el desglose facil/dificil permite mostrar
tanto el cumplimiento del RNF-03 sobre el subconjunto principal como
las limitaciones honestas del clasificador sobre el subconjunto
trampa (sarcasmo, pasivo-agresivo, frustración plana, etc.).
"""

import sys
from pathlib import Path

# Asegurar que el root del proyecto está en path para import core.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.tone_analyzer import ToneAnalyzer
from tests.tone_cases import CASES

_COLORES = ["verde", "amarillo", "rojo"]


def _matriz_vacia() -> dict:
    """Devuelve una matriz de confusión 3x3 inicializada a cero, indexada
    por color (``verde``/``amarillo``/``rojo``) en filas y columnas."""
    return {c: {p: 0 for p in _COLORES} for c in _COLORES}


def _imprimir_matriz(titulo: str, matriz: dict) -> None:
    """Imprime por consola una matriz de confusión con encabezado y celdas
    alineadas. Las filas son la etiqueta esperada y las columnas la predicha.

    Args:
        titulo: cabecera que se muestra sobre la matriz.
        matriz: dict con la forma devuelta por :func:`_matriz_vacia`.
    """
    print(f"\n{titulo} (filas=esperado, columnas=predicho):")
    print(f"  {'':9} {'verde':>8} {'amarillo':>10} {'rojo':>8}")
    for esperado in _COLORES:
        row = matriz[esperado]
        print(f"  {esperado:9} {row['verde']:>8} {row['amarillo']:>10} {row['rojo']:>8}")


def _imprimir_accuracy(titulo: str, aciertos: int, total: int) -> None:
    """Imprime una línea con el conteo de aciertos y su porcentaje.

    Args:
        titulo: etiqueta descriptiva alineada a la izquierda.
        aciertos: número de casos acertados.
        total: número total de casos evaluados (0 → 0.0 %).
    """
    pct = (aciertos / total * 100) if total else 0.0
    print(f"{titulo:30} {aciertos:>3}/{total:<3} = {pct:5.1f}%")


def main() -> bool:
    """Recorre el dataset etiquetado y calcula accuracy global, por clase,
    por dificultad y matrices de confusión (global, fácil, difícil).

    Returns:
        ``True`` si todos los casos se han clasificado correctamente,
        ``False`` si al menos uno falla. El proceso termina con ``exit(0)``
        o ``exit(1)`` según ese valor.
    """
    ta = ToneAnalyzer()
    print(f"\n=== Test ToneAnalyzer ({len(CASES)} casos) ===\n")

    # Acumuladores
    aciertos_global = 0
    por_clase: dict = {c: [0, 0] for c in _COLORES}                # [aciertos, total]
    por_dificultad: dict = {"facil": [0, 0], "dificil": [0, 0]}
    confusion_global = _matriz_vacia()
    confusion_por_dif: dict = {"facil": _matriz_vacia(), "dificil": _matriz_vacia()}
    fallos: list = []

    for caso in CASES:
        # Backwards compat: tuplas de 3 elementos se asumen "facil".
        if len(caso) == 4:
            texto, esperado, motivo, dificultad = caso
        else:
            texto, esperado, motivo = caso
            dificultad = "facil"

        result = ta.analizar(texto)
        predicho = result.semaforo
        ok = (predicho == esperado)

        confusion_global[esperado][predicho] += 1
        confusion_por_dif[dificultad][esperado][predicho] += 1
        por_clase[esperado][1] += 1
        por_dificultad[dificultad][1] += 1
        if ok:
            aciertos_global += 1
            por_clase[esperado][0] += 1
            por_dificultad[dificultad][0] += 1
        else:
            fallos.append((texto, esperado, predicho, motivo, dificultad))

    total = len(CASES)

    # ----- Bloque de resultados -----
    print(f"\n=== Resultados ===\n")
    _imprimir_accuracy("Accuracy global", aciertos_global, total)
    print()

    print("Accuracy por dificultad:")
    for nivel in ("facil", "dificil"):
        a, t = por_dificultad[nivel]
        _imprimir_accuracy(f"  {nivel}", a, t)
    print()

    print("Accuracy por clase (global):")
    for c in _COLORES:
        a, t = por_clase[c]
        _imprimir_accuracy(f"  {c}", a, t)

    _imprimir_matriz("Matriz de confusión GLOBAL", confusion_global)
    _imprimir_matriz("Matriz de confusión FÁCIL", confusion_por_dif["facil"])
    _imprimir_matriz("Matriz de confusión DIFÍCIL", confusion_por_dif["dificil"])

    if fallos:
        print(f"\n=== Fallos ({len(fallos)}) ===")
        for texto, esperado, predicho, motivo, dificultad in fallos:
            print(f"  [{dificultad}][{esperado}→{predicho}] '{texto}' (motivo: {motivo})")

    return aciertos_global == total


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
