"""Study registration. Owner authorized proceeding with P2 on 2026-10-19."""

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
    (
        'def lookup_status(statuses, key):\n    """Look up key; return unknown if absent."""',
        'def lookup_status(statuses, key):\n    return statuses.get(key, "unknown")',
    ),
    (
        'def wrap_label(text):\n    """Put text between square brackets."""',
        'def wrap_label(text):\n    return "[" + text + "]"',
    ),
    (
        'def count_tabs(text):\n    """Count tab characters in text."""',
        'def count_tabs(text):\n    return text.count("\\t")',
    ),
)
# P3_1 and P3_3 are distinct conditions in the exact prompt builder.
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
    "P5": {
        "instruction": (
            "Please read the following Python function signature and docstring carefully. "
            "Complete the function so that it satisfies the docstring and handles edge cases "
            "correctly. Return only the code for the completed function, with no explanation."
        ),
        "examples": 0,
    },
}
SYSTEM_PROMPT = "You are a helpful coding assistant."
WARMUP_PROMPT = "Respond with the single word READY."
PROMPT_ASSEMBLY = {
    "separator": "\n\n",
    "example_template": (
        "Example task:\n{example_prompt}\nExample solution:\n```python\n{example_solution}\n```"
    ),
    "task_template": "Task:\n{task_prompt}",
    "final_newline": "\n",
}
SANDBOX = {
    "timeout_seconds": 5.0,
    "memory_mb": 256,
    "poll_seconds": 0.01,
    "max_source_bytes": 100_000,
    "cleanup_timeout_seconds": 2.0,
    "cleanup_poll_seconds": 0.05,
}
# Fixed before generation; keep_alive for scored runs is resolved by CACHE_POLICY.
OLLAMA = {
    "base_url": "http://127.0.0.1:11434",
    "endpoint": "/api/generate",
    "temperature": 0,
    "seed": EXECUTION_SEED,
    "num_predict": 768,
    "num_ctx": 4096,
    "num_thread": 8,
    "stream": False,
    "num_gpu": 0,
    "keep_alive": -1,
    "stop": [],
    "request_timeout_seconds": 300,
}
CACHE_POLICY = {
    "probe_requests": 2,
    "compare_fields": ("response", "prompt_eval_count", "prompt_eval_duration"),
    "probe_keep_alive": -1,
    # A deliberately conservative signal: timing noise may also cause a decrease.
    # This is not a claim that lower duration proves token-cache reuse.
    "reuse_signal": "second_count_lt_first_or_second_duration_lt_first",
    "on_reuse_keep_alive": 0,
    "otherwise_keep_alive": -1,
    "scope": "all_scored_runs_if_any_model_signals_reuse",
    "invalid_probe": "stop_before_scored_generation",
    "freeze_decision_before_smoke": True,
    "verify_unloaded_before_scored_if_zero": True,
}
EXTRACTION = {
    "fence_labels": ("python", "py", ""),
    "selection": "last_complete_parseable_block_defining_required_top_level_function",
    "fallback": "whole_stripped_response",
    "prepend_task_prelude": True,
}
P2_SMOKE = {
    "model": MODELS[1],
    "task_ids": TASK_IDS[:5],
    "prompt_ids": tuple(PROMPTS),
    "repeats": 1,
    "order_seed": EXECUTION_SEED,
}
P2_CONTROL = {"unload_timeout_seconds": 10.0, "unload_poll_seconds": 0.1}
OLLAMA_RESPONSE_FIELDS = (
    "prompt_eval_count",
    "eval_count",
    "total_duration",
    "load_duration",
    "prompt_eval_duration",
    "eval_duration",
)

# Prospective P3 registration: implementation approved, pilot NOT approved.
P3_PILOT = {
    "task_selection_seed": 1729,
    "order_seed": 1729,
    "task_ids": tuple(
        f"HumanEval/{i}"
        for i in (
            0,
            11,
            13,
            14,
            29,
            46,
            53,
            55,
            76,
            90,
            92,
            94,
            105,
            117,
            122,
            128,
            133,
            140,
            143,
            160,
        )
    ),
    "prompt_ids": ("P0", "P1", "P2", "P4"),
    "models": MODELS,
    "repeats": 2,
    "keep_alive": 0,
    "owner_approval_required": True,
    "include_in_main_analysis": False,
    "expected_runtime_version": "0.40.6",
    "expected_model_digests": {
        "qwen2.5-coder:0.5b": "4ff64a7f502a08b7616edb8ca0a79eb1853fc363d842b7df4b46915d11a3fb09",
        "qwen2.5-coder:1.5b": "d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668",
    },
}
ENERGY = {
    "tool": "HWiNFO",
    "mode": "CPU Package Power sensor; trapezoidal; idle-adjusted",
    "sensor_column": "CPU Package Power [W]",
    "poll_seconds": 0.5,
    "cadence_relative_tolerance": 0.2,
    "max_sample_gap_seconds": 1.0,
    "low_resolution_seconds": 3.0,
    "baseline_seconds": 60.0,
    "gap_seconds": 5.0,
    "growth_check_seconds": 3.0,
    "freshness_seconds": 3.0,
    "coverage_wait_seconds": 10.0,
    "phase_tolerance_seconds": 0.1,
    "phase_tolerance_fraction": 0.05,
    "primary_window": "post_load",
    "windows": ("total", "post_load", "prompt_eval", "decode"),
    "negative_adjusted_energy": "retain_and_flag",
    "utc_offset_minutes": 330,
    "smoke_excluded": True,
}
CODECARBON = {
    "country_iso_code": "IND",
    "tracking_mode": "machine",
    "measure_power_secs": 1.0,
    "mode": "offline machine estimate; whole-request envelope; secondary",
}

# Owner amendment after the diagnostic pilot; not permission to start P4.
# Historical ENERGY/CODECARBON settings above reproduce the P3 experiment.
FULL_RUN_MEASUREMENT = {
    "registered_on": "2026-10-20",
    "tool": "HWiNFO",
    "codecarbon_enabled": False,
    "phase_energy_enabled": False,
    "windows": ("total", "post_load"),
    "primary_window": "post_load",
    "report_gross_and_net": True,
    "predictors": ("output_tokens", "input_tokens"),
    "energy_analysis_sets": ("all_available", "exclude_primary_low_resolution"),
    "sensitivity_excluded_flag": "post_load:low_resolution",
    "missing_energy": "retain_row_no_imputation_report_denominator",
    "include_failed_answers": True,
    "pilot_excluded": True,
    "idle_recheck": "owner_skipped_2026-10-20",
    "full_run_authorized": False,
}

# Authored safety demonstrations, never included in the research task population.
SANDBOX_DEMO_CASES = (
    ("correct", "def answer():\n    return 42", "passed"),
    ("wrong", "def answer():\n    return 0", "failed"),
    ("import_os", "import os\ndef answer():\n    return 42", "rejected"),
    ("infinite_loop", "def answer():\n    while True: pass", "timeout"),
    ("memory_hog", "def answer():\n    return [0] * (10**9)", "memory_limit"),
)
