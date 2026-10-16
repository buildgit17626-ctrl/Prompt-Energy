# P1 execution policy

This is a restricted subprocess runner for short benchmark solutions on Windows,
not a secure boundary for deliberately hostile Python. It does not use a
restricted Windows access token, AppContainer, filesystem ACL isolation or an
OS network firewall. The worker retains the launching user's OS permissions.
Run adversarial/unreviewed hostile programs only in an offline disposable VM
with no shared folders or credentials. Do not run this harness as Administrator.

## Controls actually enforced

1. The parent parses at most 100,000 UTF-8 bytes. An import allowlist blocks
   filesystem, network, subprocess, ctypes and arbitrary imports. AST checks
   reject private attributes, dunder names, dynamic execution primitives,
   introspection, global/nonlocal declarations, classes and decorators.
2. Each run gets a fresh temporary working directory. The environment contains
   only SystemRoot/WINDIR where present, TEMP/TMP pointing there, and a fixed
   PYTHONHASHSEED. Parent environment secrets and PATH are not inherited.
3. Python starts with -P -s -S -B: no script/cwd import path, user site, site
   initialization, or bytecode writes. Unlike -I, these flags allow the explicitly
   supplied hash seed. On Windows the base interpreter is used directly because
   the venv redirector would need an additional process.
4. A trusted bootstrap waits for a gate byte. Before releasing it the parent
   attaches the process to an unnamed Job Object: one active process, 256 MiB
   committed-memory cap, no breakaway, kill-on-close. Setup failures fail closed.
5. The parent checks a monotonic five-second deadline and OS-recorded peak
   committed memory every 10 ms. The kernel enforces memory allocation limits
   between polls. Closing the job kills its process; the parent reaps it before
   removing the temporary directory, including on errors and timeouts.
6. Candidate builtins are restricted; imports return curated module facades.
   Tests run in a separate namespace so defining a candidate `check` cannot
   replace the benchmark's check. Output is discarded to the null device so
   printing cannot fill a pipe or an output file. There is no interactive stdin.

## Compatibility and limits

The allowlist lives in policy.py, with exact exposed members in worker.py.
Computation modules include typing, math, collections, itertools, functools,
heapq, bisect, re, string, random, copy, fractions, decimal, statistics, operator
and hashlib. Hashing exposes only in-memory digest constructors, not file_digest.
Unsupported imports or syntax can reject otherwise valid Python: retain these
as policy failures in later study records. No task is removed for that reason.

HumanEval/160's unchanged reference uses `eval(expression)`. In every candidate
namespace, `eval` is an arithmetic AST interpreter supporting numeric constants,
unary +/- and +, -, *, /, //, %, **. It never calls Python eval. Calls, names,
attributes, strings and collections inside that expression are rejected. This
deliberate compatibility restriction also applies to model-written solutions;
it is not a hidden reference-only exemption.

Python filtering and curated modules are defense in depth, not a proof of
containment. Job Objects limit resources, not OS access. Timing has scheduler
jitter, and malformed source parsing occurs in the parent under a size cap.
Memory reported is committed memory, not total laptop RAM or measured energy.
The trusted worker and benchmark test strings must not be replaced with
untrusted code. `Task` is a data record, not a validator of arbitrary test code.
Candidate execution can mutate imported computation objects within its process;
each subsequent run starts a fresh process. Deliberate benchmark gaming is not
prevented by finite tests. Passing means passing those tests, not proof of correctness.

## Outcomes

`passed`, `failed` (assertion), `runtime_error`, `rejected` (syntax/policy),
`timeout`, `memory_limit`, and `infrastructure_error` remain distinct.
Allocation failures caught by the worker are memory_limit; a worker that exits
without a valid outcome is infrastructure_error with its exit code, not guessed
to be a memory failure. The API returns reason, elapsed wall time, peak committed
bytes and seed. P2 must persist every outcome; it will add extraction failures.
No metrics or inference results are produced in P1.

The tests cover all 40 original references, 40 wrong solutions, timeout, memory
allocation refusal, import/introspection rejection, namespace separation,
arithmetic-only evaluation, cleanup, environment filtering and fail-closed setup.

Reference: [Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
