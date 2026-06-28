"""
Test del ToneAnalyzer contra el dataset etiquetado a mano.
Imprime accuracy global, accuracy por clase y matriz de confusión.

Uso:
    cd AsistenteTEA
    python -m tests.test_tone

Útil para el informe TFG — comparar accuracy "antes/después" de las
mejoras (stem matching, ironía, monosílabos).
"""

import sys
from pathlib import Path

# Asegurar que el root del proyecto está en path para import core.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.tone_analyzer import ToneAnalyzer
from tests.tone_cases import CASES


def main():
    ta = ToneAnalyzer()
    print(f"\n=== Test ToneAnalyzer ({len(CASES)} casos) ===\n")

    aciertos = 0
    por_clase = {"verde": [0, 0], "amarillo": [0, 0], "rojo": [0, 0]}  # [aciertos, total]
    # Matriz confusión: confusion[esperado][predicho] = count
    confusion: dict = {
        "verde":    {"verde": 0, "amarillo": 0, "rojo": 0},
        "amarillo": {"verde": 0, "amarillo": 0, "rojo": 0},
        "rojo":     {"verde": 0, "amarillo": 0, "rojo": 0},
    }
    fallos = []

    for texto, esperado, motivo in CASES:
        result = ta.analizar(texto)
        predicho = result.semaforo
        ok = (predicho == esperado)

        confusion[esperado][predicho] += 1
        por_clase[esperado][1] += 1
        if ok:
            aciertos += 1
            por_clase[esperado][0] += 1
        else:
            fallos.append((texto, esperado, predicho, motivo))

    total = len(CASES)
    print(f"\n=== Resultados ===")
    print(f"Accuracy global: {aciertos}/{total} = {aciertos/total*100:.1f}%\n")

    print("Accuracy por clase:")
    for color, (a, t) in por_clase.items():
        pct = a / t * 100 if t else 0
        print(f"  {color:8} → {a}/{t} = {pct:.0f}%")

    print("\nMatriz de confusión (filas=esperado, columnas=predicho):")
    print(f"  {'':9} {'verde':>8} {'amarillo':>10} {'rojo':>8}")
    for esperado in ["verde", "amarillo", "rojo"]:
        row = confusion[esperado]
        print(f"  {esperado:9} {row['verde']:>8} {row['amarillo']:>10} {row['rojo']:>8}")

    if fallos:
        print(f"\n=== Fallos ({len(fallos)}) ===")
        for texto, esperado, predicho, motivo in fallos:
            print(f"  [{esperado}→{predicho}] '{texto}' (motivo: {motivo})")

    return aciertos == total


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
