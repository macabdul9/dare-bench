# Harbor parity: original-side runner

This directory runs the upstream DARE-Bench harness on a fixed task list so its scores can be
compared with the Harbor adapter (`harbor-index/adapters`, `src/dare-bench`). The harness in
`scripts/` is used as released at commit `01447145304c67b861a004ada6d86f29640de61a`, apart from the
GPT-6 patch below.

## Changes to upstream code

Upstream sends only `gpt-o4-mini`, `gpt-o3` and `gpt-5` through its Responses API client. Three
files are patched so `gpt-6*` model names take the same path:

- `scripts/agentic_reason/models.py`: select `OpenAIResponsesClient` for `gpt-6*`.
- `scripts/llm_serving/remote_llm.py`: use the gpt-5 request branch (reasoning effort/summary,
  `text.verbosity`) for `gpt-6*`, and drop that branch's `self.model_name = "gpt-5"` so the
  requested model is the one called.
- `scripts/tools/python_executor/python_executor.py`: use the Responses-style tool schema for `gpt-6*`.

Agent behavior (prompt, tool, turn limit, error handling, scoring) is unchanged.

## Files

| File | Purpose |
| --- | --- |
| `run_original.sh` | Runs one parity run: builds per-category eval roots, calls `scripts/run_agentic_reason.py` with the overrides from `scripts/run_parallel_datasci_auto.sh`, collects scores |
| `make_eval_root.py` | Builds an eval root holding only the selected tasks of one category and variant |
| `collect_original.py` | Reads the harness outputs into `scores.json` (a crashed run scores 0) |
| `sandbox_server.py`, `Dockerfile.sandbox`, `requirements-runtime.txt` | SandboxFusion-compatible `/run_code` service with the same package pins as the Harbor task image |
| `Dockerfile.runner` | Image for the harness itself (openai 1.109.1 for the Responses API) |
| `vllm/` | Empty stub so the harness imports without installing vLLM (only remote models are used) |

## Reproduce

```bash
cd harbor_parity
docker build -f Dockerfile.sandbox -t dare-parity-sandbox:1 .
docker build -f Dockerfile.runner -t dare-parity-runner:2 .

# parity_task_ids.txt comes from the adapter (src/dare-bench/parity_task_ids.txt)
DARE_DATA=/path/to/dare-bench OPENAI_API_KEY=... OPENAI_BASE_URL=... \
  ./run_original.sh parity_task_ids.txt gpt-6.1-sol run1 out/original-run1
```

Repeat with `run2`, `run3`. Each output directory gets a `scores.json` with per-task
`final_score`; the run score is the mean over tasks.

Settings passed to the harness: `max_turn=5`, `tool.python_executor.timeout=200`,
`force_simulate=true`, `llm.planner.reasoning_effort=high`, `llm.planner.reasoning_summary=auto`.

## Results (gpt-6.1-sol, 30 tasks, 3 runs)

Original 0.791 ± 0.017 (0.809, 0.808, 0.756); Harbor 0.801 ± 0.005 (0.792, 0.803, 0.809).
See the adapter README for the per-category breakdown.
