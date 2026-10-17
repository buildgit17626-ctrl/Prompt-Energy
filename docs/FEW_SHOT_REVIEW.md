# Original demonstration audit — 2026-10-17

Reviewed the full prompts of all 40 registered tasks before any model inference.
Originality here means written for this study, not copied from benchmark solutions;
it cannot imply that a trivial operation has never been written elsewhere.
Non-overlap means no selected task is duplicated or specialized by a demonstration.
Sharing Python syntax or elementary string operations is not task duplication.

The original `add_seven` example specialized HumanEval/53 (addition), so it was
removed before any generations. The task sample and other prompt arms did not change.

Current demonstrations:
- `lookup_status`: dictionary lookup with a fixed missing-key default.
- `wrap_label`: add literal square brackets around one string.
- `count_tabs`: count tab characters in one string.

None of the 40 tasks asks for these operations. In particular, balanced-parenthesis
parsing (1) does not wrap text; word/consonant filtering (117) does not count tabs;
space replacement (140) does not count tabs or wrap a label. The new lookup example
does not perform addition (53). No demonstration supplies a selected reference
solution or a function that solves a selected task by renaming it.

## Coverage of the manual semantic review

| Selected task IDs | Required operation, distinct from the three demonstrations |
| --- | --- |
| 0, 43 | Close numeric pairs; pairs summing to zero |
| 1, 11, 14, 29 | Parenthesis groups; binary XOR; prefixes; prefix filtering |
| 13, 24 | Greatest common divisor; largest proper divisor |
| 39, 46, 55 | Prime Fibonacci; Fib4; Fibonacci |
| 53, 92 | Add two inputs; integer sum relation |
| 57, 73, 74 | Monotonicity; palindrome changes; compare list text lengths |
| 76, 89, 90 | Power membership; alphabet rotation; second distinct minimum |
| 94, 96 | Largest prime's digit sum; primes below a bound |
| 101, 102, 105 | Split words; largest even in interval; digit names sorted by value |
| 115, 116, 117 | Bucket counts; sort by bit count; consonant-based word filtering |
| 122, 127, 128 | Restricted element sum; prime interval intersection; sign/magnitude aggregate |
| 133, 140, 143 | Sum of ceiling squares; space replacement; prime-length word selection |
| 144, 148, 150 | Fraction product integrality; planets between endpoints; prime-conditioned selection |
| 156, 158, 160, 162 | Roman numerals; distinct-character maximum; arithmetic expression; MD5 |

Automated checks cover different function names and normalized function bodies,
plus sandboxed correctness of all three authored demonstrations. Those checks
are regression guards, not a substitute for this semantic review. Repeat the
review and record it before changing any demonstration or selected task.
