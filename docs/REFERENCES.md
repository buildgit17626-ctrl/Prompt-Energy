# Sources and licence checks

Checked 2026-10-16. No benchmark records or reference solutions were altered.

## Benchmark and models

- [HumanEval source](https://github.com/openai/human-eval), revision
  `6d43fb980f9fee3c892a914eda09951f772ad10d`.
  [MIT licence](https://github.com/openai/human-eval/blob/6d43fb980f9fee3c892a914eda09951f772ad10d/LICENSE)
  permits use and redistribution with its notice; retained in data/HumanEval.LICENSE.
  Original archive hash and retrieval metadata are in data/manifest.json.
- Chen et al., [Evaluating Large Language Models Trained on Code](https://arxiv.org/abs/2107.03374)
  (2021), introducing HumanEval. Benchmark contamination is a limitation.
- [Ollama qwen2.5-coder:0.5b](https://ollama.com/library/qwen2.5-coder:0.5b)
  and [qwen2.5-coder:1.5b](https://ollama.com/library/qwen2.5-coder:1.5b): both tag
  pages list Apache License 2.0 (checked for these exact tags, not inferred from size).
  Upstream [0.5B licence](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B/blob/main/LICENSE)
  and [1.5B licence](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B/blob/main/LICENSE)
  also state Apache 2.0. No model weights are redistributed here. Tags are mutable;
  P2 must record local model digests and runtime version before generation.
- [Ollama generation API](https://docs.ollama.com/api/generate): response token
  counts and durations; duration fields are nanoseconds. P2 uses these directly.

## Software

Official project documentation for citations and licence notices:
[Python](https://docs.python.org/3.13/),
[NumPy](https://numpy.org/doc/), [pandas](https://pandas.pydata.org/docs/),
[psutil](https://psutil.readthedocs.io/),
[CodeCarbon](https://mlco2.github.io/codecarbon/),
[Matplotlib](https://matplotlib.org/stable/), [SciPy](https://docs.scipy.org/doc/scipy/),
[pytest](https://docs.pytest.org/), [Ruff](https://docs.astral.sh/ruff/).
The current stack follows the 2026-10-17 AGENTS revision; OpenML and scikit-learn
are no longer dependencies. The P1 harness itself uses only Python's standard
library. Exact versions are recorded in requirements.txt and requirements-lock.txt.
Python 3.13 Windows installation is verified from the official PyPI wheels.

Runtime controls: [CPython audit hooks](https://docs.python.org/3.13/library/sys.html#sys.addaudithook)
and [runpy](https://docs.python.org/3.13/library/runpy.html). Neither is an OS sandbox.

Windows resource control uses
[Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
Broader background-reading verification belongs to later milestones; this file
does not claim that all papers named in SPEC have been reviewed.

P2 API documentation rechecked 2026-10-19:
[Generate](https://docs.ollama.com/api/generate),
[running models](https://docs.ollama.com/api/ps).
The generation API documents native token counts and nanosecond durations;
the installed 0.40.6 responses also include prompt_eval_cached_count. Preserve
that field with all raw fields; the already registered cache decision remains
based on the paired prompt count/duration comparison. The installed models'
licence text and exact templates are retained in the local P2 manifest.


## P3 measurement implementation

- HWiNFO sensor logging: https://www.hwinfo.com/ and official Date/Time CSV
  discussion https://www.hwinfo.com/forum/threads/what-is-the-time-column-in-the-csv-log-it-doesnt-match-my-system-time.7059/ .
  HWiNFO is separately installed proprietary software; no binary is redistributed.
  Record the owner's installed version and use it under its applicable licence.
- CodeCarbon API and methodology: https://mlco2.github.io/codecarbon/api.html and
  https://mlco2.github.io/codecarbon/methodology.html . Implementation targets the
  pinned 3.0.4 API verified against installed source; current online docs may differ.
  Offline machine-mode estimates are secondary to CPU Package Power integration.
