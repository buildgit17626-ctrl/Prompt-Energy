# P2 exact prompts — awaiting owner review

No generation is authorized by this document alone. Review these texts together
with docs/plans/P2.md before warm-up, smoke or determinism calls. The seven arm
instructions and demonstrations below preserve the accepted P1 wording.

## Common system text (proposed)

```text
You are a helpful coding assistant.
```

Send this explicitly as the API system field. Ollama applies the selected model's
chat template; record its exact template, model digest and runtime version.
No task solution, benchmark tests or difficulty label is sent to the model.

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
| P5 | Complete Python function: | None |

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

Temperature 0, seed 1729, output budget 768, proposed context 4096 and CPU threads
8, CPU only, no custom stop strings. The full-function extraction rule and its
failure precedence are specified in plans/P2.md and apply equally to every arm.
Once approved, implementation tests will lock assembly to these exact templates.
