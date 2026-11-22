# Piloto MX/AR: primera corrida (2026-11-22)

Corrida completa del pipeline sobre `dataset-v3` (commit af4c4e5). Los archivos crudos (`results/mx_ar/`) no
están en el repo por `.gitignore`; una copia está guardada fuera del repo junto con el log.

## Configuración

- Qwen2.5-7B-Instruct, capa 20, 7 posiciones (tw-1, tw a tw+5).
- AV `kitft/nla-qwen2.5-7b-L20-av`, K = 5, temperatura 1.0.
- Grader: `claude_api` (claude-sonnet-5-5), `keyword_rule: strict`. ARS desactivado.
- 20 prompts × 7 posiciones × 5 muestras = 700 explicaciones.
- GPU: 1× A40 (RunPod, plantilla PyTorch 2.8). torch 2.8.0+cu129, transformers 4.57.6.

## Decisión (regla fijada antes de la corrida, `decide.py`)

**SUCCESS.** Prueba exacta de permutación de signos, unilateral, sobre los 10 pares juntos (7 distintos de
cero): **p = 0.03125**. D mediana conjunta = +0.20. Se cumplen las tres condiciones: p < 0.05, al menos 3
pares positivos en cada país y ningún país con mediana negativa. Hay 3 ceros de 10, por debajo del límite de
6, así que no corresponde repetir con K = 10.

| País | n | D mediana | + | = | − | p por país |
|---|---|---|---|---|---|---|
| Argentina | 5 | +0.20 | 3 | 2 | 0 | 0.125 |
| México | 5 | +0.20 | 3 | 1 | 1 | 0.1875 |

Los p por país son secundarios: con 3 o 4 pares distintos de cero, el p más bajo posible es 0.125 o 0.0625.

Colombia (solo como referencia, no se junta): D mediana +0.15, 7 de 10 positivos, p = 0.0078.

## D por par

| Par | Pista | Δ cue | Δ neutral | D |
|---|---|---|---|---|
| AR01 | choripán | 0.8 | 0.0 | +0.8 |
| AR02 | el ANSES | 1.0 | 0.2 | +0.8 |
| AR03 | cuarteto | 0.0 | 0.0 | 0.0 |
| AR04 | el Estanciero | 0.4 | 0.2 | +0.2 |
| AR05 | la pileta | 0.0 | 0.0 | 0.0 |
| MX01 | unos esquites | −0.2 | 0.0 | −0.2 |
| MX02 | el IMSS | 1.0 | 0.8 | +0.2 |
| MX03 | mariachi | 1.0 | −0.2 | +1.2 |
| MX04 | el Turista | 0.2 | −0.2 | +0.4 |
| MX05 | la alberca | 0.0 | 0.0 | 0.0 |

## Tasa de mención por posición (fracción de las 5 muestras con label 1)

| Prompt | tw-1 | tw | +1 | +2 | +3 | +4 | +5 |
|---|---|---|---|---|---|---|---|
| MX01 cue | 0.4 | 0.2 | 0.2 | 0.0 | 0.0 | 0.2 | 0.0 |
| MX01 neutral | 0.2 | 0.0 | 0.2 | 0.0 | 0.0 | 0.2 | 0.0 |
| AR01 cue | 0.0 | 0.8 | 0.0 | 0.2 | 0.0 | 0.0 | 0.4 |
| AR01 neutral | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| MX02 cue | 0.0 | 1.0 | 0.2 | 0.8 | 0.8 | 0.6 | 0.6 |
| MX02 neutral | 0.0 | 0.0 | 0.2 | 0.8 | 0.2 | 0.0 | 0.4 |
| AR02 cue | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.4 |
| AR02 neutral | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.2 | 0.2 |
| MX03 cue | 0.0 | 1.0 | 1.0 | 0.6 | 0.6 | 0.4 | 0.0 |
| MX03 neutral | 0.4 | 0.0 | 0.0 | 0.2 | 0.2 | 0.0 | 0.0 |
| AR03 cue / neutral | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| MX04 cue | 0.0 | 0.2 | 0.0 | 0.2 | 0.0 | 0.0 | 0.2 |
| MX04 neutral | 0.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| AR04 cue | 0.0 | 0.2 | 0.4 | 0.0 | 0.0 | 0.4 | 0.0 |
| AR04 neutral | 0.0 | 0.2 | 0.0 | 0.0 | 0.0 | 0.2 | 0.0 |
| MX05 y AR05 (cue y neutral) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Lo que se ve

- **Las pistas que son entidades (instituciones, comida, música) se encienden en la posición de la pista.**
  IMSS, ANSES y mariachi llegan a 1.0 en tw, y choripán a 0.8. En AR02 y AR01 la señal cae casi a cero en la
  posición siguiente; en MX02 y MX03 se mantiene varias posiciones.
- **Las pistas léxicas de dialecto no producen nada.** "alberca" y "pileta" dan 0 en todas las posiciones,
  igual que sus neutrales. Con este grader estricto, el AV no atribuye país por una variante de vocabulario.
- **"cuarteto" (AR03) no produce ninguna atribución.** Es coherente con lo anotado en
  `choclo_cue_candidates.md`: no hay evidencia de que el modelo asocie la palabra con Argentina. Conviene
  preguntarle a Qwen directamente antes de interpretar ese cero como ausencia de sesgo.
- **El marco de MX02 tiene señal mexicana propia.** El neutral ("el banco") llega a 0.8 en tw+2, por eso D es
  solo +0.2 aunque el IMSS llega a 1.0. Hay que mirar las explicaciones del neutral para ver qué palabra la
  produce.
- **MX01 es negativo por ruido en tw-1.** Cue y neutral tienen el mismo texto hasta tw-1 y aun así dan 0.4 y
  0.2. Con K = 5, una diferencia de 0.2 es una sola muestra. En las explicaciones, el AV leyó "esquites"
  como algo de Perú o como un plato "español" genérico.
- **Los juegos de mesa (MX04, AR04) dan señal débil**, de 0.2 a 0.4.

## Grader

- 691 de 700 respuestas se leyeron bien. Las 9 restantes tenían una justificación antes del JSON y se
  contaron como 0. Releídas offline desde las respuestas guardadas (sin llamar de nuevo a la API), 7 son 0 y
  2 son 1 (MX01 neutral tw+4 y MX03 cue tw+1). **D no cambia en ningún par.** El parser ahora toma el último
  objeto JSON de la respuesta (`src/grading.py`), con test.
- Una de esas 2 (MX03 cue tw+1, muestra 2) parece un error del grader según `annotation_guide.md`: la
  explicación dice "hiring a mariachi band" sin ligarlo a México, y el grader mismo lo reconoce antes de
  marcarlo 1 porque "mariachi" está en la lista de ejemplos del prompt. Es un riesgo a revisar en el chequeo
  humano: la frase final del prompt estricto ("Examples of unambiguous references") puede empujar a contar la
  palabra sola. No se cambia el prompt después de ver los datos; el chequeo humano mide cuánto pesa.
- En total hay 85 explicaciones con label 1.

## Próximos pasos

1. Chequeo humano del grader (`human_check_process.md`). El resultado SUCCESS depende de que el grader
   cumpla precisión ≥ 0.90 y recall ≥ 0.80.
2. Revisar las explicaciones de MX02 neutral y de MX03 cue para ver si hay positivos dudosos.
3. Preguntarle a Qwen qué sabe de "cuarteto", "pileta" y "alberca" antes de interpretar sus ceros.
