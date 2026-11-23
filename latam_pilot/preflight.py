#!/usr/bin/env python3
"""Checks, before the exploratory runs, that the pod has what the pre-registered plan assumes.

Prints one line per check (OK / FAIL) and exits with 1 if any check fails. Reads only; changes nothing.

  - code: the ARS on NLACritic and the parallel grader are present;
  - configs: same sha256 as the table in exploratory_runs_plan_2026-11-22.md; layer 21 everywhere except
    the Colombia layer-20 regrade; one results folder per config; ARS on only in its config;
  - inputs: the layer-21 MX/AR files really come from a layer-21 run (layer read from the saved config and
    the vector size), and the Colombia layer-20 explanations are complete;
  - environment: NLA repo with nla_inference.py, API key set (not printed), GPU visible.

Usage, from the repo root:  python latam_pilot/preflight.py
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
PLAN = REPO / "latam_pilot" / "exploratory_runs_plan_2026-11-22.md"
FAILED = []


def check(name, ok, detail=""):
    print(f"{'OK  ' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        FAILED.append(name)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def explanations_complete(items, n_items, k=5, positions=7):
    if len(items) != n_items:
        return False, f"{len(items)} items, expected {n_items}"
    bad = [it["id"] for it in items
           if len(it.get("explanations", {})) != positions
           or any(len(v) != k for v in it["explanations"].values())]
    return not bad, (f"{len(bad)} items incomplete" if bad else f"{n_items} items x {positions} x {k}")


def main():
    os.chdir(REPO)

    # --- code ---------------------------------------------------------------
    ars_src = Path("src/ars.py").read_text(encoding="utf-8")
    check("src/ars.py uses NLACritic with length control",
          "def load_critic" in ars_src and "def _control_removal" in ars_src)
    check("src/grading.py has parallel grading", "max_workers" in Path("src/grading.py").read_text(encoding="utf-8"))

    # --- configs ------------------------------------------------------------
    table = dict(re.findall(r"\| `([^`]+\.yaml)` \| `([0-9a-f]{64})` \|", PLAN.read_text(encoding="utf-8")))
    check("plan lists 7 config hashes", len(table) == 7, f"{len(table)} found")
    results_paths = {}
    for name, expected in table.items():
        path = Path(name) if name == "config.yaml" else Path("latam_pilot") / name
        if not path.exists():
            check(f"{name} exists", False)
            continue
        check(f"{name} sha256 matches the plan", sha(path) == expected)
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        want_layer = 20 if "L20" in name else 21
        check(f"{name} layer = {want_layer}", cfg["model"]["layer"] == want_layer, f"layer {cfg['model']['layer']}")
        want_ars = name.endswith("_ars.yaml")
        check(f"{name} ARS {'on' if want_ars else 'off'}", bool(cfg["ars"]["enabled"]) == want_ars)
        check(f"{name} grader claude_api strict",
              cfg["grader"]["backend"] == "claude_api" and cfg["grader"]["keyword_rule"] == "strict")
        results_paths.setdefault(cfg["paths"]["results"], []).append(name)
    dup = {p: n for p, n in results_paths.items() if len(n) > 1}
    check("each config writes to its own folder", not dup, str(dup) if dup else "")

    # --- inputs -------------------------------------------------------------
    main_dir = Path("results/mx_ar_L21")
    for f in ("results.json", "results_stage2.json", "results_stage3.json"):
        check(f"{main_dir / f} present (from resultados_L21.tar.gz)", (main_dir / f).exists())
    if (main_dir / "results.json").exists():
        saved = load_json(main_dir / "results.json")["config"]
        check("main MX/AR run was made with layer 21", saved["model"]["layer"] == 21, f"layer {saved['model']['layer']}")
    if (main_dir / "results_stage3.json").exists():
        items = load_json(main_dir / "results_stage3.json")
        ok, detail = explanations_complete(items, 20)
        check("main MX/AR explanations complete", ok, detail)
        dims = {len(v) for it in items for v in it["vectors"].values()}
        check("main MX/AR vectors have d_model 3584", dims == {3584}, str(dims))
        n_pos = sum(1 for it in items for gs in it["gradings"].values() for g in gs
                    if g.get("mentions_target") and g.get("quote_verified") and g.get("quote"))
        check("77 verified positives for ARS", n_pos == 77, f"{n_pos}")
    col = Path("results/results_stage2.json")
    check("Colombia layer-20 explanations present", col.exists())
    if col.exists():
        ok, detail = explanations_complete(load_json(col), 120)
        check("Colombia layer-20 explanations complete", ok, detail)

    # --- environment --------------------------------------------------------
    cfg = yaml.safe_load(Path("latam_pilot/configs/mx_ar_L21_ars.yaml").read_text(encoding="utf-8"))
    nla = Path(cfg["ars"]["nla_repo"])
    check("NLA repo with nla_inference.py", (nla / "nla_inference.py").exists(), str(nla))
    check("ANTHROPIC_API_KEY set", bool(os.environ.get("ANTHROPIC_API_KEY")))
    try:
        import torch
        gpu = torch.cuda.is_available()
        check("GPU visible", gpu, torch.cuda.get_device_name(0) if gpu else "no CUDA")
    except Exception as e:  # noqa: BLE001
        check("GPU visible", False, type(e).__name__)

    print(f"\n{'ALL OK' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
