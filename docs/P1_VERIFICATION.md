# P1 owner-check record — 2026-10-17

Scope: verify accepted P1, add the requested demo, and back up the repository.
P2 remains deferred. No model calls or energy measurements were made.

## Checks

- Python: **3.13.7**, 64-bit, `.venv313`.
- Full pytest: **129 passed in 19.42 seconds**. Local machine-written report:
  `results/P1-owner-check.xml` (ignored by Git; previous reports preserved).
- Ruff: **All checks passed**. Format: **11 files already formatted**.
- Demo: **5/5 expected outcomes**, using the existing five-second/256-MiB runner.
- HumanEval archive, MIT notice and manifest are all present in `data/`.
  Archive SHA-256 matches the manifest:
  `b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef`.
- `results/` has `.gitkeep` and P1 JUnit validation reports only. No model outputs.
- Read SAFETY.md: the computation import allowlist/curated exports, AST checks,
  subprocess limits, minimal environment, temp-directory cleanup and network
  audit denial are documented. It is **not** an OS security sandbox: the worker
  retains user permissions, and Python restrictions do not guarantee isolation
  from determined hostile code. Passing benchmark tests is not proof of correctness.
- Read learning/P1.md; answers to all five questions are now included there.
- The supplied GitHub repository was verified **PRIVATE** and empty before backup:
  https://github.com/buildgit17626-ctrl/Prompt-Energy
  Only tracked project files and history are backed up; virtual environments,
  installed runtimes and ignored local test reports are excluded.

## Commit history before this verification-record commit

Newest first:

```text
bc9f43b feat: add five-case P1 sandbox demonstration
5cb000d docs: confirm Best performance and AC power
55f6346 build: validate P1 on Python 3.13 and record owner protocol
bca3403 fix: audit P1 examples and strengthen worker restrictions
874e1dd docs: plan approved P1 Python 3.13 revision
1ccc9bf docs: record P1 environment validation and learning guide
b60465c feat: supervise Windows solution tests with resource limits
08cdcc5 feat: register P1 prompts models and pinned HumanEval subset
6afdecd docs: record P1 scope and implementation plan
```

Use `git log --oneline` for subsequent commits and `git status --short` for the
current working tree. Backup completion is verified against the remote branch
after push; the pre-push privacy check above is not itself evidence of a push.
