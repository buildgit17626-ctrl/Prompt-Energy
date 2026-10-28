# Report and code: Prompt design and the energy cost of correct code

Two-page overview | 28 October 2026

## Why this study

A useful answer takes time and computation. We wanted to see whether everyday prompt choices change that cost without sacrificing correct code. This is a small experiment, intended to identify questions worth testing further.

## Setup

We tested seven prompts on 40 HumanEval tasks using Qwen2.5-Coder 0.5B and 1.5B: 560 main requests, plus 280 repeat-check requests. The laptop had an i5-13420H and 16 GB RAM. Ollama ran on CPU with temperature 0, seed 1729, eight threads, context capacity 4096 and an output cap of 768 tokens.

## Hypotheses before the run (shortened)

H1: Longer outputs explain much of the variation in time and energy.

H2: Concise answers save cost on easier tasks, but may reduce accuracy on harder ones.

H3: Examples add input tokens but may improve success and cost per correct answer.

H4: Step-by-step prompts cost more but may help harder tasks.

H5: Longer code-only instructions raise input-processing cost but change total energy little.

![Figure S1](../../results/p4-summary/01_accuracy.png)

Figure S1. Pass counts and rates on the same 40 tasks per model/arm; 95% task-bootstrap intervals. P0 minimal; P1 code only; P2 explain; P3_1/P3_3 examples; P4 step by step; P5 long code only.

---PAGE---

## Observations

On 1.5B, P4 averaged 526.5 output tokens and passed 27/40 tasks; P1 averaged 71.1 tokens and passed 29/40. More explanation did not produce more passes here. P3_1 had the highest observed 1.5B pass count, 30/40, but its one-task lead over P1 is uncertain.

On 0.5B, P3_3 had the lowest mean net energy per attempt (25.18 mWh), but passed only 19 tasks. P1 used 26.61 mWh per attempt and passed 24. Three examples shortened responses compared with one example on both models, while passing two fewer tasks on each.

![Figure S2](../../results/p4-revision/02_cost_per_correct.png)

Figure S2. Total attempted energy / number passing, including failed-attempt costs; 95% task-bootstrap ratio intervals. HWiNFO CPU Package Power, trapezoidal integration, approximate post-load window; net subtracts block-start idle power. All main estimates carry baseline-drift flags.

## What limits these results

Idle power fell from 17.553 to 11.516 W during the main block, making net energy uncertain. Seventy main requests had short, low-resolution windows; excluding them changes the task mix. Only 64/140 stage-2 energy pairs were complete. We cannot attribute energy to separate input/output phases or infer whole-device, battery or carbon savings. Paired accuracy intervals do not establish equivalence.

## Conclusion

The cheapest response per attempt was not the cheapest per correct answer: P1 had lower observed energy per correct than P3_3 on 0.5B. The next step is to repeat the comparison with stable baselines and prompts that change one feature at a time. This report does not establish a universally best prompt.

Details, exact prompts, references, code provenance and limitations are in the full report. AI helped with setup, automated Ollama runs and report preparation; failure annotations were AI-assisted without an independent second annotator.
