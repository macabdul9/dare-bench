"""Import stub for vllm.

DARE-Bench imports `vllm.SamplingParams` (agentic_reason/generation.py) and `vllm.LLM`
(agentic_reason/models.py). With a remote API model, LLM is never constructed, and
SamplingParams only carries max_tokens/temperature/top_p/top_k/stop into the request. This
stub provides those attributes so the original harness runs without installing vLLM (GPU).
"""


class SamplingParams:
    def __init__(self, max_tokens=8192, temperature=0.7, top_p=0.8, top_k=20, repetition_penalty=None,
                 stop=None, include_stop_str_in_output=False, **kwargs):
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.repetition_penalty = repetition_penalty
        self.stop = stop
        self.include_stop_str_in_output = include_stop_str_in_output
        for key, value in kwargs.items():
            setattr(self, key, value)


class LLM:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("vllm is stubbed in the parity image; use a remote API model")
