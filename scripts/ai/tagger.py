"""
AI enrichment for exam questions using local Ollama LLM.

Requires:
    ollama pull mistral
    ollama serve

Adds to each question/subpart:
    - ai_tags: ["Deadlock", "Concurrency", ...]
    - ai_confidence: {"Deadlock": 1.0, "Concurrency": 0.95}
    - syllabus_topics: ["Operating Systems", "Concurrency Control"]
"""

import requests
import hashlib
import json
import re
import os
import time
import copy
import logging
from typing import List, Dict, Tuple
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = str(CACHE_DIR / "ai_cache.json")

MAX_SUBPARTS_PER_BATCH = 4

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


# ── Cache ──

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


# ── Helpers ──

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sha256_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode()).hexdigest()


def clean_json_output(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def is_valid_llm_output(data: dict) -> bool:
    return bool(data.get("tags") or data.get("syllabus_topics"))


# ── LLM Call ──

def ollama_generate_with_retry(prompt: str, max_retries: int = 3) -> Tuple[dict, float]:
    total_latency = 0.0

    for attempt in range(1, max_retries + 1):
        start = time.time()
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
                timeout=30,
            )
            response.raise_for_status()

            latency = time.time() - start
            total_latency += latency

            raw_output = response.json().get("response", "")
            cleaned = clean_json_output(raw_output)
            parsed = json.loads(cleaned)
            return parsed, total_latency

        except requests.exceptions.RequestException as e:
            logging.error(f"Attempt {attempt}: Network error: {e}")
        except json.JSONDecodeError:
            logging.warning(f"Attempt {attempt}: Invalid JSON. Retrying...")

        time.sleep(attempt)

    logging.error("LLM failed after retries")
    return {}, total_latency


def is_ollama_available() -> bool:
    """Check if Ollama server is running."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


# ── Prompts ──

def build_question_prompt(question_text: str) -> str:
    return f"""Extract:
- 3-5 technical keywords
- confidence per keyword
- 1-3 syllabus topics

Return JSON only:

{{
  "question": {{
    "tags": [],
    "confidence": {{}},
    "syllabus_topics": []
  }}
}}

Question:
{question_text}"""


def build_subpart_prompt(question_text: str, subparts: List[Dict]) -> str:
    prompt = f"""Analyze subparts.

Return JSON:

{{
  "subparts": {{
    "a": {{
      "tags": [],
      "confidence": {{}},
      "syllabus_topics": []
    }}
  }}
}}

Context:
{question_text}

"""
    for sp in subparts:
        prompt += f"{sp['subpart_id']}) {sp['text']}\n"

    return prompt


# ── Main ──

def enrich_exam_json(exam_json: dict) -> Tuple[dict, dict]:
    """Enrich all questions and subparts in an exam JSON with AI tags.

    Returns: (enriched_json, metrics_dict)
    """
    cache = load_cache()
    enriched = copy.deepcopy(exam_json)

    total_llm_calls = 0
    total_llm_time = 0.0

    for question in enriched.get("questions", []):
        q_text = question.get("question_text", "")
        q_hash = sha256_hash(q_text)
        question["question_hash"] = q_hash
        subparts = question.get("subparts", [])

        # ── Question ──
        if q_hash in cache:
            question.update(cache[q_hash])
        else:
            prompt = build_question_prompt(q_text)
            result_dict, latency = ollama_generate_with_retry(prompt)
            total_llm_calls += 1
            total_llm_time += latency

            q_data = result_dict.get("question", {})
            if not is_valid_llm_output(q_data):
                q_data = {}

            meta = {
                "ai_tags": q_data.get("tags", []),
                "ai_confidence": q_data.get("confidence", {}),
                "syllabus_topics": q_data.get("syllabus_topics", []),
            }
            question.update(meta)

            if meta["ai_tags"] or meta["syllabus_topics"]:
                cache[q_hash] = meta

        # ── Subparts ──
        uncached = []
        for sp in subparts:
            sp_text = sp.get("text", "")
            sp_hash = sha256_hash(sp_text)
            sp["subquestion_hash"] = sp_hash

            if sp_hash in cache:
                sp.update(cache[sp_hash])
            else:
                uncached.append(sp)

        for i in range(0, len(uncached), MAX_SUBPARTS_PER_BATCH):
            batch = uncached[i : i + MAX_SUBPARTS_PER_BATCH]
            prompt = build_subpart_prompt(q_text, batch)
            result_dict, latency = ollama_generate_with_retry(prompt)
            total_llm_calls += 1
            total_llm_time += latency

            sub_res = result_dict.get("subparts", {})
            for sp in batch:
                sp_id = sp.get("subpart_id")
                sp_hash = sp.get("subquestion_hash")
                data = sub_res.get(sp_id, {})

                if not is_valid_llm_output(data):
                    data = {}

                meta = {
                    "ai_tags": data.get("tags", []),
                    "ai_confidence": data.get("confidence", {}),
                    "syllabus_topics": data.get("syllabus_topics", []),
                }
                sp.update(meta)

                if meta["ai_tags"] or meta["syllabus_topics"]:
                    cache[sp_hash] = meta

    save_cache(cache)

    metrics = {
        "llm_calls": total_llm_calls,
        "total_time": round(total_llm_time, 3),
        "avg_latency": round(total_llm_time / total_llm_calls, 3) if total_llm_calls else 0,
    }

    return enriched, metrics
