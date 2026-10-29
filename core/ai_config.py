"""The ONE place that decides which model serves which routing level (protocol section 5).

Business code never names a model: it asks core.ai for a task type and gets a level back.
Model ids come from the current Anthropic model list; each can be overridden by an env var
without a code change. Prices are NOT here: they come from LLM_PRICE_* env vars (core/budget.py).
"""

import os

NO_AI, LOW, STANDARD, HIGH = "NO_AI", "LOW", "STANDARD", "HIGH"
ORDER = (NO_AI, LOW, STANDARD, HIGH)

# level -> (default model id, env override, max prompt tokens, max output tokens)
LEVELS = {
    LOW: ("claude-haiku-5-5", "LLM_MODEL_LOW", 3000, 600),
    STANDARD: ("claude-sonnet-5-5", "LLM_MODEL_STANDARD", 6000, 1500),
    HIGH: ("claude-opus-5-5", "LLM_MODEL_HIGH", 12000, 3000),
}
PROMPT_VERSION = "command-center-v1"
CHARS_PER_TOKEN = 3  # conservative: over-estimating tokens only makes the budget reservation safer


def model_for(level: str) -> str:
    default, env, _, _ = LEVELS[level]
    return os.environ.get(env, "").strip() or default


def limits(level: str) -> tuple[int, int]:
    _, _, tin, tout = LEVELS[level]
    return tin, tout


# task type -> level, context kinds pulled from the chosen business only, and whether the topic is high-stakes.
# `stakes` forces needs_approval=True on the answer (advice about it is never an instruction to act).
TASKS = {
    "calculation":         dict(level=NO_AI, context=(), stakes=False, about="Totals, sorting, counts, date math: do it in code."),
    "tag_note":            dict(level=LOW, context=(), stakes=False, about="Tag or categorise a short note."),
    "extract_fields":      dict(level=LOW, context=(), stakes=False, about="Pull named fields out of provided text."),
    "routine_summary":     dict(level=LOW, context=("goals", "kpis"), stakes=False, about="Short routine digest."),
    "draft_content":       dict(level=STANDARD, context=("goals", "knowledge", "evidence"), stakes=False, about="Draft content for this business."),
    "weekly_plan":         dict(level=STANDARD, context=("tasks", "goals", "kpis", "blockers"), stakes=False, about="Plan the week."),
    "research_summary":    dict(level=STANDARD, context=("knowledge", "research", "evidence"), stakes=False, about="Summarise or plan research."),
    "analyze_data":        dict(level=STANDARD, context=("kpis", "goals"), stakes=False, about="Analyse data the founder provides."),
    "general_question":    dict(level=STANDARD, context=("goals", "tasks"), stakes=False, about="Anything else."),
    "architecture_design": dict(level=HIGH, context=("goals", "tasks", "decisions"), stakes=False, about="System design."),
    "debug_root_cause":    dict(level=HIGH, context=("tasks", "blockers"), stakes=False, about="Hard debugging."),
    "strategy_decision":   dict(level=HIGH, context=("goals", "kpis", "decisions", "blockers"), stakes=True, about="High-impact decision."),
    "trading_validation":  dict(level=HIGH, context=("strategies", "runs"), stakes=True, about="Audit a backtest for overfitting or look-ahead bias."),
}
DEFAULT_TASK = "general_question"

# Words that make a request high-stakes regardless of its type: the level goes up one step and
# needs_approval is set on the result. (Keyword rules are crude on purpose: they only ever add caution.)
STAKES_WORDS = ("live trading", "real money", "place an order", "invest", "wire", "legal", "contract", "delete", "production",
                "email customers", "send to customers", "publish", "press release", "investor")

# Ordered (task_type, keywords) used when the caller does not name a task type.
RULES = (
    ("trading_validation", ("overfit", "look-ahead", "lookahead", "validate the backtest", "audit the backtest", "walk-forward review")),
    ("calculation", ("calculate", "how many", "sum of", "total of", "sort ", "days until", "average of", "count of")),
    ("debug_root_cause", ("root cause", "stack trace", "traceback", "why does it crash", "debug")),
    ("architecture_design", ("architecture", "system design", "data model design", "schema design")),
    ("strategy_decision", ("should we pivot", "major decision", "strategy change", "should i quit", "go or no-go")),
    ("weekly_plan", ("weekly plan", "plan my week", "this week")),
    ("draft_content", ("draft", "write a post", "caption", "script for", "newsletter")),
    ("research_summary", ("research", "competitor", "summarise sources", "summarize sources")),
    ("extract_fields", ("extract", "pull out the")),
    ("tag_note", ("tag this", "categorise", "categorize", "label this note")),
    ("routine_summary", ("summary", "summarise", "summarize", "digest")),
    ("analyze_data", ("analyse", "analyze", "trend", "compare")),
)

MAX_CONTEXT_ROWS = 6
MAX_ROW_CHARS = 300
MAX_INPUT_CHARS = 6000
