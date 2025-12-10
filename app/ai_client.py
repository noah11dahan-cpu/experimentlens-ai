import os
import json
from typing import List, Dict, Any

import requests
from dotenv import load_dotenv

# Load .env variables (DATABASE_URL, LLM_MODEL, OLLAMA_HOST)
load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")


def generate_report(experiment: Any, variants: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    experiment: an object or dict with at least .name and .hypothesis (or ['name'], ['hypothesis'])
    variants: list of dicts like:
      {
        "name": "A",
        "users": 1000,
        "conversions": 120,
        "conversion_rate": 0.12,
        "uplift": 0.033,  # optional
        "p_value": 0.04   # optional
      }

    Returns:
      {
        "report_text": "...",
        "recommendation": "ship" | "dont_ship" | "more_data"
      }
    """

    # Works if experiment is ORM object OR plain dict
    exp_name = getattr(experiment, "name", None) or experiment.get("name")
    exp_hypothesis = getattr(experiment, "hypothesis", None) or experiment.get("hypothesis")

    # Build a text block summarizing variants
    variants_text_lines = []
    for v in variants:
        line = (
            f"Variant {v.get('name')}: "
            f"users={v.get('users')}, "
            f"conversions={v.get('conversions')}, "
            f"conversion_rate={v.get('conversion_rate')}"
        )
        if v.get("uplift") is not None:
            line += f", uplift_vs_control={v.get('uplift')}"
        if v.get("p_value") is not None:
            line += f", p_value_vs_control={v.get('p_value')}"
        variants_text_lines.append(line)

    variants_block = "\n".join(variants_text_lines)

    # Instruction as in your spec
    prompt = f"""
You are an expert data analyst. I will give you A/B experiment stats that are already computed.
Do not recompute the numbers; only interpret them.

Experiment name: {exp_name}
Hypothesis: {exp_hypothesis}

Here are the variants and stats:
{variants_block}

Your job:
1. Explain in simple English what happened.
2. Say clearly if the result is statistically significant or not (based on p < 0.05).
3. Make a recommendation: "ship", "dont_ship", or "more_data".
4. Mention any risks or caveats (e.g. sample size too small, borderline p-values, low effect size).

Output JSON ONLY with keys:
- "report_text": string
- "recommendation": one of "ship", "dont_ship", "more_data"
""".strip()

    # Call Ollama chat API
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a careful data analyst who follows instructions exactly."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }

    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    # Ollama returns the whole conversation; we need the assistant message content
    content = data["message"]["content"].strip()

    # Try to parse JSON from the model
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # If the model didn't obey perfectly, wrap raw text
        parsed = {
            "report_text": content,
            "recommendation": "more_data",
        }

    report_text = parsed.get("report_text", "")
    recommendation = parsed.get("recommendation", "more_data")

    return {
        "report_text": report_text,
        "recommendation": recommendation,
    }
