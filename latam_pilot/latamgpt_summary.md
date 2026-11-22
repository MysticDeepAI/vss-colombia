# Revisión con LatamGPT: resumen para redactar (2026-11-22)

Texto pensado para adaptarse a un documento o paper. Los registros completos, con los mensajes y las
respuestas textuales, están en `latamgpt_check_2026-11-22.md` (ronda 1) y
`latamgpt_check_round2_2026-11-22.md` (ronda 2).

## Qué hicimos

Como control complementario a la revisión de hablantes nativos, consultamos a LatamGPT, un modelo de lenguaje
entrenado para América Latina, a través de su interfaz web pública Copuchat (copuchat.latamgpt.org). Todo se
hizo el 22 de noviembre de 2026, sobre la versión candidata dataset-v3 de los pares mínimos de México y
Argentina. Cada pregunta se envió en una conversación nueva.

En la primera ronda hubo cuatro consultas. En dos le mostramos los cinco pares de cada país, le dijimos el
país objetivo y le preguntamos si la versión con pista sonaba natural y si la pista remitía a ese país. En la
tercera le mostramos, sin nombrar ningún país, los diez prompts con pista y tres prompts neutros mezclados, y
le pedimos que adivinara el país de quien escribe y su nivel de confianza. En la cuarta le pedimos que
revisara el prompt del grader y sus listas de referencias, y que clasificara cuatro explicaciones de prueba,
dos positivas y dos negativas, sin mostrarle las respuestas esperadas.

En la segunda ronda le pedimos mejoras para los pares respetando las reglas del diseño, una revisión de si
los prompts neutros contienen pistas de país, alternativas para la pista musical del par AR03 y una revisión
de las listas de referencias del grader para Colombia, México y Argentina.

## Resultados (hechos)

- Con el país nombrado en la pregunta, LatamGPT consideró naturales los diez prompts con pista y dijo que
  todas las pistas remitían al país objetivo.
- A ciegas, atribuyó correctamente 9 de los 10 prompts con pista. El error fue AR03, que en ese momento usaba
  "cumbia": lo atribuyó a Colombia con confianza alta.
- A ciegas, también les asignó un país a los tres prompts neutros: dos con confianza alta y uno con
  confianza media.
- Consideró correctas las listas de referencias de México y Argentina y clasificó las cuatro explicaciones de
  prueba igual que la regla del grader.
- Cuando se le pidieron referencias colombianas, propuso por su cuenta la cumbia. Cuando se le pidieron
  alternativas para AR03, calificó "cuarteto" como igual de natural que "cumbia" en Argentina y sin
  asociación con otro país.
- Señaló que "en la casa" sonaba mexicano y que "jubilación" sonaba argentino.
- Sus propuestas de mejora para los pares no respetaban las reglas indicadas: incluían gentilicios o
  eliminaban la pista. Además cometió errores factuales: describió El Turista como un juego de cartas y dijo
  que el tango no se asocia con otro país.

## Qué cambiamos a partir de esto

Reemplazamos la pista de AR03. El revisor nativo había propuesto "cumbia" en lugar de "tango"; tras el
resultado a ciegas, el equipo eligió "cuarteto", y el revisor lo aprobó el mismo día. Agregamos "cuarteto" a
las referencias argentinas del grader. Mantuvimos el marco "en la casa" por decisión del equipo. No cambiamos
nada más a partir de las sugerencias de LatamGPT.

## Interpretación

LatamGPT sirvió como detector de ambigüedad entre países. Su error a ciegas con "cumbia" coincide con un
riesgo que ya habíamos anotado en el diseño: el género es de origen colombiano y muy difundido en México. En
cambio, no lo consideramos un juez confiable de naturalidad ni de exclusividad. Atribuyó país incluso a
frases diseñadas para ser neutras, aceptó todos los pares cuando la pregunta sugería el país y propuso
cambios que contradecían las reglas que se le dieron. Por eso sus respuestas se usaron solo para señalar
puntos a revisar por personas, y ninguna decisión se tomó solo por lo que dijo.

## Limitaciones

- Copuchat es una interfaz web de chat, sin API documentada. No conocemos la versión del modelo, la
  temperatura ni el prompt de sistema, y no podemos fijar una semilla, así que las respuestas no son
  reproducibles.
- La interfaz mostró el mismo número de conversación después de cada "Nueva Conversación". No podemos
  asegurar que el contexto anterior se haya borrado del lado del servidor.
- Se hizo una sola consulta por pregunta, sin repeticiones. No sabemos cuánto varían las respuestas.
- Las preguntas dirigidas, que nombran el país, tienden a confirmar. El dato más informativo es la prueba a
  ciegas.
- Según los términos de Copuchat, lo enviado puede publicarse, así que los prompts del dataset y el prompt del
  grader quedaron expuestos.
- Es la opinión de un modelo, no de hablantes nativos, y no reemplaza la revisión nativa.
