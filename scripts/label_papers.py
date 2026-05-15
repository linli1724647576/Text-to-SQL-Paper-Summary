#!/usr/bin/env python3
"""Filter and classify Text-to-SQL papers.

ASE-style two-phase pipeline:

* phase=filter: high-recall keyword filter for Text-to-SQL relevance.
* phase=label: classify filtered papers. The default backend is deterministic
  rules; --backend bedrock uses an LLM classifier when AWS Bedrock credentials
  are available.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from taxonomy import LLM_TERMS, PIPELINE_TAXONOMY, TOPIC_TAXONOMY

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def norm(text):
    return re.sub(r"\s+", " ", (text or "").lower())


def contains_any(text, terms):
    return any(term in text for term in terms)


def is_relevant(title, abstract, keywords=""):
    text = norm(" ".join([title, abstract, keywords]))
    direct = contains_any(
        text,
        [
            "text-to-sql",
            "text to sql",
            "text2sql",
            "nl2sql",
            "natural language to sql",
            "natural-language-to-sql",
        ],
    )
    semantic_sql = "semantic parsing" in text and "sql" in text
    nl_db = (
        contains_any(
            text,
            [
                "natural language interface to database",
                "natural language interfaces to databases",
                "natural language query",
                "database question answering",
                "question answering over databases",
            ],
        )
        and "sql" in text
        and contains_any(text, ["query", "queries", "interface", "question answering"])
    )
    llm_sql = contains_any(text, LLM_TERMS) and contains_any(
        text,
        [
            "sql generation",
            "generate sql",
            "sql query generation",
            "natural language query",
            "database question answering",
            "question answering over databases",
        ],
    )
    return direct or semantic_sql or nl_db or llm_sql


TOPIC_RULES = {
    "Single-turn Text-to-SQL": ["single-turn", "single turn", "one-shot", "question-to-sql"],
    "Multi-turn Text-to-SQL": ["multi-turn", "multi turn", "conversational", "dialogue", "dialog"],
    "Cross-domain Text-to-SQL": ["cross-domain", "cross domain", "spider", "bird", "generalization"],
    "Enterprise / BI Text-to-SQL": ["enterprise", "production", "business intelligence", "bi", "dashboard", "warehouse"],
    "Conversational Data Analysis": ["conversational analytics", "data analysis", "analytics", "ask questions", "plain english"],
    "Text-to-DSL / Hybrid Query": ["sparql", "cypher", "dsl", "query language", "text-to-query", "hybrid query"],
    "Pre-training": ["pre-train", "pretrain", "masked language", "language model pretraining", "bert", "t5", "codebert"],
    "Supervised Fine-tuning": ["fine-tun", "supervised", "training", "train a model", "labeled data"],
    "Instruction Tuning": ["instruction tuning", "instruction-tuned", "alignment tuning", "instruction data"],
    "Reinforcement Learning": ["reinforcement learning", "rlhf", "preference optimization", "policy optimization"],
    "Small Models and Distillation": ["small language model", "small model", "distillation", "distill", "student model", "slm"],
    "Zero-shot / Few-shot ICL": ["in-context", "few-shot", "zero-shot", "demonstration"],
    "Prompt Engineering": ["prompt", "prompting", "prompt engineering", "prompt design"],
    "Chain-of-Thought Reasoning": ["chain-of-thought", "chain of thought", "step-by-step", "reasoning"],
    "Self-consistency / Voting": ["self-consistency", "self consistency", "voting", "majority vote", "candidate selection"],
    "Example Selection": ["example selection", "demonstration selection", "retrieved examples", "similar examples"],
    "Schema Linking": ["schema linking", "schema-linking", "column linking", "table linking", "schema element"],
    "Value Linking": ["value linking", "cell value", "database value", "entity linking"],
    "Schema / Content Retrieval": ["database content", "content retrieval", "sample rows", "retrieval", "rag", "retrieve"],
    "Semantic Layer / Metadata": ["semantic layer", "metadata", "description", "documentation", "comment", "data dictionary"],
    "Knowledge Graph / External Knowledge": ["knowledge graph", "external knowledge", "ontology", "kg"],
    "Intermediate Representation": ["intermediate representation", "ir", "sketch", "skeleton", "semql", "grammar"],
    "Query Decomposition": ["decomposition", "decompose", "sub-question", "subquery", "multi-step"],
    "Join Path Planning": ["join path", "join planning", "foreign key", "join graph"],
    "Constrained Decoding": ["constrained decoding", "grammar-constrained", "grammar constrained", "decoder"],
    "Dialect Adaptation": ["dialect", "postgres", "postgresql", "mysql", "sqlite", "snowflake", "bigquery", "oracle"],
    "Neural-symbolic Parsing": ["neural-symbolic", "symbolic", "semantic parser", "grammar"],
    "Agentic Workflow": ["agent", "workflow", "planner", "multi-agent", "autonomous"],
    "Tool Use and Execution Guidance": ["tool use", "execution-guided", "execution guided", "execution feedback", "execution result"],
    "Self-correction and Repair": ["self-correction", "self correction", "repair", "refine", "revision"],
    "Verification and Guardrails": ["verification", "validate", "guardrail", "static analysis", "checker"],
    "Security and Access Control": ["privacy", "access control", "permission", "security", "rbac", "policy", "prompt injection"],
    "Human Feedback": ["human feedback", "user feedback", "interactive", "clarification"],
    "Benchmark": ["benchmark", "bird", "spider", "wikisql", "cosql", "sparc"],
    "Dataset Construction": ["dataset", "corpus", "annotation", "data collection"],
    "Synthetic Data Generation": ["synthetic", "data generation", "augmentation", "generate data"],
    "Evaluation Metric": ["metric", "execution accuracy", "exact match", "soft f1", "leaderboard"],
    "Robustness and Generalization": ["robustness", "generalization", "out-of-domain", "distribution shift", "ambiguity"],
    "Contamination / Data Leakage": ["contamination", "data leakage", "leakage", "training leakage"],
    "Industrial Evaluation": ["industrial", "production", "deployment", "enterprise", "case study"],
}

STAGE_RULES = {
    "Task Understanding": ["intent", "question understanding", "decomposition", "dialogue", "context", "constraint"],
    "Intent Detection": ["intent"],
    "Question Decomposition": ["decomposition", "decompose", "sub-question", "subquestion"],
    "Dialogue Context Tracking": ["dialogue", "dialog", "multi-turn", "context tracking"],
    "Domain Constraint Understanding": ["domain constraint", "business rule", "constraint"],
    "Grounding": ["grounding", "schema linking", "value linking", "schema", "column", "table", "database content"],
    "Schema Linking": ["schema linking", "column linking", "table linking", "foreign key"],
    "Value Linking": ["value linking", "cell value", "database value", "entity linking"],
    "Context Retrieval": ["retrieval", "retrieve", "rag", "context"],
    "Database Content Grounding": ["database content", "sample rows", "row retrieval", "content grounding"],
    "Query Planning": ["planning", "planner", "sketch", "skeleton", "intermediate representation", "chain-of-thought"],
    "SQL Sketch / Skeleton": ["sketch", "skeleton"],
    "Intermediate Representation": ["intermediate representation", "semql", "ir"],
    "Join Path Planning": ["join path", "join planning", "foreign key"],
    "Step-by-step Reasoning": ["step-by-step", "chain-of-thought", "reasoning"],
    "SQL Generation": ["sql generation", "generate sql", "decoder", "text-to-sql", "nl2sql"],
    "Prompt-based Generation": ["prompt", "few-shot", "zero-shot", "in-context"],
    "Fine-tuned Generation": ["fine-tun", "instruction tuning", "supervised"],
    "Constrained Decoding": ["constrained decoding", "grammar-constrained", "decoder"],
    "Dialect Adaptation": ["dialect", "postgres", "mysql", "sqlite", "snowflake"],
    "Verification & Repair": ["verification", "repair", "self-correction", "execution feedback", "validate", "refine"],
    "Execution Feedback": ["execution feedback", "execution-guided", "execution result"],
    "Self-correction": ["self-correction", "self correction", "refine", "repair"],
    "Static SQL Validation": ["static validation", "static analysis", "syntax check", "validator"],
    "Result Validation": ["result validation", "answer validation", "consistency"],
}

ALL_TOPIC_SUBLABELS = [f"{top}, {sub}" for top, subs in TOPIC_TAXONOMY.items() for sub in subs]
ALL_STAGE_SUBLABELS = [f"{top}, {sub}" for top, subs in PIPELINE_TAXONOMY.items() for sub in subs]

SYSTEM_PROMPT = """You are a senior database and NLP researcher specializing in Text-to-SQL.
Determine whether the paper is centrally about Text-to-SQL / NL2SQL / semantic parsing to SQL / natural-language database querying.

If not centrally about this area, return exactly: NOT_RELEVANT

If relevant, classify it with:
1. topic_labels: one or more labels in "TopLevel, SubLevel" format from TOPIC_TAXONOMY.
2. pipeline_labels: one or more labels in "Stage, SubStage" format from PIPELINE_TAXONOMY.

Do not invent labels.
Return only JSON:
{"topic_labels": [...], "pipeline_labels": [...]}
"""

USER_PROMPT_TEMPLATE = """TOPIC_TAXONOMY:
{topic_taxonomy}

PIPELINE_TAXONOMY:
{pipeline_taxonomy}

Title: {title}

Abstract: {abstract}
"""


def add_parent_labels(selected, taxonomy):
    result = []
    seen = set()
    for parent, children in taxonomy.items():
        if parent in selected or any(child in selected for child in children):
            if parent not in seen:
                result.append(parent)
                seen.add(parent)
            for child in children:
                if child in selected and child not in seen:
                    result.append(child)
                    seen.add(child)
    return result


def classify_entry(title, entry):
    text = norm(" ".join([title, entry.get("abstract", ""), entry.get("keywords", "")]))
    selected_topics = set()
    selected_stages = set()

    for label, terms in TOPIC_RULES.items():
        if contains_any(text, terms):
            selected_topics.add(label)

    for label, terms in STAGE_RULES.items():
        if contains_any(text, terms):
            selected_stages.add(label)

    if contains_any(text, LLM_TERMS):
        selected_topics.add("Prompt Engineering")
    if "text-to-sql" in text or "nl2sql" in text or "natural language to sql" in text:
        selected_topics.add("Single-turn Text-to-SQL")
        selected_stages.add("SQL Generation")

    labels = add_parent_labels(selected_topics, TOPIC_TAXONOMY)
    stages = add_parent_labels(selected_stages, PIPELINE_TAXONOMY)

    if not labels:
        labels = ["Planning and Generation", "Neural-symbolic Parsing"]
    if not stages:
        stages = ["SQL Generation"]

    copied = dict(entry)
    copied["labels"] = labels
    copied["pipeline_stages"] = stages
    return copied


def classify_with_bedrock(papers, model, region, delay):
    try:
        import boto3
    except ImportError:
        print("Error: pip install boto3 to use --backend bedrock", file=sys.stderr)
        sys.exit(1)

    client = boto3.client("bedrock-runtime", region_name=region)
    classified = {}
    topic_taxonomy = json.dumps(TOPIC_TAXONOMY, indent=2, ensure_ascii=False)
    pipeline_taxonomy = json.dumps(PIPELINE_TAXONOMY, indent=2, ensure_ascii=False)

    for i, (title, entry) in enumerate(papers.items(), 1):
        abstract = entry.get("abstract", "")
        user_prompt = USER_PROMPT_TEMPLATE.format(
            topic_taxonomy=topic_taxonomy,
            pipeline_taxonomy=pipeline_taxonomy,
            title=title,
            abstract=abstract,
        )
        try:
            response = client.converse(
                modelId=model,
                system=[{"text": SYSTEM_PROMPT}],
                messages=[{"role": "user", "content": [{"text": user_prompt}]}],
                inferenceConfig={"maxTokens": 700, "temperature": 0.0},
            )
            output = response["output"]["message"]["content"][0]["text"].strip()
        except Exception as exc:
            print(f"[{i}/{len(papers)}] WARN: {title[:70]}: {exc}", file=sys.stderr)
            continue

        if output == "NOT_RELEVANT" or "NOT_RELEVANT" in output:
            continue

        try:
            if "```" in output:
                output = output.split("```")[1].removeprefix("json").strip()
            payload = json.loads(output)
        except json.JSONDecodeError:
            print(f"[{i}/{len(papers)}] WARN: parse failed: {title[:70]} -> {output[:120]}", file=sys.stderr)
            continue

        topic_pairs = [label for label in payload.get("topic_labels", []) if label in ALL_TOPIC_SUBLABELS]
        stage_pairs = [label for label in payload.get("pipeline_labels", []) if label in ALL_STAGE_SUBLABELS]

        selected_topics = {part for pair in topic_pairs for part in pair.split(", ", 1)}
        selected_stages = {part for pair in stage_pairs for part in pair.split(", ", 1)}
        entry_copy = dict(entry)
        entry_copy["labels"] = add_parent_labels(selected_topics, TOPIC_TAXONOMY)
        entry_copy["pipeline_stages"] = add_parent_labels(selected_stages, PIPELINE_TAXONOMY)
        if entry_copy["labels"] and entry_copy["pipeline_stages"]:
            classified[title] = entry_copy
        print(f"[{i}/{len(papers)}] OK: {title[:70]}", file=sys.stderr)
        if delay:
            import time
            time.sleep(delay)
    return classified


def filter_papers(papers):
    return {
        title: entry
        for title, entry in papers.items()
        if is_relevant(title, entry.get("abstract", ""), entry.get("keywords", ""))
    }


def label_papers(papers, backend="rules", model="us.anthropic.claude-sonnet-4-6", region="us-east-1", delay=0.5):
    if backend == "bedrock":
        return classify_with_bedrock(papers, model=model, region=region, delay=delay)
    return {title: classify_entry(title, entry) for title, entry in papers.items()}


def main():
    parser = argparse.ArgumentParser(description="Filter and classify Text-to-SQL papers")
    parser.add_argument("input", help="Input JSON from crawler or extractor")
    parser.add_argument("--output", "-o", help="Output JSON path")
    parser.add_argument("--phase", choices=["filter", "label", "all"], default="all")
    parser.add_argument("--backend", choices=["rules", "bedrock"], default="rules")
    parser.add_argument("--model", default="us.anthropic.claude-sonnet-4-6")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        papers = json.load(f)
    print(f"Loaded {len(papers)} papers", file=sys.stderr)

    if args.phase in ("filter", "all"):
        papers = filter_papers(papers)
        print(f"After relevance filter: {len(papers)} papers", file=sys.stderr)

    if args.dry_run:
        for title in list(papers)[:30]:
            print(f"  - {title}", file=sys.stderr)
        return

    if args.phase in ("label", "all"):
        papers = label_papers(
            papers,
            backend=args.backend,
            model=args.model,
            region=args.region,
            delay=args.delay,
        )
        print(f"Classified {len(papers)} papers", file=sys.stderr)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(papers, f, indent=2, ensure_ascii=False)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        json.dump(papers, sys.stdout, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
