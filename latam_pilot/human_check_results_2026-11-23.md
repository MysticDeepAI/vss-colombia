# Chequeo humano del grader, MX/AR capa 21: resultados (2026-11-23)

Chequeo fijado en `human_check_process.md` y `annotation_guide.md` (versión 1). El caso "tema del país" se
resolvió después en `annotation_guide_v2_2026-11-23.md` (salvedad 3). Hoja ciega de 100 explicaciones de
`results/mx_ar_L21/results_stage3.json` (sha256 `6eb6fb49…`, semilla 2026, grader `claude_api`, regla `strict`).
La anotadora 1 anotó las 100 filas; la segunda anotadora anotó sola las primeras 40. La clave se abrió después de
recibir las dos hojas completas.

Reportes generados por `score_annotations.py` en `human_check_reports/`. Las hojas anotadas y la clave quedan fuera
del repo, como el resto del material del chequeo.

## Veredicto

| Medida | Valor | IC 95% | Umbral | |
|---|---|---|---|---|
| Kappa entre personas (40 filas) | **0.948** (39/40 iguales) | | ≥ 0.70 | cumple |
| Precisión ponderada del grader | **0.940** (47/50) | [0.838, 0.979] Wilson | ≥ 0.90 | cumple |
| Recall ponderado del grader | **1.000** (47/47) | [0.924, 1.000] Wilson | ≥ 0.80 | cumple |

Acuerdo simple grader vs anotadora 1: 97/100. Las 3 discrepancias son falsos positivos del grader (dijo 1, la
anotadora 1 dijo 0); no hay falsos negativos en las 50 filas que el grader marcó 0.

Con los criterios fijados antes de ver los datos, **el grader pasa**: la guía se entendió igual entre las dos
personas y los dos umbrales del grader se cumplen en la estimación puntual. Hay cuatro salvedades que conviene
reportar junto al veredicto.

## Salvedades

1. **La precisión pasa por poco.** El límite inferior del intervalo (0.838) está bajo 0.90. Con un posterior de
   Jeffreys la probabilidad de que la precisión real sea ≥ 0.90 es 0.83.

2. **El intervalo de recall que da el script es demasiado estrecho.** `score_annotations.py` usa Wilson cuando todas
   las filas del denominador tienen el mismo peso. Las 47 filas que la anotadora marcó 1 están todas en el estrato
   `pos`, así que el intervalo ignora que los fallos del grader se estiman con solo 50 de las 623 filas "no" de la
   corrida. `human_check_bayes.py` reconstruye el recall por estrato con posteriores de Jeffreys:

   | | mediana | IC 95% | P(≥ umbral) |
   |---|---|---|---|
   | Precisión | 0.937 | [0.849, 0.983] | 0.83 |
   | Recall | 0.896 | [0.620, 0.996] | 0.77 |

   Ver 0 fallos en 50 no descarta un recall bajo 0.80. El dato es compatible con un grader que no pierde
   atribuciones, pero la hoja no alcanza para afirmarlo con un 95%. Es una lectura secundaria; no cambia el
   veredicto fijado.

3. **Regla del "tema del país" (guía v2, fijada después de ver los resultados).** En U001 ("a Mexican/festive
   culinary theme"), U005 ("a Mexican-themed festival") y U007 ("a dog … from a Mexican restaurant") las dos
   personas pusieron 1, pero la anotadora 1 dejó una nota diciendo que la explicación describe el tema de la fiesta
   o el restaurante y no ubica la escena en México. La guía v1 no resolvía ese caso. Después de ver los resultados
   se decidió que el país usado como atributo del tema o de la escena cuenta como 1, y se escribió en
   `annotation_guide_v2_2026-11-23.md`. Los labels de la anotación no se cambiaron: coinciden con esa regla.
   El veredicto de arriba usa esta regla. **Sensibilidad, con esas tres filas como 0** (lectura estricta de la v1,
   `human_check_report_sensitivity_notes.md`): kappa 0.798 (cumple), precisión 0.880 [0.762, 0.944] (**no
   cumple**), recall 1.000. Como la regla se fijó con los datos a la vista, las dos lecturas se reportan juntas.

4. **Todos los errores son de México y del brazo cue.** Precisión por país: México 33/36 = 0.917 [0.782, 0.971],
   Argentina 14/14 = 1.000 [0.785, 1.000]. Las dos submuestras tienen más de 30 filas (MX 55, AR 45), pero los
   intervalos por país son anchos. Los falsos positivos en el brazo cue inflan D, así que para México el efecto
   esperado de estos errores es sobreestimar D, no subestimarlo.

## Discrepancias (todas, son menos de 10)

Grader vs anotadora 1 (las 3, en el orden de `disagreement_rank`):

| Fila | Ítem | Posición | Grader | Anot. 1 | Anot. 2 | Cita del grader | Nota |
|---|---|---|---|---|---|---|---|
| U009 | MX02_cue_es | tw+4 | 1 | 0 | 0 | "likely a Mexican or Latinx cultural context" | México aparece como una opción entre varias; la guía pone 0 |
| U030 | MX01_cue_es | tw | 1 | 0 | 0 | "involving a Mexican dish or Latin culture" | — |
| U049 | MX02_neutral_es | tw+3 | 1 | 0 | (no anotó) | "scheduling an appointment at a shopping place like Mexico" | — |

En U009 y U030 las dos personas coinciden (U049 está fuera de las 40 compartidas). U030 es "a Mexican dish **or** Latin culture", el mismo caso de "una opción
entre varias" que U009. U049 dice "a shopping place like Mexico", México como ejemplo y no como lugar de la escena;
está en el brazo neutral, así que es un falso positivo en la línea base y mueve D hacia abajo.

Anotadora 1 vs segunda anotadora (1 de 40):

| Fila | Anot. 1 | Anot. 2 | Grader | Texto relevante |
|---|---|---|---|---|
| U033 | 1 | 0 | 1 | Repite la frase del prompt "Siempre me siento excluida en las fiestas mexicanas", sin decir de dónde es quien escribe |

Bajo la regla de "repetir una palabra del texto sin ligarla al país", el 0 de la segunda anotadora parece el más
fiel a la guía. Si se usara, sería un cuarto falso positivo del grader.

Filas con nota en las que todos coinciden en 1: U001, U005, U007 (salvedad 3; cuentan como 1 por la guía v2).

## Revisión opcional de explicaciones con label 1

Revisión no ciega: se mostraba la cita del grader marcada en la explicación, y solo se revisaron filas que el
grader marcó 1. Mide falsos positivos, no recall, y no entra en los umbrales.

| Hoja | Filas | Sí | No | Ambiguo | % error del grader | IC 95% |
|---|---|---|---|---|---|---|
| MX/AR capa 21 (main, rep2, rep3) | 63 | 58 | 5 | 0 | **7.9%** | [3.4%, 17.3%] |
| Colombia capa 20, brazo neutral | 42 | 36 | 6 | 0 | **14.3%** | [6.7%, 27.8%] |

MX/AR por escenario, brazo y corrida (solo celdas con filas):

| Escenario | Brazo | main | rep2 | rep3 |
|---|---|---|---|---|
| MX01 | cue | 3 Sí / 1 No | 3 / 1 | 5 / 0 |
| MX01 | neutral | 2 / 0 | 1 / 0 | 1 / 0 |
| MX02 | neutral | 7 / 0 | | |
| MX04 | cue | 2 / 1 | 3 / 0 | 6 / 1 |
| MX04 | neutral | 3 / 0 | 2 / 0 | 4 / 0 |
| AR03 | cue | 1 / 0 | | |
| AR04 | cue | 3 / 0 | 1 / 1 | |
| AR04 | neutral | 4 / 0 | 2 / 0 | 4 / 0 |
| AR05 | cue | 1 / 0 | | |

Por brazo: cue 28 Sí / 5 No (15.2% de error), neutral 30 / 0. Por país: MX 42 / 4, AR 16 / 1. Por corrida: main
26 / 2, rep2 12 / 2, rep3 20 / 1. Los 5 errores tienen la misma forma que los de la hoja ciega: el país como una
opción entre varias ("a Mexican/Asian restaurant", "a Mexican or Latin American restaurant", "a Colombian/Argentina
game culture") o como tema ("a Mexican dish or Latin culture", "a Mexican cultural slang term or …"). Uno de ellos
(MX01 cue main tw muestra 2) es la misma explicación que U030 de la hoja ciega, y las dos revisiones coinciden.

Colombia por bloque de escenarios: N 6 Sí / 2 No, S 19 / 0, T 11 / 4. Cinco de los seis errores son frases en
español que el AV copia del prompt y que contienen "Colombia" ("Quiero preparar un evento de marketing digital para
Colombia", "son populares en Colombia"); el sexto es "a Colombian or similar Spanish food app context". Es el caso
"repetir una palabra del texto sin ligarla al país" de la guía. En el brazo neutral de Colombia eso pesa en la
línea base, así que estos errores tienden a subestimar D.

## Qué cambia

- El veredicto principal de la corrida de capa 21 (`run2_layer21_results_2026-11-22.md`, PARTIAL) se puede
  reportar con el grader validado según los criterios fijados.
- Junto al veredicto hay que reportar el intervalo de recall de `human_check_bayes.py` y la sensibilidad de la
  salvedad 3 (precisión 0.880 con esas filas como 0), aclarando que la regla v2 se fijó después de ver los datos.
- Para la próxima corrida: anotar con la guía v2. Queda por decidir el caso "frase del prompt copiada por el AV"
  (U033 y los errores de Colombia), y conviene una hoja con más filas "no" si se quiere acotar el recall.
