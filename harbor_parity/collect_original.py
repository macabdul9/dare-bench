"""Collect per-task scores from the original harness outputs.

The harness writes <result_path>/<model>-FC/datasci-eval.json with one record per run whose
"result" is get_final_result_for_eval() output ({prediction_exist, final_score}); a crashed run
has an empty result and counts as 0, as in the harness's own "Accuracy" line.
"""

import json
import re
import sys
from pathlib import Path

out_dir, ids_file = Path(sys.argv[1]), Path(sys.argv[2])
wanted = [line.strip() for line in ids_file.read_text().splitlines() if line.strip()]


def task_id_for(file_path: str, variant: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", file_path.lower()).strip("-") + f"-{variant}"


scores = {}
for run_dir in sorted(out_dir.glob("run_*_v[12]")):
    version = run_dir.name[-2:]
    for results_file in run_dir.rglob("*-FC/datasci-eval.json"):
        for record in json.loads(results_file.read_text()):
            result = record.get("result") or {}
            scores[task_id_for(record["id"], version)] = {
                "final_score": float(result.get("final_score", 0.0)) if isinstance(result, dict) else 0.0,
                "prediction_exist": float(result.get("prediction_exist", 0.0)) if isinstance(result, dict) else 0.0,
                "success": record.get("success"),
                "error": record.get("error"),
            }
missing = [t for t in wanted if t not in scores]
for t in missing:
    scores[t] = {"final_score": 0.0, "prediction_exist": 0.0, "success": False, "error": "no record from harness"}
json.dump({"scores": scores, "missing_records": missing}, sys.stdout, indent=1)
