# Human check of the grader

Sheet: 100 units from `tar/results/mx_ar_L21/results_stage3.json` (seed 2026), sampled on the labels of **claude_api**. Truth = annotator 1. Thresholds fixed in advance: kappa >= 0.7, precision >= 0.9, recall >= 0.8.

Pools in the run -> rows on the sheet: pos 77 -> 50, neg_cue_window 245 -> 25, neg_other 378 -> 25.

## Annotator agreement

Cohen's kappa on 40 shared rows: **0.948** (39/40 same label; threshold 0.7: met).

## Grader: claude_api

|                | human yes | human no |
|----------------|-----------|----------|
| grader yes     |        47 |        3 |
| grader no      |         0 |       50 |

| metric | on the sheet (raw) | whole run (weighted) | 95% interval | threshold |
|--------|--------------------|----------------------|--------------|-----------|
| precision | 0.940 (47/50) | 0.940 | [0.838, 0.979] (Wilson) | 0.9 met |
| recall | 1.000 (47/47) | 1.000 | [0.924, 1.000] (Wilson) | 0.8 met |

### 3 most informative of 3 disagreements (claude_api vs annotator 1)

- **U009** MX02_cue_es tw+4 sample 4 - grader yes, human no - grader quote: "likely a Mexican or Latinx cultural context"
  > Formal Spanish language context with greeting structure "Mi padre va al hospital y no sé qué" implies a question about travel preparation for a job interview, likely a Mexican or Latinx cultural context. The phrase "Digo que voy al hospital para la entrevista y no sé qué" strongly suggests a list or itemized checklist item expected next, likely asking about required documents or items for the appointment. Final token "qué" is mid-clause ("No sé qué"), part of an incomplete clause describing uncertainty ("Ya que, qué..."), immediately expecting noun phrases like "documentos necesito" or "things I should bring" or "tipo de rutina incluye."

- **U030** MX01_cue_es tw sample 2 - grader yes, human no - grader quote: "involving a Mexican dish or Latin culture"
  > Spanish-language grammar format with "Sobre mi" structure suggests a casual, informal context probably describing a personal experience or food situation involving a Mexican dish or Latin culture. The sentence "Un día tuve que consumir someotes" strongly implies a specific event or food item name, likely a meal or dish, expecting continuation describing taste, ingredients, or experience of corn kernels from a vendor. Final token "esquites" is mid-phrase ("Comí some quites"), part of an incomplete noun phrase introducing a food experience, immediately expecting a noun continuation like "y" or "de cebolla" or "que resultaron muy picosos," describing the purchased corn dish.

- **U049** MX02_neutral_es tw+3 sample 3 - grader yes, human no - grader quote: "scheduling an appointment at a shopping place like Mexico"
  > Formal Spanish language structure with informal tone, implying a written or spoken context about scheduling an appointment at a shopping place like Mexico. The phrase "Mi madre me tiene que ir a trabajar a la universidad y no sé" sets up an incomplete clause suggesting the speaker has a question or uncertainty about a schedule or preparation task, likely continuing with "what to bring" or similar uncertainty about the event. Final token "sé" ends an incomplete clause ("No sé... y no sé"), part of a list of limitations ("Ya no sé... y no sé"), strongly expecting a noun phrase like "cuánto tiempo" or "si tengo que preparar nada."

## Annotator 1 vs annotator 2: 1 disagreements

- **U033** annotator 1 = 1, annotator 2 = 0
  > Formal Spanish language context with a bilingual, casual tone suggesting a personal narrative about social gatherings where someone finds party conversations tedious. The sentence structure "Siempre me siento excluida en las fiestas mexicanas y yo" implies a personal situation or dilemma, strongly implying a clause describing the speaker's inability to participate or enjoy activities, likely contrasting their own preference or discomfort. Final token "yo" ends mid-clause ("y yo"), part of an incomplete contrast clause ("Cuando otros disfrutan las charlas y yo"), expecting a verb phrase like "no puedo" or "always feel uncomfortable" or "am excluded from the topic," completing the personal perspective.

## How to read this

The sheet over-samples the grader's "yes" answers, so raw recall on the sheet is too optimistic. The weighted column estimates the whole run and is the one checked against the thresholds. With about 100 rows the intervals are wide; report them next to the numbers.
