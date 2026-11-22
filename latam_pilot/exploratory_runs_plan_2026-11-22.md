# Corridas exploratorias sobre capa 21 (plan, 2026-11-22)

Escrito y commiteado antes de correr nada. Ninguna de estas corridas cambia el veredicto principal
(`run2_layer21_results_2026-11-22.md`, PARTIAL) ni se junta con la corrida principal. En el artículo van como
análisis secundario o de sensibilidad. Cada sección dice qué resultado cambiaría lo que se afirma.

## 1. Ruido del estadístico (MX/AR, capa 21)

**Corridas.**

- Dos repeticiones completas: `configs/mx_ar_L21_rep2.yaml` y `configs/mx_ar_L21_rep3.yaml`. Incluyen
  extracción, AV y grader, sin semilla. Con la corrida principal son 3 valores de D por par.
- Una recalificación de las mismas explicaciones de la corrida principal: `configs/mx_ar_L21_regrade.yaml`,
  con `--from grading` sobre `results/mx_ar_L21/results_stage2.json`, sin GPU. Mide solo el ruido del
  grader, porque Sonnet 5.5 no admite temperatura. La diferencia con las repeticiones completas es el ruido
  del AV.

**Reporte.** `noise_report.py` da, por par, el D de cada corrida, la media, la SD y si cambia de signo, por
separado para las repeticiones completas y para la recalificación.

**Hipótesis previa.** Un |D| menor o igual a 0.4 está dentro del ruido.

- **La confirman** cualquiera de estas dos cosas en las repeticiones completas: 4 o más de los 10 pares
  cambian de signo entre las 3 corridas, o en 4 o más de las comparaciones de un par con |D| ≤ 0.4 contra
  una repetición, el D se mueve más de 0.4.
- **La refutan** las dos cosas a la vez: 2 o menos pares cambian de signo, y ningún par con |D| ≤ 0.4 se
  mueve más de 0.4.
- En cualquier otro caso, no concluyente.

**Qué cambia en el artículo.** Si se confirma, los pares con |D| ≤ 0.4 (en la corrida principal: AR03,
AR04, AR05, MX01, MX04 y MX05) se describen como indistinguibles de cero, y la afirmación se limita a las
pistas que son entidades. Si se refuta, esos pares se pueden describir como señal débil. Si la
recalificación sola explica la mayor parte de la variación, el problema principal es el grader y no el AV,
y eso se dice.

## 2. ARS con el crítico oficial (MX/AR, capa 21)

**Corrida.** `configs/mx_ar_L21_ars.yaml`, con `--from ars` sobre `results/mx_ar_L21/results_stage3.json`.
No se regenera nada. Es **nuestra versión** de ARS, construida sobre el reconstructor oficial (NLACritic).
No es un ARS definido por los autores de NLA, y así se describe.

- El objetivo es el vector guardado en la extracción, `hidden_states[21]`, que es el espacio del
  reconstructor.
- Para cada positivo verificado (77: 57 en el brazo cue y 20 en el neutral) se calcula:
  - ARS = MSE sin la frase citada − MSE original.
  - **Control de longitud:** ARS_control = MSE sin un tramo del mismo largo que no toca la cita − MSE
    original. El tramo sale con una semilla fija por explicación.
  - ARS_net = ARS − ARS_control.
- Antes de la GPU: pruebas en CPU con un crítico falso (`test_cloud_patch.py`).

**Reporte.** `ars_report.py` da:

- las distribuciones de ARS, ARS_control y ARS_net por brazo (n, mediana y cuartiles), y la fracción con
  ARS_net > 0;
- un barrido del umbral τ en los percentiles **80, 90 y 95** del ARS del brazo neutral, con los
  sobrevivientes por brazo y el D filtrado en cada uno.

Con 20 valores neutrales, τ depende de 2 a 4 puntos, así que ningún percentil se toma como el bueno.

**Qué cambia en el artículo.**

- Si en el brazo cue la mediana de ARS_net es mayor que 0 y la fracción con ARS_net > 0 es mayor que en el
  neutral, se dice que las menciones del brazo cue aportan a la reconstrucción más que el texto de igual
  largo, como evidencia a favor de que no son confabulación.
- Si ARS_net del brazo cue no supera al del neutral, se dice que este control no distingue menciones reales
  de confabuladas en este piloto, y no se usa el ARS como argumento.
- El D filtrado se reporta en los tres percentiles y no reemplaza al D principal.

## 3. Colombia: separar capa y grader (2×2 incompleto)

| | Grader antiguo | Grader estricto |
|---|---|---|
| Capa 20 | piloto original (`results/results.json`) | `configs/colombia_L20_strict.yaml` |
| Capa 21 | no se corre | `configs/colombia_L21_strict.yaml` |

**Corridas.**

- **Capa 20 con grader estricto:** recalifica las explicaciones originales del piloto
  (`results/results_stage2.json`, con `--from grading`). Solo cuesta API, sin GPU.
- **Capa 21 con grader estricto:** la corrida completa de los 30 pares, en es y en (120 prompts, 4200
  explicaciones).

**Comparaciones.**

- Piloto original contra capa 20 estricto: efecto del grader.
- Capa 20 estricto contra capa 21 estricto: efecto de la capa. El ruido de AV y grader medido en la sección 1
  sirve de referencia para juzgarlo.

Se reportan, por atributo (nationality, ses, stereotype), D mediana, +/=/− y p, en las tres celdas.

**Qué cambia en el artículo.** El resultado de Colombia se presenta como robusto a la capa y al grader solo
si nationality conserva D mediana > 0 y p < 0.05 en las tres celdas. Si cambia con el grader, se dice que el
número del piloto depende del grader antiguo. Si cambia con la capa más allá del ruido de la sección 1, se
dice que depende de la capa.

**Riesgos operativos.**

- Son 4200 llamadas por celda, con 8 en paralelo. El cliente reintenta los 429 hasta 5 veces con espera, y
  después hay una pasada de reintento. Se reporta cuántas quedan sin etiqueta. Si superan el 2%, se
  recalifican antes de analizar.
- El paralelismo guarda cada resultado en su posición, no en orden de llegada. Hay una prueba de eso.

## Configuraciones (sha256 del archivo al commitear este plan)

| Archivo | sha256 |
|---|---|
| `config.yaml` | `6f279e4240f82ae63e7b64a2e78b9822d40f604038d9975e58d262baca3b81f0` |
| `configs/mx_ar_L21_rep2.yaml` | `a349c7d700b1820f2083e8bf38ad76ca36d4f8103306720a3b8f4747fe4bf23c` |
| `configs/mx_ar_L21_rep3.yaml` | `5e6067639a1bc20e1a50e7099260967ff10fa855d7012aa5d43efe75a43eb29e` |
| `configs/mx_ar_L21_regrade.yaml` | `50d37d241de3fb18e4bc8a5bb910dc6be3fb6f69ad15d6b76ad7fe9f89bd4cc6` |
| `configs/mx_ar_L21_ars.yaml` | `a05f4cbbcfccf39399b500684db57857e12a0c809578c307156547d0e0021df6` |
| `configs/colombia_L20_strict.yaml` | `0c5f93f1ae5ee5f4dab114ef48782694e340bd28bbc40fa27a47ed3deaf63714` |
| `configs/colombia_L21_strict.yaml` | `d62682eff0fd5a5de9f60800294d4f8e52698d076facbf326c7bacbdc6e9ea41` |

Antes de cada corrida se verifica con `sha256sum` que la config no cambió. Cada resultado se reporta con el
commit del código con que se corrió.
