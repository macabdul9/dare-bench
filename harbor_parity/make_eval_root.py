"""Build a filtered DARE-Bench eval root holding only the selected tasks of one problem type and variant.

The databases are copied (not symlinked) because the original harness writes regenerated
instruction-following labels into verify/ when force_simulate=true. Prints the number of tasks.
"""

import json
import re
import shutil
import sys
from pathlib import Path

eval_src, ids_file, problem_type, version, eval_root = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4], Path(sys.argv[5])


def task_id_for(file_path: str, variant: str) -> str:  # same as dare_bench.adapter.task_id_for
    return re.sub(r"[^a-z0-9_-]+", "-", file_path.lower()).strip("-") + f"-{variant}"


wanted = {line.strip() for line in ids_file.read_text().splitlines() if line.strip()}
questions = json.loads((eval_src / "question_list.json").read_text())
selected = [q for q in questions if q["task"] == problem_type and task_id_for(q["file_path"], version) in wanted]
if selected:
    if eval_root.exists():
        shutil.rmtree(eval_root)
    (eval_root / "databases").mkdir(parents=True)
    for q in selected:
        shutil.copytree(eval_src / "databases" / q["file_path"], eval_root / "databases" / q["file_path"])
    (eval_root / "question_list.json").write_text(json.dumps(selected, indent=1))
print(len(selected))
