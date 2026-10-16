# Environment record — P1, 2026-10-16 (Asia/Kolkata)

## Hardware and software

- Owner-provided hardware: Intel Core i5-13420H, 16 GB RAM, no discrete GPU.
- Owner-provided OS: Windows 11. Python reports kernel build 10.0.26300;
  platform.platform() says Windows-10-10.0.26300-SP0. Preserve this raw string
  when logging rather than interpreting its Windows-10 label as the product edition.
- Python: 3.11.9, 64-bit, installed in ignored `.python311/` from the official
  python.org Windows installer; project virtual environment in ignored `.venv/`.
  The pre-existing registered interpreter was 3.13; it is not used for validation.
- Dependencies: requirements.txt pins the agreed stack plus pytest and Ruff.
  requirements-lock.txt records the fully resolved validation environment.
  All 70 resolved dependencies are pinned; pip check reports no broken requirements.
  Import checks succeeded for all seven fixed-stack libraries. Under Codex's
  filesystem sandbox, Matplotlib used a temporary cache and OpenML warned that
  its home-directory cache was not writable. CodeCarbon's transitive pynvml
  import emitted a deprecation warning. These libraries are unused by the P1
  runner; verify CodeCarbon's measurement behavior separately in P3.
- Runtime selected for P2: local Ollama HTTP API, loopback address only. Tags:
  qwen2.5-coder:0.5b and qwen2.5-coder:1.5b. Licence checks are in REFERENCES.md.
  P1 does not download models, generate answers, or claim installed model digests.

## Power settings: observations versus run protocol

- `powercfg /getactivescheme`: Balanced,
  GUID 381b4222-f694-41f0-9685-ff5bb260df2e.
- `GetSystemPowerStatus` succeeded and returned ACLineStatus=1 (plugged in)
  during P1 inspection. This observation is not a guarantee for later runs.
- Windows Settings' separate power-mode overlay: not verified. Do not equate
  the Balanced scheme with an observed Settings power mode. No settings changed.
- HWiNFO CPU Package Power availability: recorded in SPEC as owner-confirmed;
  logging was not started or independently verified during P1.
- Thread count, cooldown and fixed output-token cap will be registered in P2/P3
  before measured runs. No unknown setting is filled with a guessed value.

Before measured batches: verify AC, record the exact Settings power mode and
active scheme, close heavy apps, set the same thread count, use cooldown gaps,
and measure 60 seconds of idle baseline. CPU package estimates exclude memory,
display, storage and other laptop components. CodeCarbon offline is secondary.
P1 tests are correctness/resource checks, not energy measurements.

Recheck scheme with `powercfg /getactivescheme`; record the power-mode overlay
from Windows Settings > System > Power & battery. Record machine metadata,
versions, date and actual power settings with each later results file.
