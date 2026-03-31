"""
Builds ChromaDB vector index from questions in PostgreSQL.
Can be called per-paper (in pipeline) or as a bulk rebuild.
"""

from sentence_transformers import SentenceTransformer
from chroma.client import get_collection
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load model once at module level
_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _safe_join(items):
    return " ".join(str(i) for i in items if i) if items else ""


def build_embedding_text(subject, unit, text, tags, topics, marks):
    """Build a rich text string for embedding — repeats tags/topics for weight."""
    tag_text = _safe_join(tags)
    topic_text = _safe_join(topics)

    return (
        f"Subject: {subject}. "
        f"Unit: {unit}. "
        f"Marks: {marks}. "
        f"Question: {text}. "
        f"Concepts: {tag_text}. {tag_text}. "
        f"Syllabus: {topic_text}. {topic_text}."
    )


def insert_paper_to_chroma(paper_id, metadata, questions):
    """Insert all questions/subparts from one paper into ChromaDB."""
    model = get_model()

    subject = metadata.get("subject_name", "")
    department = metadata.get("branch") or metadata.get("department", "")
    semester = metadata.get("semester", 0)
    exam_type = metadata.get("exam_type", "")
    academic_year = metadata.get("academic_year", "")

    documents = []
    metadatas = []
    ids = []
    seen_ids = set()

    def unique_id(base_id):
        uid = base_id
        i = 1
        while uid in seen_ids:
            uid = f"{base_id}_{i}"
            i += 1
        seen_ids.add(uid)
        return uid

    for q in questions:
        q_text = q.get("question_text", "")
        if not q_text or q_text == "Attempt all parts.":
            # Skip parent questions, index subparts instead
            pass
        else:
            q_id = unique_id(q.get("q_id") or f"{paper_id}_{q.get('question_id', 'x')}")
            unit = q.get("unit", "")

            doc = build_embedding_text(
                subject, unit, q_text,
                q.get("ai_tags"), q.get("syllabus_topics"),
                q.get("marks"),
            )

            documents.append(doc)
            ids.append(q_id)
            metadatas.append({
                "paper_id": paper_id,
                "type": "question",
                "subject_name": subject,
                "department": department,
                "semester": semester or 0,
                "exam_type": exam_type,
                "academic_year": academic_year,
                "unit": unit or "",
            })

        # Subparts
        for sp in q.get("subparts", []):
            sp_text = sp.get("text", "")
            if not sp_text:
                continue

            sp_id = unique_id(sp.get("s_id") or f"{paper_id}_{q.get('question_id', 'x')}_{sp.get('subpart_id', 'x')}")
            unit = q.get("unit", "")

            doc = build_embedding_text(
                subject, unit, sp_text,
                sp.get("ai_tags"), sp.get("syllabus_topics"),
                sp.get("marks"),
            )

            documents.append(doc)
            ids.append(sp_id)
            metadatas.append({
                "paper_id": paper_id,
                "type": "subpart",
                "subject_name": subject,
                "department": department,
                "semester": semester or 0,
                "exam_type": exam_type,
                "academic_year": academic_year,
                "unit": unit or "",
            })

    if not documents:
        return 0

    # Batch encode and insert
    embeddings = model.encode(documents).tolist()

    # ChromaDB upsert (handles duplicates)
    get_collection().upsert(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )

    return len(ids)


def rebuild_from_json_dir(json_dir):
    """Bulk rebuild ChromaDB from all JSON files in a directory."""
    import json
    from config import get_branch

    json_dir = Path(json_dir)
    total = 0

    for json_file in sorted(json_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  [chroma] SKIP bad JSON: {json_file.name} ({e})")
            continue

        paper_id = data.get("paper_id", json_file.stem)
        metadata = data.get("paper_metadata", {})
        metadata["branch"] = get_branch(metadata.get("subject_code"))

        questions = data.get("questions", [])
        count = insert_paper_to_chroma(paper_id, metadata, questions)
        total += count
        print(f"  [chroma] {paper_id}: {count} vectors")

    print(f"\n  [chroma] Total: {total} vectors indexed")
    return total
