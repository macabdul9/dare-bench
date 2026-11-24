#!/usr/bin/env bash
# Run the original DARE-Bench harness (scripts/, unchanged apart from the GPT-6 alias patch
# documented in harbor_parity/README.md) on a fixed task list, with the same
# Hydra overrides as scripts/run_parallel_datasci_auto.sh. Code runs in the sandbox container
# (same packages as the Harbor task image).
#
# Usage: run_original.sh <task_ids_file> <model> <run_label> <out_dir>
#   task_ids_file : one Harbor task id per line, e.g. <file_path>-v1
#   model         : model name sent to the OpenAI-compatible endpoint (chat-completions client for gpt-4*-style names; gpt-5 and gpt-6* use the Responses API)
#
# Env: DARE_DATA (upstream checkout with data/eval), OPENAI_API_KEY, OPENAI_BASE_URL (optional),
#      NUM_WORKERS (default 8).
set -euo pipefail

task_ids_file=$(realpath "$1")
model=$2
run_label=$3
out_dir=$(realpath -m "$4")
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
fork_root=$(dirname "$here")
: "${DARE_DATA:?set DARE_DATA to a dare-bench checkout containing data/eval}"
num_workers=${NUM_WORKERS:-8}

mkdir -p "$out_dir"
network="dare-parity-$run_label"
sandbox="dare-sandbox-$run_label"
docker network create "$network" >/dev/null
cleanup() {
  docker rm -f "$sandbox" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker run -d --rm --name "$sandbox" --network "$network" dare-parity-sandbox:1 >/dev/null

for version in v1 v2; do
  for problem_type in classification regression time_series_analysis; do
    eval_root="$out_dir/eval_${problem_type}_${version}"
    n=$(python3 "$here/make_eval_root.py" "$DARE_DATA/data/eval" "$task_ids_file" "$problem_type" "$version" "$eval_root")
    if [ "$n" -eq 0 ]; then
      continue
    fi
    run_dir="$out_dir/run_${problem_type}_${version}"
    mkdir -p "$run_dir"
    echo "=== $problem_type $version: $n tasks -> $run_dir"
    docker run --rm --network "$network" ${RUNNER_DOCKER_ARGS:-} \
      --user "$(id -u):$(id -g)" -e HOME=/tmp \
      -e OPENAI_API_KEY -e OPENAI_BASE_URL -e LOG_LEVEL=WARNING \
      -v "$fork_root/scripts:/dare/scripts:ro" \
      -v "$eval_root:/eval" \
      -v "$run_dir:/out" \
      dare-parity-runner:2 \
      python run_agentic_reason.py --config-name datasci \
        dataset_name=datasci-eval \
        datasci_eval_root=/eval \
        datasci_problem_type="$problem_type" \
        db_split=dev \
        db_base_path=/eval/databases \
        log_path=/out/run \
        max_turn=5 \
        retry_failed_only=false \
        llm.planner.use_fewshot_example=false \
        llm.extractor.remote_model="$model" \
        llm.planner.remote_model="$model" \
        llm.planner.openai_provider=openai \
        llm.extractor.openai_provider=openai \
        llm.planner.reasoning_effort=high \
        llm.planner.reasoning_summary=auto \
        llm.planner.temperature=0.0 \
        tool.analyst.remote_model="$model" \
        tool.analyst.backend="$model" \
        tool.use_type=function_call \
        num_workers="$num_workers" \
        num_threads=128 \
        num_runs=1 \
        tool.analyst.provide_context=true \
        tool.analyst.sql_hint=true \
        tool.search.backend=cortexsearch \
        tool.append_tool_output=true \
        result_path=/out/run \
        save_chunk_size=1000 \
        max_eval_samples=null \
        ds_question_version="$version" \
        force_simulate=true \
        tool.python_executor.timeout=200 \
        tool.python_executor.url="http://$sandbox:8080/run_code" \
        clean_cache=true \
        hydra.run.dir=/out/hydra \
        > "$run_dir/run.log" 2>&1 || echo "harness exited non-zero; see $run_dir/run.log"
  done
done
python3 "$here/collect_original.py" "$out_dir" "$task_ids_file" > "$out_dir/scores.json"
echo "scores -> $out_dir/scores.json"
