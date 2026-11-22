# Corridas exploratorias sobre capa 21 (plan, 2026-11-22)

Escrito antes de correrlas. Ninguna cambia el veredicto principal (`run2_layer21_results_2026-11-22.md`,
PARTIAL). Las tres van en el paper como análisis secundario o de sensibilidad.

## 1. Repetición de MX/AR (`configs/mx_ar_L21_rep2.yaml`)

- Qué: la misma corrida de capa 21, otra vez. El AV samplea a temperatura 1.0 sin semilla, y Sonnet no
  admite temperatura, así que la diferencia entre las dos corridas mide el ruido del estadístico.
- Qué se reporta: D por par en las dos corridas, la diferencia absoluta por par y cuántos pares cambian de
  signo. La hipótesis previa es que un |D| menor que unos 0.4 está dentro del ruido.
- No se junta con la corrida principal ni se usa para el veredicto.

## 2. ARS sobre la corrida principal (`configs/mx_ar_L21_ars.yaml`)

- Qué: se toman las explicaciones y labels ya generados (`results/mx_ar_L21/results_stage3.json`) y se
  puntúa cada positivo verificado con el reconstructor oficial (NLACritic, el mismo de `layer_test.py`).
  ARS = MSE sin la frase citada − MSE con ella. No se regenera nada.
- Hay 77 positivos elegibles: 57 en el brazo cue y 20 en el neutral.
- Regla de siempre: umbral τ en el percentil 90 de los ARS del brazo neutral; un positivo sobrevive si
  ARS > τ. Con 20 valores neutrales, τ depende de los 2 más altos, así que es inestable. Se reporta τ, cuántos
  positivos sobreviven por brazo y el D filtrado. Es secundario: no puede cambiar el veredicto principal.
- Cambio de código: el ARS anterior cargaba el reconstructor como un modelo causal común y no usaba su value
  head ni la distancia normalizada. Ahora usa NLACritic (`src/ars.py`).

## 3. Colombia con capa 21 y grader estricto (`configs/colombia_L21_strict.yaml`)

- Qué: los 30 pares de Colombia (es + en, 120 prompts, 4200 explicaciones) con capa 21 y el mismo grader
  que MX/AR (claude_api, regla estricta).
- Por qué: Colombia se corrió con capa 20 y otro grader, y MX/AR con capa 21. Esto pone las tres en la misma
  configuración.
- No reproduce el número del piloto de Colombia, porque cambian la capa y el grader a la vez. Se reporta
  como sensibilidad, junto al original.
- Grading en paralelo (`grader.max_workers: 8`) para que las 4200 llamadas no tarden horas.
