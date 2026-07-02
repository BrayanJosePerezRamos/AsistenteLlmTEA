# AsistenteTEA

**Simulador multimodal de habilidades sociales para estudiantes universitarios con TEA.**
Trabajo de Fin de Grado. Ejecución íntegramente local.

Brayan José Pérez Ramos, 2026.

---

## Descripción

AsistenteTEA es una aplicación de escritorio, con interfaz web local, que permite al alumnado universitario con Trastorno del Espectro Autista (TEA) practicar situaciones sociales del contexto académico en un entorno seguro. El estudiante elige un escenario (revisión de examen, trabajo en grupo, tutoría, presentación oral) y un interlocutor (profesor estricto, profesor comprensivo, compañero informal, compañero conflictivo o compañero crítico), y mantiene una conversación por texto o voz. Un pequeño modelo de lenguaje ejecuta el rol del interlocutor y responde en tiempo real.

Durante la conversación, cada mensaje del alumno se analiza con un clasificador de emociones e ironía en español, y el resultado se muestra como un **Semáforo Social** (verde/amarillo/rojo) con un consejo breve. Al finalizar la sesión, un módulo genera una **Historia Social** siguiendo la metodología de Carol Gray (descripción objetiva, perspectiva del interlocutor y directiva accionable en primera persona), acompañada de un esquema visual y una narración TTS opcional. Todos los datos permanecen en la máquina del usuario.

---

## Características

- Chat conversacional por texto y voz (STT + TTS neuronales, todo en CPU).
- Cuatro escenarios y cinco roles combinables, con diferentes niveles de dificultad.
- Semáforo Social en cada turno, con consejo, tooltip explicativo y soporte para daltonismo (emoji + glyph ✓ / ⚠ / ✗).
- Historia Social estructurada según el método de Carol Gray, con esquema visual y narración TTS.
- Accesibilidad integrada: modo texto grande y modo alto contraste, ambos persistidos entre sesiones.
- Ejecución 100 % local. Ningún dato sale de la máquina.

---

## Requisitos previos

- **Sistema operativo:** Linux o Windows con WSL2 (probado en Ubuntu 22.04 sobre WSL2). Debería funcionar en macOS con ajustes menores.
- **Python:** 3.10 o superior.
- **RAM:** 8 GB recomendados (el LLM cuantizado + los modelos de voz caben cómodamente).
- **Disco:** unos 5 GB libres para modelos.
- **Ollama:** servidor local para servir el LLM.
- **Micrófono:** opcional, solo si se quiere usar la entrada por voz.

---

## Instalación

Los tres pasos habituales — clonar, entorno virtual, dependencias Python — y después la parte específica de modelos (Ollama, voces Piper y descargas automáticas de whisper/pysentimiento).

### 1. Clonar el repositorio

```bash
git clone https://github.com/BrayanJosePerezRamos/AsistenteTEA.git
cd AsistenteTEA
```

### 2. Crear un entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate       # Linux / macOS / WSL
# .venv\Scripts\activate         # Windows (PowerShell)
```

### 3. Instalar dependencias Python

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Esto instala Gradio, el cliente de Ollama, `faster-whisper`, `piper-tts`, `onnxruntime`, `pysentimiento` y sus utilidades de audio (`soundfile`, `numpy`, `Pillow`, `scipy`).

### 4. Instalar Ollama y descargar el modelo Qwen 2.5

Ollama es el servidor que ejecuta el LLM en local. Instalación en Linux/WSL:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

En Windows y macOS descarga el instalador desde <https://ollama.com/download>.

Con Ollama instalado, descarga el modelo por defecto del proyecto (unos 2 GB):

```bash
ollama pull qwen2.5:3b
```

El servidor Ollama se lanza como servicio en segundo plano tras la instalación. Puedes comprobarlo con:

```bash
ollama list
```

### 5. Voces Piper (TTS)

Las dos voces en español ya están incluidas en el repositorio, en `models/piper/`:

- `es_ES-sharvard-medium.onnx` (principal, 22 050 Hz)
- `es_ES-mls_9972-low.onnx` (respaldo, 16 000 Hz)

Cada `.onnx` va acompañado de su `.onnx.json`. **No es necesario descargarlas.**

### 6. Modelos que se descargan automáticamente en el primer arranque

- **faster-whisper (STT):** al arrancar por primera vez descarga el modelo `small` (~460 MB en int8). Cambia el tamaño con la variable de entorno `TEA_STT_MODEL` (opciones: `tiny`, `base`, `small`, `medium`).
- **pysentimiento (tono):** descarga en el primer uso los dos clasificadores en español (`emotion` e `irony`).

En ambos casos hace falta conexión a internet **solo la primera vez**. Los siguientes arranques son totalmente offline.

---

## Configuración

Variables de entorno opcionales:

| Variable            | Valor por defecto | Uso                                                                                 |
|---------------------|-------------------|-------------------------------------------------------------------------------------|
| `TEA_LLM_MODEL`     | `qwen2.5:3b`      | Modelo servido por Ollama. Puedes usar cualquier otro que hayas hecho `ollama pull`. |
| `TEA_STT_MODEL`     | `small`           | Tamaño de faster-whisper (`tiny`/`base`/`small`/`medium`).                          |
| `ORT_LOGGING_LEVEL` | `3`               | Silencia warnings de onnxruntime en WSL2/headless.                                  |

---

## Uso

1. Asegúrate de que Ollama está corriendo (se lanza como servicio tras la instalación). Sino, arráncalo con:

   ```bash
   ollama serve
   ```
2. Arranca la aplicación:

   ```bash
   python app.py
   ```

3. Al primer arranque verás en consola el warmup paralelo de los cuatro motores (LLM, STT, TTS y analizador de tono). Cuando termina se abre el navegador automáticamente en <http://127.0.0.1:7860>.
4. Flujo típico:
   - En la pestaña **Practicar escenario**: elige escenario y rol, pulsa **Iniciar sesión**.
   - Escribe o graba tu mensaje. El interlocutor responde en streaming; el semáforo se actualiza tras cada turno.
   - Cuando termines, pulsa **Terminar sesión**.
   - Ve a la pestaña **Historia Social** y pulsa **Generar Historia Social**. Verás el esquema Carol Gray (descripción, perspectiva, directiva) con el resumen del semáforo y podrás escuchar la narración.

---

## Escenarios y roles

| Escenario                     | Roles compatibles                                                       |
|-------------------------------|-------------------------------------------------------------------------|
| Revisión de Examen            | Profesor estricto, Profesor comprensivo, Compañero informal             |
| Trabajo en Grupo              | Compañero informal, Compañero conflictivo                               |
| Tutoría con Profesor          | Profesor estricto, Profesor comprensivo                                 |
| Preguntas tras Presentación   | Profesor estricto, Compañero informal, Compañero crítico                |

Los cinco roles cubren un rango de dificultad de bajo (Profesor comprensivo, Compañero informal) a alto (Profesor estricto, Compañero conflictivo).

---

## Estructura del proyecto

```
AsistenteTEA/
├── app.py                # Punto de entrada: warmup y lanzamiento Gradio
├── config/               # Escenarios, roles y plantillas de prompts
├── core/                 # Motores ML y lógica de sesión
│   ├── llm.py            # Cliente Ollama con streaming
│   ├── stt.py            # Reconocimiento de voz (faster-whisper)
│   ├── tts.py            # Síntesis de voz (Piper)
│   ├── tone_analyzer.py  # Semáforo Social (pysentimiento + capa léxica)
│   ├── historia_social.py# Generación de la Historia Social (Carol Gray)
│   └── session.py        # SessionState + ToneResult (dataclasses)
├── ui/                   # Interfaz Gradio
│   ├── tab_chat.py       # Pestaña de práctica
│   ├── tab_historia.py   # Pestaña de Historia Social
│   ├── components.py     # Semáforo y esquema Carol Gray (HTML)
│   ├── styles.css        # Accesibilidad (texto grande, alto contraste)
│   └── scripts.js        # Toggles persistidos en localStorage
├── models/piper/         # Voces Piper en español (incluidas)
├── tests/                # Dataset etiquetado y evaluación del ToneAnalyzer
├── output/               # WAVs generados en runtime (Audio TTS)
├── requirements.txt
```

---

## Pruebas

Evaluación del ToneAnalyzer contra un dataset de 60 casos etiquetados (30 fáciles + 30 difíciles):

```bash
python -m tests.test_tone
```

La salida incluye accuracy global, desglose por dificultad, accuracy por color, matrices de confusión y listado de fallos con motivo. Los resultados actuales (en el hardware de referencia) son aproximadamente:

- Global: 78,3 %
- Subconjunto fácil: 93,3 %
- Subconjunto difícil: 63,3 %

---

## Privacidad

Todo el procesamiento ocurre en local:

- El LLM se sirve mediante Ollama en `127.0.0.1`.
- STT, TTS y análisis de tono se ejecutan en CPU con modelos ya descargados.
- No hay telemetría ni llamadas a APIs externas durante el uso normal.

Los WAVs temporales se guardan en `output/` y pueden borrarse en cualquier momento.

---

## Limitaciones conocidas

- El LLM cuantizado (Qwen 2.5 3B) pierde coherencia en conversaciones largas y su razonamiento pragmático es inferior al de modelos mayores en la nube.
- El analizador de tono se basa en un clasificador léxico + ironía y no cubre de forma fiable sarcasmo, pasivo-agresivo o insultos velados. Por eso el subconjunto de casos difíciles cae al 63,3 %.
- Los cuatro escenarios son un subconjunto reducido de las interacciones sociales del entorno universitario.
- La herramienta no sustituye la intervención de profesionales de la orientación educativa.

---

## Autor y contexto

Trabajo de Fin de Grado desarrollado por **Brayan José Pérez Ramos**.
