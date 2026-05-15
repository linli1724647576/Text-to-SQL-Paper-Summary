"""Shared Text-to-SQL taxonomy and keyword rules."""

TOPIC_TAXONOMY = {
    "Task Setting": [
        "Single-turn Text-to-SQL",
        "Multi-turn Text-to-SQL",
        "Cross-domain Text-to-SQL",
        "Enterprise / BI Text-to-SQL",
        "Conversational Data Analysis",
        "Text-to-DSL / Hybrid Query",
    ],
    "Pre-training and Fine-tuning": [
        "Pre-training",
        "Supervised Fine-tuning",
        "Instruction Tuning",
        "Reinforcement Learning",
        "Small Models and Distillation",
    ],
    "Prompting and ICL": [
        "Zero-shot / Few-shot ICL",
        "Prompt Engineering",
        "Chain-of-Thought Reasoning",
        "Self-consistency / Voting",
        "Example Selection",
    ],
    "Grounding and Retrieval": [
        "Schema Linking",
        "Value Linking",
        "Schema / Content Retrieval",
        "Semantic Layer / Metadata",
        "Knowledge Graph / External Knowledge",
    ],
    "Planning and Generation": [
        "Intermediate Representation",
        "Query Decomposition",
        "Join Path Planning",
        "Constrained Decoding",
        "Dialect Adaptation",
        "Neural-symbolic Parsing",
    ],
    "Agentic Feedback and Repair": [
        "Agentic Workflow",
        "Tool Use and Execution Guidance",
        "Self-correction and Repair",
        "Verification and Guardrails",
        "Security and Access Control",
        "Human Feedback",
    ],
    "Benchmarks and Evaluation": [
        "Benchmark",
        "Dataset Construction",
        "Synthetic Data Generation",
        "Evaluation Metric",
        "Robustness and Generalization",
        "Contamination / Data Leakage",
        "Industrial Evaluation",
    ],
}

PIPELINE_TAXONOMY = {
    "Task Understanding": [
        "Intent Detection",
        "Question Decomposition",
        "Dialogue Context Tracking",
        "Domain Constraint Understanding",
    ],
    "Grounding": [
        "Schema Linking",
        "Value Linking",
        "Context Retrieval",
        "Database Content Grounding",
    ],
    "Query Planning": [
        "SQL Sketch / Skeleton",
        "Intermediate Representation",
        "Join Path Planning",
        "Step-by-step Reasoning",
    ],
    "SQL Generation": [
        "Prompt-based Generation",
        "Fine-tuned Generation",
        "Constrained Decoding",
        "Dialect Adaptation",
    ],
    "Verification & Repair": [
        "Execution Feedback",
        "Self-correction",
        "Static SQL Validation",
        "Result Validation",
    ],
}

TEXT2SQL_TERMS = [
    "text-to-sql",
    "text to sql",
    "text2sql",
    "nl2sql",
    "natural language to sql",
    "natural-language-to-sql",
    "natural language interface to database",
    "natural language interfaces to databases",
    "semantic parsing",
    "database question answering",
    "question answering over databases",
]

DATABASE_TERMS = [
    "sql",
    "database",
    "databases",
    "relational",
    "schema",
    "table",
    "column",
    "query",
    "queries",
]

LLM_TERMS = [
    "large language model",
    "llm",
    "gpt",
    "chatgpt",
    "codex",
    "llama",
    "deepseek",
    "qwen",
    "prompt",
    "in-context",
    "chain-of-thought",
    "agent",
]


def all_topic_labels():
    labels = []
    for top, subs in TOPIC_TAXONOMY.items():
        labels.append(top)
        labels.extend(subs)
    return labels


def all_pipeline_labels():
    labels = []
    for stage, subs in PIPELINE_TAXONOMY.items():
        labels.append(stage)
        labels.extend(subs)
    return labels
