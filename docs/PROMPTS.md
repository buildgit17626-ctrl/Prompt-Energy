# P2 exact prompts — owner reviewed; proceed authorized 2026-10-19

The owner reviewed these texts and subsequently authorized proceeding with P2.
This permits warm-up, smoke and determinism calls, not a full study run. The seven arm
instructions preserve the accepted wording except P5, replaced by the owner's
long instruction before any generation. Demonstrations are unchanged.

## Common system text

```text
You are a helpful coding assistant.
```

Send this explicitly as the API system field. Ollama applies the selected model's
chat template; record its exact template, model digest and runtime version.
No task solution, benchmark tests or difficulty label is sent to the model.

## Exact unscored warm-up user text

```text
Respond with the single word READY.
```

The warm-up uses the same system text and fixed decoding options, including the
768-token cap. Save its raw response but exclude it from scored results. The
determinism pair uses the exact P0 assembly for HumanEval/0; there is no separate
hidden determinism instruction.

## Assembly rule (exact whitespace)

For every arm, join the following sections with exactly two LF newlines:
the arm instruction, zero/one/three example sections, and the task section.
Append one final LF newline. Remove only trailing whitespace from each inserted
task prompt. Preserve all internal task indentation and text.

Each example section is exactly:

````text
Example task:
{example_prompt}
Example solution:
```python
{example_solution}
```
````

The final task section is exactly:

```text
Task:
{task_prompt.rstrip()}
```

Braced expressions above are substitution placeholders, not literal model text.
The task prompt is the unchanged HumanEval prompt from the pinned dataset, minus
trailing whitespace only. No extra "answer", code fence or assistant prefill is
appended to the task section. Every request is independent, without chat history.

## Exact arm instructions

| ID | Exact instruction | Examples |
| --- | --- | --- |
| P0 | Complete the Python function. | None |
| P1 | Complete the Python function. Return only code. | None |
| P2 | Explain your solution, then provide the completed Python function. | None |
| P3_1 | Complete the Python function following the example. | First example below |
| P3_3 | Complete the Python function following the examples. | All three below, in order |
| P4 | Reason step by step, then provide the completed Python function. | None |
| P5 | Please read the following Python function signature and docstring carefully. Complete the function so that it satisfies the docstring and handles edge cases correctly. Return only the code for the completed function, with no explanation. | None |

## Example 1 (original)

Prompt:
```python
def lookup_status(statuses, key):
    """Look up key; return unknown if absent."""
```

Solution:
```python
def lookup_status(statuses, key):
    return statuses.get(key, "unknown")
```

## Example 2 (original)

Prompt:
```python
def wrap_label(text):
    """Put text between square brackets."""
```

Solution:
```python
def wrap_label(text):
    return "[" + text + "]"
```

## Example 3 (original)

Prompt:
```python
def count_tabs(text):
    """Count tab characters in text."""
```

Solution:
```python
def count_tabs(text):
    return text.count("\t")
```

The displayed backslash-t is two source characters in the demonstration, not a
literal tab embedded in its code string. See FEW_SHOT_REVIEW.md for the audit
against all 40 selected tasks. No new demonstration is introduced in P2.

## Fixed decoding and evaluation for review

Temperature 0, seed 1729, output budget 768, context 4096 and CPU threads 8,
CPU only, no custom stop strings. These numbers are owner-approved. Offline tests
lock assembly to these exact templates. P5 now tests a longer version of the
code-only demand in P1; it is not the former compressed-instruction arm.

## Extraction and execution (owner revision)

Choose the last complete fenced python/py/unlabelled block that parses as Python
and defines the required top-level function. Fence labels are case-insensitive.
If none qualifies, use the whole stripped response; never merge blocks or repair
code. A nested definition, a function name inside a string, an invalid Python
block or an unclosed fence does not qualify. A later unrelated code block does
not override an earlier qualifying block.

Prepend the task prompt's original prelude, meaning everything before the target
function (imports, helper functions and comments). For decorated targets, the
target starts at its first decorator. Then pass the combined source to the P1
sandbox, including its syntax/import checks. No reference body is added. The
same path is tested on all 40 reference solutions before model calls.

## Determinism, prompt caching and residency

Compare exact response text, prompt_eval_count and prompt_eval_duration on two
identical requests. Preserve all three observations, even when text differs.
The probe uses keep_alive=-1. Registered conservative cache signal in config:
**a decrease in either prompt_eval_count or prompt_eval_duration on request two**.
A shorter duration alone may be noise; it is not proof of reuse. The policy
deliberately prefers unloading when reuse is possible rather than claiming a
cache-free comparison from timing alone. No arbitrary timing-ratio threshold is used.

If either model signals reuse, use **keep_alive=0 for all scored runs**. Unload
probe/warm-up models before the first scored call and verify unload; zero on a
generation request alone unloads after that request and would not by itself
prevent the first request from reusing already resident state. Record each call's
load_duration separately. If neither signals reuse, retain -1. Invalid/missing
probe fields stop scored generation. Persist the resolved policy before the smoke
run and retain it on resume. Observed outcomes will be recorded in learning/P2.md.
