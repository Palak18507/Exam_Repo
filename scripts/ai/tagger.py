import requests
import hashlib
import json
import re

# CONFIG

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

# HELPING FUNCTIONS

def normalize_text(text: str) -> str:
    """
    Normalize text for hashing:
    - lowercase
    - remove punctuation
    - collapse whitespace
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sha256_hash(text: str) -> str:
    """
    Generate SHA-256 hash of normalized text
    """
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# Calling OLLAMA

def ollama_generate(prompt: str) -> str:
    response = requests.post(
        OLLAMA_URL,
        timeout=None,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )
    response.raise_for_status()
    return response.json()["response"].strip()


# Adding AI tags with confidence scores

def generate_tags_with_confidence(text: str):
    """
    Returns:
    - ai_tags: list[str]
    - ai_confidence: dict[tag -> confidence]
    """

    prompt = f"""
Extract 3–5 concise technical keywords from the following exam question.
Assign a confidence score between 0 and 1 for each keyword.

Return ONLY valid JSON in the following format:
{{
  "tags": ["tag1", "tag2"],
  "confidence": {{
    "tag1": 0.95,
    "tag2": 0.87
  }}
}}

Question:
{text}
"""

    raw_output = ollama_generate(prompt)

    try:
        parsed = json.loads(raw_output)
        ai_tags = parsed.get("tags", [])
        ai_confidence = parsed.get("confidence", {})
    except json.JSONDecodeError:
        # Fallback safety
        ai_tags = []
        ai_confidence = {}

    return ai_tags, ai_confidence

# Adding AI-assisted mapping with syllabus topic
def generate_syllabus_topics(text: str):
    """
    AI-assisted semantic topic mapping (NOT matched with actual syllabus handed out by the University)
    """

    prompt = f"""
Identify 1–3 high-level academic subject areas this exam question belongs to.
These should be broad concepts (e.g., Operating Systems, Data Structures).

Return ONLY a comma-separated list.

Question:
{text}
"""

    output = ollama_generate(prompt)
    topics = [t.strip() for t in output.split(",") if t.strip()]
    return topics


# Adding the fields of ai_tags, hash, ai_confidence and syllabus_topics to question and subpart

def enrich_text(text: str, level: str = "question"):
    """
    Enrich question or subpart text with:
    - hash
    - ai_tags
    - ai_confidence
    - syllabus_topics

    level: "question" | "subpart"
    """

    metadata = {}

    # Hashing
    hash_value = sha256_hash(text)
    if level == "question":
        metadata["question_hash"] = hash_value
    else:
        metadata["subquestion_hash"] = hash_value

    # AI tags + confidence
    ai_tags, ai_confidence = generate_tags_with_confidence(text)
    metadata["ai_tags"] = ai_tags
    metadata["ai_confidence"] = ai_confidence

    # Syllabus / concept topics
    metadata["syllabus_topics"] = generate_syllabus_topics(text)

    return metadata

def enrich_exam_json(exam_json: dict) -> dict:
    """
    End-to-end enrichment pipeline.
    Takes a raw exam JSON and returns an enriched exam JSON.
    """

    enriched = exam_json.copy()

    for question in enriched.get("questions", []):

        # Question-level enrichment
        q_text = question.get("question_text", "")
        q_meta = enrich_text(q_text, level="question")

        question.update(q_meta)

        # Subpart-level enrichment
        for subpart in question.get("subparts", []):
            sp_text = subpart.get("text", "")
            sp_meta = enrich_text(sp_text, level="subpart")

            subpart.update(sp_meta)

    return enriched

# DEMO

if __name__ == "__main__":
    question_text = "What is a deadlock? Explain its necessary conditions."

    enriched_question = enrich_text(question_text, level="question")

    print("Input text:")
    print(question_text)
    print("\nAI metadata:")
    print(json.dumps(enriched_question, indent=2))