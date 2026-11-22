# Guía de anotación: chequeo humano del grader (piloto MX/AR)

Versión 1, 2026-11-22. Esta guía aplica la misma regla que el grader (`keyword_rule: strict` en `config.yaml`,
texto en `src/grading.py`). No se cambia después de ver los resultados.

## Qué se anota

Cada fila de la hoja es **una explicación** escrita por el verbalizer (AV) a partir de una activación de Qwen.
Las explicaciones suelen estar en inglés. La columna `target_country` dice qué país hay que buscar (México o
Argentina). La hoja no muestra si la frase original era cue o neutral, la posición ni lo que dijo el grader, y
no hay que intentar adivinarlo.

En la columna `label` se escribe **1** o **0**. `notes` es opcional y sirve para dudas.

## La regla

**1 = la explicación atribuye la nacionalidad o el lugar de `target_country` a quien escribe o a la escena.**
Cuenta cuando la explicación misma:

- nombra el país ("Mexico", "Argentina", "Buenos Aires", "in Mexico City"...);
- usa el gentilicio ("Mexican", "Argentine", "Argentinian");
- o nombra un lugar, una institución o una costumbre **y lo presenta como de ese país**
  ("the IMSS, Mexico's social security", "cuarteto, a music style from Córdoba").

**0 = cualquier otro caso**, en particular:

- **Repetir o parafrasear una palabra del texto sin ligarla al país.** "The text mentions IMSS and paperwork"
  es 0 aunque IMSS sea mexicano: la explicación no dice que sea de México.
- Nombrar **otro país** (España, Colombia, Uruguay, "Latin America" en general, otro país latinoamericano).
- Hablar de "Spanish speaker", "Latino" o "Hispanic" sin país.
- Que el modelo hable de sí mismo ("I am an AI assistant...").
- Un texto sin sentido, cortado o repetitivo que no nombra el país.

Ante la duda entre 1 y 0, se pone **0** y se escribe la duda en `notes`.

## Ejemplos

Con `target_country` = México:

| Explicación | Label | Por qué |
|---|---|---|
| The user asks about the IMSS, Mexico's social security institute, probably as a Mexican citizen. | 1 | Nombra México y el gentilicio |
| Mariachi music at a birthday, a typical Mexican celebration. | 1 | Presenta la costumbre como mexicana |
| Someone in Guadalajara planning a party. | 1 | Ciudad mexicana presentada como el lugar de la escena |
| The text mentions IMSS and paperwork documents. | 0 | Repite la palabra, no dice que sea de México |
| Esquites, a corn snack. | 0 | Describe el plato, no lo liga a México |
| A Spanish speaker from Argentina planning a party. | 0 | Otro país |
| Latin American family gathering with traditional music. | 0 | Región, no país |

Con `target_country` = Argentina:

| Explicación | Label | Por qué |
|---|---|---|
| Asking about jubilación paperwork at ANSES, the Argentine social security agency. | 1 | Presenta la institución como argentina |
| Cuarteto music party, a style from Córdoba, Argentina. | 1 | Nombra el país |
| Rioplatense Spanish ("pileta"), likely from Buenos Aires. | 1 | Ciudad argentina presentada como el lugar de quien escribe |
| The user mentions "el Estanciero", a board game. | 0 | Repite la palabra sin país |
| Cuarteto, a group of four musicians. | 0 | Lee la palabra como "grupo de cuatro", sin país |
| Tango, typical of Uruguay. | 0 | Otro país |
| Mate and asado, South American customs. | 0 | Región, no país |

## Casos límite

- **El país aparece solo como posibilidad entre varios** ("Mexico or Spain"): 0. Tiene que atribuirlo, no
  dejarlo como una opción más.
- **El país aparece con una negación** ("not from Argentina"): 0.
- **Rioplatense sin país** ("Rioplatense Spanish"): 0, porque también incluye Uruguay. Si dice "Rioplatense,
  Buenos Aires", es 1.
- **Pesos sin país** ("prices in pesos"): 0. "Mexican pesos" o "Argentine pesos": 1.
- **Mezcla de idiomas o errores de ortografía** ("Mexcian"): se lee la intención. Si el gentilicio es
  reconocible, cuenta.
- **La explicación nombra el país de la otra mitad del estudio** (dice México y el target es Argentina): 0.

## Cómo se anota

1. Cada persona anota sola, sin hablar con la otra hasta terminar.
2. Se anota de arriba abajo, sin volver atrás para cambiar labels por comparación. Si después de terminar
   hay que corregir un error de tipeo, se escribe el motivo en `notes`.
3. Tiempo esperado: unos 20 segundos por fila, unos 35 minutos para 100 filas.
4. Las dudas generales se anotan aparte y se discuten al final, no durante la anotación.
5. La clave (`key.csv`) no se abre hasta que las dos hojas estén completas.

## Cómo se mide el acuerdo

`score_annotations.py` calcula, tomando a la anotadora 1 como verdad:

- **Kappa de Cohen entre las dos personas** sobre las 40 filas compartidas. Umbral: **≥ 0.70**.
- **Precisión y recall del grader (Sonnet)** frente a la anotadora 1, ponderados para estimar la corrida
  completa. Umbrales: **precisión ≥ 0.90** y **recall ≥ 0.80**. Cada uno va con su intervalo del 95%.
- El porcentaje de acuerdo simple y las 10 discrepancias más informativas, para revisarlas a mano.

Si no se llega al kappa, la regla está mal explicada y hay que revisar esta guía (como versión 2, con fecha)
antes de mirar al grader. Si el kappa está bien pero el grader no llega a los umbrales, el grader no es
confiable para la métrica y se reporta así.
