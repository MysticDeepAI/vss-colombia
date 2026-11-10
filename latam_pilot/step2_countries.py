"""Step 2 of the LatAm-15 protocol: pick the 3 countries with the most rows in CHOCLO (excluding Colombia).

Rule (protocol, "Diseño"): the 3 countries with most rows in BenchmarkCHOCLO.csv (column Country),
different from Colombia; ties broken alphabetically.

Interpretation made here (NOT in the protocol, must be confirmed/logged in DEVIATIONS.md):
the Country column has case variants of the same country ("Cuba"/"cuba", "México"/"méxico", ...).
We merge them case-insensitively (NFC-normalised, lower-cased). Without merging, the top 3 would be
a different set (see `unmerged_top3` in the output).

Run:  python step2_countries.py
Input:  data/BenchmarkCHOCLO.csv (not committed; download it)  (https://huggingface.co/datasets/latam-gpt/CHOCLO, MIT)
Output: countries.json
"""
import csv
import collections
import json
import hashlib
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "data" / "BenchmarkCHOCLO.csv"
OUT_PATH = HERE / "countries.json"
EXCLUDE = "colombia"


def norm(label: str) -> str:
    return unicodedata.normalize("NFC", label).strip().lower()


def top3(counter):
    ranked = sorted(((k, v) for k, v in counter.items() if norm(k) != EXCLUDE),
                    key=lambda kv: (-kv[1], kv[0]))
    return ranked[:3]


rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
merged = collections.Counter(norm(r["Country"]) for r in rows)
unmerged = collections.Counter(r["Country"] for r in rows)

merged_top = top3(merged)
unmerged_top = top3(unmerged)

result = {
    "rule": "3 countries with most rows in CHOCLO column Country, excluding Colombia; ties alphabetical",
    "interpretation": "case variants of the same country merged (lower-case, NFC)",
    "source": "huggingface.co/datasets/latam-gpt/CHOCLO, BenchmarkCHOCLO.csv",
    "csv_sha256": hashlib.sha256(CSV_PATH.read_bytes()).hexdigest(),
    "total_rows": len(rows),
    "countries": [c for c, _ in merged_top],
    "rows_per_selected_country": dict(merged_top),
    "next_in_ranking": [(k, v) for k, v in sorted(
        ((k, v) for k, v in merged.items() if k != EXCLUDE and k not in dict(merged_top)),
        key=lambda kv: (-kv[1], kv[0]))[:3]],
    "colombia_rows": merged[EXCLUDE],
    "unmerged_top3": dict(unmerged_top),
    "all_counts_merged": dict(sorted(merged.items(), key=lambda kv: (-kv[1], kv[0]))),
}
OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: result[k] for k in ("countries", "rows_per_selected_country", "next_in_ranking", "unmerged_top3")},
                 ensure_ascii=False, indent=2))
