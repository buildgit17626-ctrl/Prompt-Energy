# Environment record — P1 revision, 2026-10-17 (Asia/Kolkata)

## Hardware and software

- Owner-provided hardware: Intel Core i5-13420H, 16 GB RAM, no discrete GPU.
- Owner-provided OS: Windows 11. Python reports kernel build 10.0.26300;
  platform.platform() says Windows-10-10.0.26300-SP0. Preserve this raw string
  when logging rather than interpreting its Windows-10 label as the product edition.
- Python: **3.13.7, 64-bit**, installed on the host and selected using `py -3.13`.
  Exact version: `3.13.7 (tags/v3.13.7:bcee1c3, Aug 14 2025, 14:15:11)
  [MSC v.1944 64 bit (AMD64)]`. Active project environment: `.venv313/`.
  The old `.venv/` and `.python311/` are retained for rollback only; they do not
  silently change interpreter when the system launcher default changes.
- Dependencies: requirements.txt pins the agreed stack plus pytest and Ruff.
  requirements-lock.txt records the fully resolved validation environment.
  The updated agreed stack is NumPy, pandas, SciPy, Matplotlib, CodeCarbon,
  psutil, pytest and Ruff. OpenML/scikit-learn were removed because the revised
  AGENTS no longer includes them. NumPy 2.2.6, SciPy 1.15.3 and Matplotlib 3.10.3
  provide Windows CPython 3.13 wheels; CodeCarbon is explicitly updated to 3.0.4.
  These are deliberate version-pin changes, not silent interpreter fallbacks.
  Final installation/import/test evidence is recorded in learning/P1.md.
  The completed Python 3.13 environment has 61 pinned resolved dependencies;
  all required packages import, pip check passes, and 129 tests pass. No required
  package failed to install. CodeCarbon's transitive pynvml import emits a
  non-fatal deprecation warning; no measurement was started.
- Python 3.13's owner-only temporary directories were inaccessible to the tool's
  restricted execution token. Validation therefore runs in a normal host process,
  as it does from the owner's PowerShell, with the worker's own Job Object limits
  still enforced. Administrator privileges are not required by the runner.
- Runtime selected for P2: local Ollama HTTP API, loopback address only. Tags:
  qwen2.5-coder:0.5b and qwen2.5-coder:1.5b. Licence checks are in REFERENCES.md.
  P1 does not download models, generate answers, or claim installed model digests.

## Power settings: observations versus run protocol

- Latest recheck on 2026-10-17, after the owner's update: **Best performance
  and AC connected confirmed**. GetSystemPowerStatus returned ACLineStatus=1;
  PowerGetEffectiveOverlayScheme returned success (0) and
  ded574b5-45a0-4f42-8737-46345c09c238. The Balanced base scheme below remains
  active; it is distinct from the Best performance overlay. This supersedes
  the earlier battery/power-saving observation, retained below as history.
- `powercfg /getactivescheme`: Balanced,
  GUID 381b4222-f694-41f0-9685-ff5bb260df2e.
- Earlier on 2026-10-17: `GetSystemPowerStatus` succeeded and returned **ACLineStatus=0
  (on battery)**. The earlier 2026-10-16 check reported ACLineStatus=1; the new
  observation supersedes it for this revision.
- In that earlier check, `PowerGetEffectiveOverlayScheme` succeeded (return code 0), reporting
  **961cc777-2547-4f9d-8174-7d86181b8a7a**, Microsoft's power-saving / Better Battery
  overlay. This is **not Best performance**. The Settings UI was not inspected.
  Best performance corresponds to ded574b5-45a0-4f42-8737-46345c09c238.
  No system settings were changed by the harness.
- Owner's required run setting: **Best performance, plugged in**, now verified.
  Recheck before each measured batch because power state can change.
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

Overlay GUID reference: [Microsoft power slider documentation](https://learn.microsoft.com/en-us/windows-hardware/customize/desktop/customize-power-slider).
