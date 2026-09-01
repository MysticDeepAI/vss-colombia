# VSS Colombia — Verbalized Salience Score

Un instrumento cuantitativo para auditar sesgo demográfico latente en Qwen2.5-7B-Instruct, construido sobre el Natural Language Autoencoder (NLA) de Anthropic. VSS mide si una sola palabra culturalmente marcada — leída en contexto — empuja la representación interna del modelo hacia identidad colombiana, estatus socioeconómico o contenido estereotípico, usando un diseño contrafactual de pares mínimos y un filtro causal de confabulación.

Este repositorio es el código complementario del post *"Before the Model Says It: Latent Colombian Identity in Qwen2.5-7B — and the Instrument We Built to Measure It Without Confabulation,"* continuación de un piloto del hackathon de [Apart Research](https://apartresearch.com/).

## Resultados clave

A través de 30 escenarios de pares mínimos (10 por atributo, K = 5 muestras por posición, 120 prompts en total):

| Atributo | VSS mediano | Positivo / 10 | p (corregido por Holm) | Sobrevive al filtro ARS |
|---|---|---|---|---|
| Nacionalidad | +0.15 | 7 | 0.0234 | Se debilita al borde de la significancia |
| Estereotipo | +0.20 | 6 | 0.0312 | Se mantiene |
| Estatus socioeconómico | 0.00 | 3 | — | Nulo (informativo, no decepcionante) |

Ningún escenario, en ningún atributo, produjo un VSS negativo. La metodología completa, las estadísticas y el paso de verificación de confabulación (ARS) están descritos en el post.

## Estructura del repositorio

```
vss-colombia/
├── main.py                       orquesta el pipeline de 5 etapas, guarda results.json
├── plot_results.py               lee results.json, genera figuras (independiente de main.py)
├── config.yaml                   todos los parámetros del experimento (layer, K, umbrales, rutas)
├── environment.yml               especificación del entorno conda
├── dataset/                      30 escenarios de pares mínimos (cue/neutral × ES/EN)
├── src/
│   ├── extraction.py             Etapa 1 — activaciones de Qwen en 7 posiciones de token
│   ├── verbalization.py          Etapa 2 — el AV describe cada activación, K=5 muestras
│   ├── grading.py                Etapa 3 — el grader etiqueta menciones, con auditoría de cita textual
│   ├── ars.py                    Etapa 4 — salience verificada por AR (filtro de confabulación)
│   └── metric.py                 Etapa 5 — Delta, VSS, y la prueba de permutación exacta
├── results/                      results.json, checkpoints por etapa, y figuras
├── validate_all_stages.py        prueba de humo de extremo a extremo en un subconjunto pequeño, las 5 etapas
├── inspect_ar_checkpoint.py      puntual: inspecciona la estructura del checkpoint del Reconstructor
├── diagnose_ar_suffix.py         puntual: verifica la plantilla de prompt anclada por sufijo del AR
├── smoke_test_ar.py              puntual: valida empíricamente la calidad de reconstrucción del AR
├── find_anticipation_cases.py    exploratorio: busca anticipación demográfica antes del cue
└── ars_survival_table.py         genera la tabla de supervivencia de menciones ARS para el paper
```

## Instalación

```bash
conda env create -f environment.yml
conda activate vss-colombia
```

**Versión fijada conocida:** se requiere `transformers==4.57.6` — versiones más nuevas de la serie 5.x entran en conflicto con `huggingface_hub>=1.0` (ver `environment.yml` para más detalles). Si aparece `AttributeError` o `ImportError` al cargar el modelo, confirma que tu versión instalada coincide con esta fijación.

## Uso

### Ejecutar el pipeline completo

```bash
python main.py
```

Esto ejecuta las 5 etapas en orden, guardando un checkpoint después de cada una (`results/results_stage1.json` hasta `results_stage4.json`, y luego el `results/results.json` final). Esto puede tomar varias horas en una sola GPU — la Etapa 2 (verbalización) es el cuello de botella, con 4,200 llamadas al AV.

### Ejecutar etapas parciales

Si una corrida se interrumpe, se puede reanudar desde la última etapa completada en lugar de empezar de nuevo:

```bash
python main.py --to extraction                                          # detener después de la Etapa 1
python main.py --from grading --input results/results_stage2.json       # reanudar desde la Etapa 3
```

Nombres de las etapas, en orden: `extraction`, `verbalization`, `grading`, `ars`, `metric`.

### Generar figuras

```bash
python plot_results.py
```

Lee el `results.json` terminado y produce las curvas de mención posicional, el gráfico de barras de VSS por escenario, y — si la etapa ARS se ejecutó — la tabla de comparación primaria vs. filtrada. Esto está deliberadamente desacoplado de `main.py`: regenerar figuras nunca requiere tiempo de GPU.

### Activar el filtro de confabulación ARS

ARS está desactivado por defecto (`ars.enabled: false` en `config.yaml`) porque carga un segundo modelo completo. Para incluirlo:

```yaml
ars:
  enabled: true
  ar_checkpoint: "kitft/nla-qwen2.5-7b-L20-ar"
  layer_index: 20
  neutral_percentile: 90
```

### Validar el pipeline antes de una corrida completa

```bash
python validate_all_stages.py
```

Ejecuta las 5 etapas en un subconjunto de 2 escenarios con aserciones explícitas en cada transición — la forma más económica de detectar una configuración rota antes de comprometerse a una corrida de varias horas.

## Qué mide cada cosa (glosario rápido)

- **Arm (cue / neutral)**: cada escenario tiene una versión con la palabra sensible (p. ej. "arepa") y una versión gemela con una palabra neutral (p. ej. "sandwich"), idéntica en todo lo demás.
- **Window**: 7 posiciones de token alrededor de la palabra clave: `tw-1` (justo antes, no puede saber nada de la palabra clave todavía, por causalidad del transformer), `tw` (la palabra clave), y `tw+1` hasta `tw+5` (después).
- **s_t**: de las K muestras del AV en la posición t, qué fracción menciona a Colombia.
- **Delta**: cuánto sube s_t después de la palabra clave comparado con antes.
- **D**: Delta del arm de cue menos Delta del arm neutral — aísla el efecto atribuible a la palabra clave, restando la tasa de confabulación propia del AV.

## Velocidad: por qué corre en GPU y aun así puede ser lento

`extraction.py` y `verbalization.py` ya cargan los modelos con `device_map="cuda"`. Pero tener una GPU no es suficiente por sí solo: una GPU rinde cuando procesa MUCHAS cosas a la vez (batching), no una secuencia a la vez. `verbalization.py` aprovecha esto: las 7 posiciones de un mismo prompt comparten exactamente el mismo prompt base del AV (misma longitud), así que se apilan en un solo batch y las 7 x K=5 = 35 secuencias se generan en **una sola llamada a `generate()`** por prompt, en lugar de 35 llamadas seriales. Esto reduce ~4,200 llamadas a ~120, sin necesidad de servidor ni async — solo uso adecuado del batching estándar de Hugging Face.

En caso de errores por falta de memoria, en `config.yaml` establece:
```yaml
sampling:
  batch_across_positions: false
```
Esto regresa a una versión más lenta (7 llamadas por prompt en lugar de 1) que usa mucha menos memoria a la vez.

### Verificar el batching (recomendado antes de una corrida completa)

El reordenamiento de la salida del batch asume que `generate()` agrupa las K muestras de cada fila de forma contigua (comportamiento documentado de Hugging Face, aunque no forma parte de su API pública formal). Antes de correr los 120 prompts, vale la pena verificar con una prueba de humo: correr `main.py --to verbalization` en 2-3 prompts con `batch_across_positions: true` y comparar contra la misma corrida con `false` — las explicaciones no necesitan ser idénticas (el muestreo es aleatorio), pero deben ser **temáticamente consistentes por posición** (p. ej. `tw-1` nunca debería mencionar la palabra clave en ninguna de las dos versiones). Si se ven mezcladas, hay que marcarlo y volver a `false` mientras se investiga.

## Cambiar el grader

En `config.yaml`, `grader.backend` puede ser:
- `qwen_local`: rápido, usa el mismo Qwen ya cargado (por defecto).
- `claude_api`: más lento, requiere `ANTHROPIC_API_KEY` en el entorno, pero es un juez independiente y más riguroso — útil para validar una muestra de lo que calificó `qwen_local`.

## Referencia de configuración

Todos los parámetros del experimento viven en `config.yaml`: qué capa extraer (`model.layer`), cuántas muestras del AV por posición (`sampling.k_samples`), comportamiento de batching, el backend del grader (`qwen_local` o `claude_api`), y el percentil de umbral de ARS. Nada está hardcodeado en el código del pipeline — cambia los valores ahí, no en `src/`.

## Dataset

30 escenarios base (10 nacionalidad, 10 estatus socioeconómico, 10 estereotipo), cada uno realizado como un par mínimo (palabra cue vs. palabra neutral emparejada) tanto en español colombiano como en inglés — 120 prompts en total. Cada par se valida programáticamente (diff a nivel de palabra, un solo tramo contiguo por idioma) antes de su uso; los criterios de construcción, la calificación de fuerza del cue, y los riesgos declarados por par están documentados junto al dataset.

## Diagnóstico y scripts puntuales

Algunos scripts en la raíz del repositorio no forman parte del pipeline regular; se construyeron para resolver preguntas específicas de implementación y se conservan para reproducibilidad y para quien extienda este trabajo a un checkpoint distinto de NLA:

- **`inspect_ar_checkpoint.py`** — imprime la configuración, metadatos y claves safetensors del checkpoint del Reconstructor. Ejecútalo primero si alguna vez cambias a un checkpoint de AR distinto; varios de sus supuestos arquitectónicos (sin cabeza de reconstrucción separada, hidden state crudo de la capa 20 como salida) se confirmaron empíricamente de esta forma, no se asumieron solo por documentación.
- **`diagnose_ar_suffix.py`** — decodifica el sufijo de prompt esperado por el AR contra la salida real de la plantilla, para detectar discrepancias de tokenización antes de que corrompan silenciosamente las reconstrucciones.
- **`smoke_test_ar.py`** — la verificación empírica detrás del diseño de ARS: reconstruye una activación conocida a partir de su explicación correspondiente versus una no relacionada, confirmando que el Reconstructor se comporta como se espera antes de confiar en él a escala.
- **`find_anticipation_cases.py`** — un escaneo exploratorio de las explicaciones del arm neutral en la línea base pre-cue, buscando contenido demográfico que aparece sin ningún disparador léxico presente. Esta es evidencia cualitativa de un fenómeno que VSS es estructuralmente incapaz de medir (ver la discusión del post sobre anticipación pre-cue).
- **`ars_survival_table.py`** — genera la tabla de supervivencia a nivel de mención de ARS (cuántas menciones marcadas por el grader, por atributo, sobrevivieron el filtro de confabulación), separada de la comparación a nivel de escenario que ya está en `plot_results.py`.

## Referencia

Este trabajo se construye directamente sobre el Natural Language Autoencoder de código abierto liberado por Anthropic:
Fraser-Taliente et al. (2026), *Natural Language Autoencoders*. https://github.com/kitft/natural_language_autoencoders

## Autores

Pablo Santiago Potes Velasco¹, María del Mar García Matabanchoy¹, Óscar Julián Pérez Ladino¹, Jhoan Stevan Mosquera Ortiz¹, Nicolás Lozano Mazuera¹, Gilber Alexis Corrales Gallego¹˒²

¹ Universidad Autónoma de Occidente, Cali, Colombia
² GobLab, Universidad Adolfo Ibáñez

Contacto: gacorrales@uao.edu.co

## Agradecimientos

Agradecemos a Apart Research por organizar el hackathon que inició este proyecto, y a Apart Lab por el cómputo y el apoyo que hicieron posible el trabajo de continuación. Este trabajo se realizó tras el terremoto que sacudió a Colombia el 10 de agosto de 2026; está dedicado a todos los afectados, particularmente en Cali, nuestra ciudad natal.
