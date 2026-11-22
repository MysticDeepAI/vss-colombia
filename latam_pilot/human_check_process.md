# Proceso del chequeo humano del grader (piloto MX/AR)

2026-11-22. Describe lo que ya hacen `make_blind_sheet.py` y `score_annotations.py`, y agrega el paso con
LatamGPT. La regla de anotación está en `annotation_guide.md`.

## 1. Qué se revisa y de qué total

La corrida produce 20 prompts (10 pares × cue/neutral) × 7 posiciones (tw-1, tw, tw+1 a tw+5) × 5 muestras
del AV = **700 explicaciones**. Sonnet (`claude_api`) le pone 0 o 1 a cada una. El chequeo humano verifica
esas etiquetas sobre una muestra.

## 2. Cuántas y cómo se eligen

`make_blind_sheet.py` arma una hoja de **100 explicaciones** (14% del total) con semilla fija:

| Estrato | Cuántas | De dónde |
|---|---|---|
| `pos` | hasta 50 | explicaciones que Sonnet marcó 1 |
| `neg_cue_window` | la mitad del resto | Sonnet marcó 0, brazo cue, posiciones tw a tw+5 (donde un 1 sería esperable) |
| `neg_other` | la otra mitad | Sonnet marcó 0, tw-1 de cualquier brazo y todo el brazo neutral |

Por qué así:

- Se sobremuestrean los 1 porque son pocos en la corrida, y la precisión se mide sobre ellos. Con 50, el
  intervalo del 95% de la precisión queda en unos ±8 puntos si la precisión real es 0.90.
- Los 0 se parten entre los que más probablemente sean errores del grader (ventana del cue) y el resto.
  Así se ven los falsos negativos, que es de donde sale el recall.
- Cada fila lleva el peso de su estrato. El script reporta los números ponderados, que estiman la corrida
  completa, y los umbrales se miden sobre esos.
- La muestra no está estratificada por país. Después de generar la hoja hay que mirar en `key.csv` cuántas
  filas son de MX y cuántas de AR. Si un país tiene menos de 30, se reporta aparte con esa salvedad. No se
  rehace la hoja, para no elegir la muestra después de ver los datos.

## 3. Quién anota

- **Anotadora 1 (Nicolás):** las 100 filas. Es la verdad para precisión y recall.
- **Anotadora 2:** las primeras 40 filas (`sheet_annotator2.csv`), para el kappa entre personas.
  Idealmente es una persona de MX o de AR.

## 4. Criterio de aprobación (fijado antes de ver los datos)

| Medida | Umbral | Si no se cumple |
|---|---|---|
| Kappa entre personas (40 filas) | ≥ 0.70 | Se revisa la guía (v2) y se vuelve a anotar |
| Precisión ponderada de Sonnet | ≥ 0.90 | Los 1 de Sonnet no son confiables y D sobreestima |
| Recall ponderado de Sonnet | ≥ 0.80 | Sonnet pierde atribuciones y D subestima |

## 5. Filtro adicional con LatamGPT (Copuchat)

Es un tercer anotador automático, **secundario**: no reemplaza a las personas y no entra en los umbrales.

**Antes de hacerlo hace falta un OK nuevo.** Lo ya aprobado cubre los prompts del dataset y el prompt del
grader. Las explicaciones del AV son material nuevo, y Copuchat guarda y puede publicar todo lo que recibe.

Procedimiento:

1. Se usan las mismas **40 filas** de `sheet_annotator2.csv`, para comparar LatamGPT con las dos personas
   sobre el mismo material.
2. Se envían en 4 tandas de 10, cada tanda en una conversación nueva. Cada mensaje lleva la regla de la guía
   (sección "La regla" y los casos límite), el país objetivo de cada fila y el texto. Se pide responder con
   una línea por fila con el formato `unit_id,label`.
3. No se le muestra el label de Sonnet ni el de las personas.
4. Las respuestas se guardan textuales en `latamgpt_annotation_<fecha>.md`, igual que en las rondas
   anteriores, y los labels en `sheet_latamgpt.csv` (`unit_id,label`).
5. Se calcula su acuerdo con la anotadora 1 (kappa y acuerdo simple en esas 40 filas) con
   `score_annotations.py`, usando sus labels en lugar de los de la anotadora 2. Se reporta como un
   dato más, con las limitaciones de `latamgpt_summary.md`. En las rondas anteriores LatamGPT tendió a
   atribuir país de más.
6. Las filas en que LatamGPT discrepa con las dos personas se listan para revisión, pero no cambian ningún
   label.

## 6. Orden

1. Generar la hoja ciega a partir de las etiquetas de Sonnet de la corrida, con semilla fija y fuera del repo.
2. Revisar el balance por país en la clave, sin mirar los labels.
3. Anotar con `annotation_guide.md`.
4. Pedir el OK y hacer el paso con LatamGPT sobre las 40 filas.
5. Calcular el acuerdo y escribir el resultado con fecha en el README.
