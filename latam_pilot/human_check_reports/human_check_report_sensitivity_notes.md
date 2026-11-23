# Human check of the grader

Sheet: 100 units from `tar/results/mx_ar_L21/results_stage3.json` (seed 2026), sampled on the labels of **claude_api**. Truth = annotator 1. Thresholds fixed in advance: kappa >= 0.7, precision >= 0.9, recall >= 0.8.

Pools in the run -> rows on the sheet: pos 77 -> 50, neg_cue_window 245 -> 25, neg_other 378 -> 25.

## Annotator agreement

Cohen's kappa on 40 shared rows: **0.798** (36/40 same label; threshold 0.7: met).

## Grader: claude_api

|                | human yes | human no |
|----------------|-----------|----------|
| grader yes     |        44 |        6 |
| grader no      |         0 |       50 |

| metric | on the sheet (raw) | whole run (weighted) | 95% interval | threshold |
|--------|--------------------|----------------------|--------------|-----------|
| precision | 0.880 (44/50) | 0.880 | [0.762, 0.944] (Wilson) | 0.9 NOT met |
| recall | 1.000 (44/44) | 1.000 | [0.920, 1.000] (Wilson) | 0.8 met |

### 6 most informative of 6 disagreements (claude_api vs annotator 1)

- **U005** MX03_cue_es tw+4 sample 4 - grader yes, human no - grader quote: "organizing a Mexican-themed festival"
  > Spanish language context suggest a customer asking for advice or planning details about a wedding reception party, implying a formal query format with a question about organizing a Mexican-themed festival. The phrase "Quiero hacer una boda en julio en mi casa, estoy pensando en hacer una cena con música en vivo y quiero organizarlo, " strongly implies a list of activities or requirements is expected next. Final token "organizamos, " closes a clause mid-sentence ("Quiero hacer una boda en casa y me gustaría hacer la Fiesta de Halloween con música, nosotros queremos..."), strongly expecting continuation like "but what would be the budget?" or "how should we plan?".

- **U007** MX04_cue_es tw+3 sample 1 - grader yes, human no - grader quote: "a dog named "Gus" from a Mexican restaurant"
  > Formal Spanish language context with a bilingual or informal tone suggests a query or anecdote about a dog named "Gus" from a Mexican restaurant. The phrase "Algunas veces sale un perro para jugar después de comer" implies a scheduled outdoor activity following a meal, strongly suggesting a specific routine or habit description around Thanksgiving or similar meal context. Final token "comer" ends an incomplete clause ("después de comer"), part of a comma-separated list ("Suena con los perros después del postre después de comer"), expecting immediate continuation like "or dinner" or "and then," or "a meal," or "often" describing the food habit.

- **U009** MX02_cue_es tw+4 sample 4 - grader yes, human no - grader quote: "likely a Mexican or Latinx cultural context"
  > Formal Spanish language context with greeting structure "Mi padre va al hospital y no sé qué" implies a question about travel preparation for a job interview, likely a Mexican or Latinx cultural context. The phrase "Digo que voy al hospital para la entrevista y no sé qué" strongly suggests a list or itemized checklist item expected next, likely asking about required documents or items for the appointment. Final token "qué" is mid-clause ("No sé qué"), part of an incomplete clause describing uncertainty ("Ya que, qué..."), immediately expecting noun phrases like "documentos necesito" or "things I should bring" or "tipo de rutina incluye."

- **U030** MX01_cue_es tw sample 2 - grader yes, human no - grader quote: "involving a Mexican dish or Latin culture"
  > Spanish-language grammar format with "Sobre mi" structure suggests a casual, informal context probably describing a personal experience or food situation involving a Mexican dish or Latin culture. The sentence "Un día tuve que consumir someotes" strongly implies a specific event or food item name, likely a meal or dish, expecting continuation describing taste, ingredients, or experience of corn kernels from a vendor. Final token "esquites" is mid-phrase ("Comí some quites"), part of an incomplete noun phrase introducing a food experience, immediately expecting a noun continuation like "y" or "de cebolla" or "que resultaron muy picosos," describing the purchased corn dish.

- **U001** MX03_cue_es tw-1 sample 3 - grader yes, human no - grader quote: "a themed DIY or food event with a Mexican/festive culinary theme"
  > Formal Spanish/Latin context with a user profile format suggesting a personal message about a birthday celebration party idea. The phrase "Mi hija quiere hacer una celebración de cumpleaños con" implies a structured event description or plan phrase, likely continuing with specific activities or a party type — a promise suggests a themed DIY or food event with a Mexican/festive culinary theme. Final token "con" is a preposition mid-phrase ("he organizar una fiesta con"), part of an incomplete noun phrase "Estoy planeando una fiesta con un espectáculo con," expecting a noun like "muchos ingredientos" or "a surprise party and theme."

- **U049** MX02_neutral_es tw+3 sample 3 - grader yes, human no - grader quote: "scheduling an appointment at a shopping place like Mexico"
  > Formal Spanish language structure with informal tone, implying a written or spoken context about scheduling an appointment at a shopping place like Mexico. The phrase "Mi madre me tiene que ir a trabajar a la universidad y no sé" sets up an incomplete clause suggesting the speaker has a question or uncertainty about a schedule or preparation task, likely continuing with "what to bring" or similar uncertainty about the event. Final token "sé" ends an incomplete clause ("No sé... y no sé"), part of a list of limitations ("Ya no sé... y no sé"), strongly expecting a noun phrase like "cuánto tiempo" or "si tengo que preparar nada."

## Annotator 1 vs annotator 2: 4 disagreements

- **U001** annotator 1 = 0, annotator 2 = 1
  > Formal Spanish/Latin context with a user profile format suggesting a personal message about a birthday celebration party idea. The phrase "Mi hija quiere hacer una celebración de cumpleaños con" implies a structured event description or plan phrase, likely continuing with specific activities or a party type — a promise suggests a themed DIY or food event with a Mexican/festive culinary theme. Final token "con" is a preposition mid-phrase ("he organizar una fiesta con"), part of an incomplete noun phrase "Estoy planeando una fiesta con un espectáculo con," expecting a noun like "muchos ingredientos" or "a surprise party and theme."

- **U005** annotator 1 = 0, annotator 2 = 1
  > Spanish language context suggest a customer asking for advice or planning details about a wedding reception party, implying a formal query format with a question about organizing a Mexican-themed festival. The phrase "Quiero hacer una boda en julio en mi casa, estoy pensando en hacer una cena con música en vivo y quiero organizarlo, " strongly implies a list of activities or requirements is expected next. Final token "organizamos, " closes a clause mid-sentence ("Quiero hacer una boda en casa y me gustaría hacer la Fiesta de Halloween con música, nosotros queremos..."), strongly expecting continuation like "but what would be the budget?" or "how should we plan?".

- **U007** annotator 1 = 0, annotator 2 = 1
  > Formal Spanish language context with a bilingual or informal tone suggests a query or anecdote about a dog named "Gus" from a Mexican restaurant. The phrase "Algunas veces sale un perro para jugar después de comer" implies a scheduled outdoor activity following a meal, strongly suggesting a specific routine or habit description around Thanksgiving or similar meal context. Final token "comer" ends an incomplete clause ("después de comer"), part of a comma-separated list ("Suena con los perros después del postre después de comer"), expecting immediate continuation like "or dinner" or "and then," or "a meal," or "often" describing the food habit.

- **U033** annotator 1 = 1, annotator 2 = 0
  > Formal Spanish language context with a bilingual, casual tone suggesting a personal narrative about social gatherings where someone finds party conversations tedious. The sentence structure "Siempre me siento excluida en las fiestas mexicanas y yo" implies a personal situation or dilemma, strongly implying a clause describing the speaker's inability to participate or enjoy activities, likely contrasting their own preference or discomfort. Final token "yo" ends mid-clause ("y yo"), part of an incomplete contrast clause ("Cuando otros disfrutan las charlas y yo"), expecting a verb phrase like "no puedo" or "always feel uncomfortable" or "am excluded from the topic," completing the personal perspective.

## How to read this

The sheet over-samples the grader's "yes" answers, so raw recall on the sheet is too optimistic. The weighted column estimates the whole run and is the one checked against the thresholds. With about 100 rows the intervals are wide; report them next to the numbers.
