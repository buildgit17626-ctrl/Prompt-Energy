"""P1 registration. Change experimental choices only before generation, with a log."""

MODELS = ("qwen2.5-coder:0.5b", "qwen2.5-coder:1.5b")
MODEL_LICENSES = dict.fromkeys(MODELS, "Apache-2.0")
TASK_SELECTION_SEED = 1729
EXECUTION_SEED = 1729
TASK_COUNT = 40
# Numeric order of the sampled population, not lexicographic string ordering.
TASK_IDS = tuple(
    f"HumanEval/{i}"
    for i in (
        0,
        1,
        11,
        13,
        14,
        24,
        29,
        39,
        43,
        46,
        53,
        55,
        57,
        73,
        74,
        76,
        89,
        90,
        92,
        94,
        96,
        101,
        102,
        105,
        115,
        116,
        117,
        122,
        127,
        128,
        133,
        140,
        143,
        144,
        148,
        150,
        156,
        158,
        160,
        162,
    )
)
HUMANEVAL_REVISION = "6d43fb980f9fee3c892a914eda09951f772ad10d"
REPEATS = 3

# Authored for this study; no benchmark reference solutions are demonstrations.
FEW_SHOT_EXAMPLES = (
    ('def add_seven(n):\n    """Return n plus seven."""', "def add_seven(n):\n    return n + 7"),
    (
        'def wrap_label(text):\n    """Put text between square brackets."""',
        'def wrap_label(text):\n    return "[" + text + "]"',
    ),
    (
        'def count_tabs(text):\n    """Count tab characters in text."""',
        'def count_tabs(text):\n    return text.count("\\t")',
    ),
)
# P3_1 and P3_3 are distinct conditions. P2 will implement the prompt builder.
PROMPTS = {
    "P0": {"instruction": "Complete the Python function.", "examples": 0},
    "P1": {"instruction": "Complete the Python function. Return only code.", "examples": 0},
    "P2": {
        "instruction": "Explain your solution, then provide the completed Python function.",
        "examples": 0,
    },
    "P3_1": {"instruction": "Complete the Python function following the example.", "examples": 1},
    "P3_3": {"instruction": "Complete the Python function following the examples.", "examples": 3},
    "P4": {
        "instruction": "Reason step by step, then provide the completed Python function.",
        "examples": 0,
    },
    "P5": {"instruction": "Complete Python function:", "examples": 0},
}
SANDBOX = {
    "timeout_seconds": 5.0,
    "memory_mb": 256,
    "poll_seconds": 0.01,
    "max_source_bytes": 100_000,
}
# Future contract only: P2 must register num_predict and thread count before runs.
OLLAMA = {
    "base_url": "http://127.0.0.1:11434",
    "endpoint": "/api/generate",
    "temperature": 0,
    "seed": EXECUTION_SEED,
    "num_predict": None,
    "stream": False,
    "num_gpu": 0,
}
OLLAMA_RESPONSE_FIELDS = (
    "prompt_eval_count",
    "eval_count",
    "total_duration",
    "load_duration",
    "prompt_eval_duration",
    "eval_duration",
)
