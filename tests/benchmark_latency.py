"""
Benchmark de latencia del primer token (RNF-01).

Mide el tiempo entre el envío de un mensaje de usuario y la llegada del
primer token de la respuesta del LLM, reproduciendo las mismas
condiciones que la aplicación real: system prompt completo de un
escenario, streaming activado y `num_predict=150`.

Uso:
    # Medición con GPU (comportamiento por defecto de Ollama):
    python -m tests.benchmark_latency

    # Medición forzando ejecución íntegra en CPU:
    python -m tests.benchmark_latency --cpu

    # Opciones adicionales:
    python -m tests.benchmark_latency --runs 5 --model qwen2.5:3b

El modelo se precalienta antes de medir (igual que hace la app en el
arranque), de modo que las cifras corresponden al primer turno de una
sesión normal y no incluyen el coste de carga en memoria.
"""

import argparse
import statistics
import time

import ollama

from config.prompts import build_system_prompt
from config.scenarios import get_scenario, get_role

# Mensajes de primer turno representativos, uno por escenario.
PROMPTS = [
    ("revision_examen", "profesor_comprensivo",
     "Hola, quería preguntarle por la nota del examen del otro día."),
    ("revision_examen", "profesor_estricto",
     "Buenos días, creo que hay un error en la corrección de mi examen."),
    ("trabajo_grupo", "companero_conflictivo",
     "Oye, tenemos que repartirnos las partes del trabajo antes del viernes."),
    ("tutoria_profesor", "profesor_comprensivo",
     "Hola, venía a la tutoría porque no entiendo el tema 4 y el examen está cerca."),
    ("presentacion_oral", "companero_critico",
     "Gracias por la pregunta, ¿puedes repetirla? No la he entendido bien."),
]

MAX_TOKENS = 150  # mismo valor que LLMEngine.max_tokens
KEEP_ALIVE = "10m"


def measure_once(model: str, messages: list, options: dict) -> tuple:
    """Lanza una petición en streaming y cronometra la respuesta.

    Args:
        model: nombre del modelo en Ollama.
        messages: lista de mensajes en formato Ollama (system + user).
        options: opciones de inferencia (num_predict, num_gpu...).

    Returns:
        Tupla (ttft, total, n_tokens): segundos hasta el primer token,
        segundos hasta completar la respuesta y tokens generados.
    """
    t0 = time.time()
    ttft = None
    n_tokens = 0
    stream = ollama.chat(
        model=model,
        messages=messages,
        stream=True,
        keep_alive=KEEP_ALIVE,
        options=options,
    )
    for chunk in stream:
        if chunk["message"]["content"]:
            if ttft is None:
                ttft = time.time() - t0
            n_tokens += 1
    return ttft, time.time() - t0, n_tokens


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark de latencia RNF-01")
    parser.add_argument("--cpu", action="store_true",
                        help="Fuerza la inferencia íntegra en CPU (num_gpu=0)")
    parser.add_argument("--runs", type=int, default=3,
                        help="Repeticiones por prompt (por defecto 3)")
    parser.add_argument("--model", default="qwen2.5:3b",
                        help="Modelo de Ollama a medir")
    args = parser.parse_args()

    options = {"num_predict": MAX_TOKENS}
    modo = "GPU"
    if args.cpu:
        options["num_gpu"] = 0
        modo = "CPU"

    # Expulsar el modelo por si estaba cargado con otra configuración
    # (p. ej. pasar de GPU a CPU exige recargar el runner).
    try:
        ollama.chat(model=args.model,
                    messages=[{"role": "user", "content": " "}],
                    stream=False, keep_alive=0,
                    options={"num_predict": 1})
    except Exception:
        pass

    # Warmup: carga el modelo igual que hace la app al arrancar. Se usa
    # un prompt largo neutro (distinto de los medidos) para ejercitar
    # también la ruta de prefill y no contaminar la caché de prefijos.
    print(f"[bench] Modo {modo}. Precalentando '{args.model}'...")
    t0 = time.time()
    warm_text = "Describe brevemente esta lista de palabras. " + \
        " ".join(f"palabra{n}" for n in range(600))
    ollama.chat(model=args.model,
                messages=[{"role": "user", "content": warm_text}],
                stream=False, keep_alive=KEEP_ALIVE,
                options={**options, "num_predict": 1})
    print(f"[bench] Modelo cargado en {time.time() - t0:.1f}s "
          f"(coste de arranque, excluido de las medidas).\n")

    # Las rondas se intercalan (prompt 1..5, prompt 1..5, ...) para que
    # cada petición cambie de prefijo y Ollama no reutilice la caché KV
    # de la petición anterior: así todas las medidas reflejan el coste
    # real del primer turno de una sesión nueva.
    resultados = {i: ([], []) for i in range(len(PROMPTS))}
    for _ in range(args.runs):
        for i, (scenario_id, role_id, user_msg) in enumerate(PROMPTS):
            scenario = get_scenario(scenario_id)
            role = get_role(role_id)
            messages = [
                {"role": "system", "content": build_system_prompt(scenario, role)},
                {"role": "user", "content": user_msg},
            ]
            ttft, total, n_tokens = measure_once(args.model, messages, options)
            resultados[i][0].append(ttft)
            resultados[i][1].append(total)

    all_ttft = []
    all_total = []
    for i, (scenario_id, role_id, _) in enumerate(PROMPTS):
        ttfts, totals = resultados[i]
        all_ttft.extend(ttfts)
        all_total.extend(totals)
        scenario = get_scenario(scenario_id)
        role = get_role(role_id)
        print(f"{scenario['nombre']:<28} ({role['nombre']}): "
              f"primer token {statistics.mean(ttfts):.2f}s "
              f"(min {min(ttfts):.2f} / max {max(ttfts):.2f}), "
              f"respuesta completa {statistics.mean(totals):.2f}s")

    umbral = 8.0 if args.cpu else 3.0
    media = statistics.mean(all_ttft)
    peor = max(all_ttft)
    print(f"\n=== Resumen modo {modo} ({len(all_ttft)} medidas) ===")
    print(f"Primer token   : media {media:.2f}s | mediana "
          f"{statistics.median(all_ttft):.2f}s | max {peor:.2f}s")
    print(f"Resp. completa : media {statistics.mean(all_total):.2f}s | "
          f"max {max(all_total):.2f}s")
    veredicto = "CUMPLE" if peor < umbral else "NO CUMPLE"
    print(f"RNF-01 (< {umbral:.0f}s en {modo}): {veredicto} "
          f"(peor caso {peor:.2f}s)")


if __name__ == "__main__":
    main()
