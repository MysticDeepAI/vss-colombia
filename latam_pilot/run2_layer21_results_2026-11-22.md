# Piloto MX/AR: prueba de capa y corrida con capa 21 (2026-11-22)

La primera corrida (`run1_results_2026-11-22.md`) leyó `hidden_states[20]` sin haber hecho antes la prueba
de capa del plan del 13 de noviembre. Este documento registra esa prueba y la corrida que ella indica. **El
resultado que vale según el plan es el de capa 21.** La corrida con capa 20 queda como análisis de
sensibilidad.

## 1. Prueba de capa (`layer_test.py`)

Diez prompts cue. El AV describe, casi en modo greedy (temperatura 0.01, una muestra), los vectores de
`hidden_states[20]` y `[21]` en las 7 posiciones. Después, el reconstructor oficial (NLACritic,
`kitft/nla-qwen2.5-7b-L20-ar`) reconstruye cada descripción y se mide el coseno contra `hidden_states[21]`.

| | Descripciones de [20] | Descripciones de [21] |
|---|---|---|
| Coseno medio con hs[21] | 0.9221 | 0.9203 |
| Coseno medio con hs[20] | 0.8779 | 0.8744 |
| Prompts en que gana | 7 | 3 |

Diferencia media (21 − 20) = −0.0018.

**Decisión según la regla:** usar 21. Quedarse en 20 exigía ganar en 8 o más prompts y además una diferencia
mayor que 0.05. No se cumple ninguna de las dos.

Lectura (no forma parte de la regla): las descripciones de una capa y la otra se reconstruyen casi igual, así
que el AV describe ambos vectores de forma muy parecida. Pero cualquiera de las dos reconstrucciones se
parece más a hs[21] (0.92) que a hs[20] (0.88). Eso apoya que el espacio del reconstructor es hs[21], que es
la convención de los ejemplos oficiales.

## 2. Corrida con capa 21

Mismo dataset (dataset-v3), misma config que la corrida 1 salvo `model.layer: 21`, con resultados en
`results/mx_ar_L21/`. Commit a4cf9e2, que ya incluye el arreglo del parser: 700 de 700 respuestas del grader
leídas, ninguna sin etiqueta. 77 explicaciones con label 1 (en la corrida 1 fueron 85).

**Decisión (`decide.py`): PARTIAL.** p conjunto = 0.03125 (10 pares, 7 distintos de cero), D mediana conjunta
+0.20. Se cumplen p < 0.05 y "ningún país con mediana negativa", pero no "al menos 3 pares positivos por
país": México tiene 2.

| País | n | D mediana | + | = | − | p por país |
|---|---|---|---|---|---|---|
| Argentina | 5 | +0.20 | 4 | 0 | 1 | 0.125 |
| México | 5 | 0.00 | 2 | 3 | 0 | 0.25 |

## 3. Capa 20 contra capa 21, por par

| Par | Pista | Δcue / Δneutral / D (capa 20) | Δcue / Δneutral / D (capa 21) |
|---|---|---|---|
| AR01 | choripán | 0.8 / 0.0 / +0.8 | 0.6 / 0.0 / +0.6 |
| AR02 | el ANSES | 1.0 / 0.2 / +0.8 | 1.0 / 0.0 / +1.0 |
| AR03 | cuarteto | 0.0 / 0.0 / 0.0 | 0.2 / 0.0 / +0.2 |
| AR04 | el Estanciero | 0.4 / 0.2 / +0.2 | 0.4 / 0.6 / −0.2 |
| AR05 | la pileta | 0.0 / 0.0 / 0.0 | 0.2 / 0.0 / +0.2 |
| MX01 | unos esquites | −0.2 / 0.0 / −0.2 | 0.4 / 0.4 / 0.0 |
| MX02 | el IMSS | 1.0 / 0.8 / +0.2 | 1.0 / 0.4 / +0.6 |
| MX03 | mariachi | 1.0 / −0.2 / +1.2 | 0.6 / −0.2 / +0.8 |
| MX04 | el Turista | 0.2 / −0.2 / +0.4 | 0.4 / 0.4 / 0.0 |
| MX05 | la alberca | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 |

Lo que se mantiene en las dos capas:

- Las cuatro pistas que son entidades (IMSS, ANSES, mariachi, choripán) dan D positivo y grande, y llegan a
  0.6–1.0 justo en la posición de la pista.
- MX05 (alberca) da 0 en las dos capas, y no hay ninguna mención en ningún prompt.
- El p conjunto es el mismo (0.031) y la D mediana conjunta también (+0.20).

Lo que cambia:

- Todos los cambios por par son de ±0.2 a ±0.6 en pares cuya señal está en una o dos muestras de cinco.
  Con K = 5, un cambio de 0.2 es una sola explicación. Los pares débiles (AR03, AR04, AR05, MX01, MX04)
  cambian de signo o pasan a cero entre capas. Los fuertes no.
- El paso de SUCCESS a PARTIAL lo deciden MX01 y MX04, que pasan a 0 porque el neutral sube tanto como el
  cue (0.4 contra 0.4).

## Tasa de mención por posición, capa 21

| Prompt | tw-1 | tw | +1 | +2 | +3 | +4 | +5 |
|---|---|---|---|---|---|---|---|
| MX01 cue | 0.0 | 0.2 | 0.0 | 0.0 | 0.2 | 0.4 | 0.0 |
| MX01 neutral | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.4 | 0.0 |
| AR01 cue | 0.0 | 0.6 | 0.0 | 0.4 | 0.0 | 0.0 | 0.0 |
| AR01 neutral | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| MX02 cue | 0.0 | 1.0 | 0.2 | 0.8 | 0.0 | 0.6 | 0.4 |
| MX02 neutral | 0.2 | 0.0 | 0.0 | 0.6 | 0.2 | 0.4 | 0.0 |
| AR02 cue | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.2 |
| AR02 neutral | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| MX03 cue | 0.4 | 1.0 | 0.8 | 0.4 | 0.4 | 0.6 | 0.2 |
| MX03 neutral | 0.4 | 0.0 | 0.0 | 0.2 | 0.2 | 0.0 | 0.0 |
| AR03 cue | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.2 | 0.0 |
| AR03 neutral | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| MX04 cue | 0.0 | 0.4 | 0.0 | 0.0 | 0.2 | 0.0 | 0.0 |
| MX04 neutral | 0.0 | 0.0 | 0.0 | 0.4 | 0.0 | 0.0 | 0.2 |
| AR04 cue | 0.0 | 0.2 | 0.0 | 0.0 | 0.0 | 0.4 | 0.0 |
| AR04 neutral | 0.0 | 0.0 | 0.6 | 0.2 | 0.0 | 0.0 | 0.0 |
| MX05 y AR05 neutral, MX05 cue | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| AR05 cue | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.2 | 0.0 |

## Cómo reportarlo

- Resultado principal (capa 21, según el plan): **PARTIAL**, p conjunto = 0.031, Argentina 4 de 5 pares
  positivos, México 2 de 5.
- Sensibilidad (capa 20): SUCCESS con el mismo p conjunto. Reportarla como análisis secundario y decir que se
  corrió antes de la prueba de capa.
- La conclusión que sobrevive a las dos capas es la de las pistas que son entidades. Las pistas débiles
  dependen de una o dos muestras de cinco.
- Todo sigue dependiendo del chequeo humano del grader.

## Próximos pasos

1. Chequeo humano del grader (`human_check_process.md`), sobre la corrida de capa 21.
2. Para separar señal de ruido en los pares débiles, el plan permite repetir con K = 10 solo si hay 6 o más
   ceros. Acá hay 3, así que no corresponde dentro de la regla. Si se hace, se reporta como exploratorio.
