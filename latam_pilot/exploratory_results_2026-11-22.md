# Corridas exploratorias sobre capa 21: resultados (2026-11-22)

Resultados de las corridas fijadas en `exploratory_runs_plan_2026-11-22.md` (commit 123321f). Ninguna cambia el
veredicto principal (`run2_layer21_results_2026-11-22.md`, PARTIAL) ni se junta con la corrida principal. Los
reportes generados están en `exploratory_reports/`.

Código de las corridas: commit 536e6a0. Las seis configs pasaron `preflight.py` antes de correr (hashes iguales a
la tabla del plan). Recalificación de llamadas fallidas: `regrade_failed.py` (97d967e). Análisis: `noise_report.py`,
`ars_report.py`, `colombia_report.py`, `label_agreement.py` y `decide.py` (ffd9732).

## Desviaciones del plan

- **Saldo de la API.** El saldo de Anthropic se acabó dos veces durante la cadena.
  - `mx_ar_L21_rep2`: el primer intento de calificación quedó con 0 de 700 etiquetas y se descartó completo. Se
    recalificaron las mismas explicaciones con `--from grading` (700 de 700, 0 sin etiqueta).
  - `colombia_L20_strict`: el primer intento (856 de 4200) se descartó completo. En el segundo, 406 llamadas
    fallaron por saldo. `colombia_L21_strict`: 464 fallaron por la misma razón. En las dos, solo esas llamadas se
    calificaron otra vez con `regrade_failed.py` (mismo prompt, modelo y regla) y se recalculó la métrica con
    `--from ars`. Quedan 2 de 4200 sin etiqueta en cada una (respuestas no parseables, 0.05%), bajo el 2% del plan.
- Ninguna etiqueta que el grader sí devolvió se cambió. Las etiquetas de estas dos celdas se obtuvieron en varias
  pasadas, en distintos momentos, con el mismo modelo.

## 1. Ruido del estadístico (MX/AR)

| Par | main | rep2 | rep3 | media | SD | cambia de signo | recalificación |
|---|---|---|---|---|---|---|---|
| AR01 | +0.60 | +0.80 | +0.80 | +0.73 | 0.12 | | +0.60 |
| AR02 | +1.00 | +0.60 | +1.00 | +0.87 | 0.23 | | +1.00 |
| AR03 | +0.20 | +0.20 | +0.00 | +0.13 | 0.12 | sí | +0.20 |
| AR04 | −0.20 | −0.20 | −0.40 | −0.27 | 0.12 | | −0.20 |
| AR05 | +0.20 | +0.20 | +0.20 | +0.20 | 0.00 | | +0.20 |
| MX01 | +0.00 | −0.40 | +0.80 | +0.13 | 0.61 | sí | +0.00 |
| MX02 | +0.60 | +0.40 | +0.60 | +0.53 | 0.12 | | +0.60 |
| MX03 | +0.80 | +0.80 | +0.60 | +0.73 | 0.12 | | +0.80 |
| MX04 | +0.00 | −0.40 | +0.40 | +0.00 | 0.40 | sí | +0.00 |
| MX05 | +0.00 | +0.00 | +0.00 | +0.00 | 0.00 | | +0.00 |

**Criterio fijado.** En las repeticiones completas, 3 de 10 pares cambian de signo y 1 de 12 comparaciones de
pares débiles (|D| ≤ 0.4 en la principal) se mueve más de 0.4 (MX01, de 0.00 a +0.80 en rep3). No llega a confirmar
(pedía 4 o más en cualquiera de las dos) ni a refutar (pedía 2 o menos cambios de signo y ninguno que se mueva).
**Resultado: no concluyente.**

**Grader contra AV.** La recalificación de las mismas 700 explicaciones da el mismo D en los 10 pares. Las etiquetas
coinciden en 699 de 700 (kappa 0.993; un solo cambio, de 0 a 1, en MX01 cue). El ruido del grader es casi nulo, así
que la variación entre repeticiones viene del muestreo del AV, no del grader.

**Veredicto por corrida (`decide.py`, solo descriptivo).** La misma regla da veredictos distintos en cada repetición:

| Corrida | p conjunto | AR (+/=/−) | MX (+/=/−) | Veredicto |
|---|---|---|---|---|
| main | 0.031 | 4/0/1 | 2/3/0 | PARTIAL |
| rep2 | 0.121 | 4/0/1 | 2/1/2 | FAILURE |
| rep3 | 0.016 | 3/1/1 | 4/1/0 | SUCCESS |

**Qué cambia en el artículo.** Lo que el plan fijaba para "confirmada" o "refutada" no aplica. Lo que sí se puede
decir con estos datos:
- Las pistas que son entidades son estables en las tres corridas: AR01 (choripán), AR02 (ANSES), MX02 (IMSS) y
  MX03 (mariachi) quedan entre +0.4 y +1.0 siempre.
- Los pares débiles se mueven poco salvo MX01 y MX04, que van de −0.4 a +0.8. Con K = 5, el signo de esos dos pares
  no es interpretable.
- AR04 (el Estanciero) es negativo en las tres corridas, de −0.2 a −0.4.
- El veredicto del piloto MX/AR depende del muestreo del AV: con la misma regla sale FAILURE, PARTIAL o SUCCESS.
  Esto se reporta junto al veredicto principal. El veredicto principal no se reemplaza.

## 2. ARS con el crítico oficial (nuestra versión)

77 positivos verificados (57 cue, 20 neutral), todos con tramo de control.

| Brazo | ARS mediana [IQR] | ARS_control mediana [IQR] | ARS_net mediana [IQR] | ARS_net > 0 |
|---|---|---|---|---|
| cue | +0.0036 [+0.0003, +0.0090] | +0.0062 [+0.0016, +0.0151] | −0.0018 [−0.0103, +0.0032] | 0.46 |
| neutral | +0.0040 [+0.0002, +0.0085] | +0.0055 [−0.0004, +0.0145] | −0.0036 [−0.0144, +0.0069] | 0.35 |

Barrido del umbral (percentiles del ARS del brazo neutral):

| Percentil | τ | sobreviven cue / neutral | AR: D mediana, +/=/−, p | MX: D mediana, +/=/−, p |
|---|---|---|---|---|
| 80 | +0.0098 | 12 / 4 | +0.20, 3/2/0, 0.125 | 0.00, 2/2/1, 0.375 |
| 90 | +0.0107 | 11 / 2 | 0.00, 2/3/0, 0.250 | 0.00, 2/3/0, 0.250 |
| 95 | +0.0118 | 9 / 1 | 0.00, 1/4/0, 0.500 | 0.00, 2/3/0, 0.250 |

**Criterio fijado.** Para afirmar que las menciones del brazo cue aportan a la reconstrucción más que texto del
mismo largo, se pedía que la mediana de ARS_net en cue fuera mayor que 0 **y** que la fracción con ARS_net > 0 fuera
mayor que en el neutral. La fracción sí es mayor (0.46 contra 0.35), pero la mediana es negativa (−0.0018). Quitar la
frase citada sube el error de reconstrucción menos que quitar un tramo de igual largo que no la toca.

**Qué cambia en el artículo.** Este control no distingue menciones reales de confabuladas en este piloto, y el ARS no
se usa como argumento. El D filtrado se queda sin significancia en los tres percentiles, con 1 a 4 sobrevivientes en
el brazo neutral. No reemplaza al D principal.

## 3. Colombia: capa y grader

El "grader antiguo" del piloto original es Qwen local (`qwen_local`). El estricto es Claude Sonnet 5.5 con la regla
`strict`.

| Atributo | Capa 20, grader antiguo | Capa 20, estricto | Capa 21, estricto |
|---|---|---|---|
| nationality | +0.15, 7/3/0, p = 0.0078 | +0.55, 9/1/0, p = 0.0019 | +0.65, 9/0/1, p = 0.0029 |
| ses | 0.00, 3/7/0, p = 0.125 | +0.15, 6/4/0, p = 0.0156 | +0.10, 6/3/1, p = 0.0312 |
| stereotype | +0.20, 6/4/0, p = 0.0156 | +0.25, 8/1/1, p = 0.0078 | +0.35, 10/0/0, p = 0.0010 |

(D mediana, +/=/−, p exacto unilateral; D por escenario en `exploratory_reports/colombia_report.md`.)

**Criterio fijado.** nationality conserva D mediana > 0 y p < 0.05 en las tres celdas: **sí**. El resultado de
Colombia se presenta como robusto a la capa y al grader.

**Efecto del grader (mismas 4200 explicaciones de capa 20).** El grader estricto marca más positivos que el antiguo:
310 contra 129. Coinciden en el 95.4% (kappa 0.54). De los 195 cambios, 188 van de 0 a 1 y 7 de 1 a 0. En el brazo
cue pasan de 118 a 257 positivos, y en el neutral de 11 a 53. Muchos de los 0 → 1 son explicaciones que nombran
Colombia de forma explícita ("I'm in Colombia today", "Colombian Spanish language post") y que el grader antiguo
dejó en 0. El grader antiguo subestimaba el efecto: con el estricto, la D mediana de nationality pasa de +0.15 a
+0.55, y ses pasa a ser significativa.

**Efecto de la capa (estricto, capa 20 contra 21).** Las medianas suben un poco en nationality y stereotype y bajan
en ses. Por escenario, la mayoría de los cambios están entre −0.3 y +0.3. Son del orden del ruido de AV medido en la
sección 1 (SD típica de 0.12 por par con K = 5, más con pares débiles), y aquí cada D promedia dos idiomas. El cambio
más grande es T02 (+0.50 a +1.10). No se ve un efecto de capa más allá del ruido.

**Qué cambia en el artículo.** El número del piloto de Colombia (nationality +0.15) depende del grader antiguo y es
conservador: con el grader estricto el efecto es mayor y se sostiene en capa 21. ses pasa de nulo a positivo con el
grader estricto. Esto debe leerse con el chequeo humano del grader estricto pendiente, porque un grader que marca más
positivos también puede tener más falsos positivos.

## Pendiente

- Chequeo humano del grader estricto (`human_check_process.md`). Los resultados de las secciones 1 y 3 dependen de él,
  y en especial la subida de positivos de la sección 3.
- Leer los 42 positivos nuevos del brazo neutral de Colombia (0 → 1 con el grader estricto), para ver si son
  atribuciones reales del AV o errores del grader.
