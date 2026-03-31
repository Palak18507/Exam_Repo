import hashlib
import json
from pathlib import Path
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.database import get_session
from db.models import ExamPaper, PaperMetadata, Question, Subpart


def _hash_text(text):
    """SHA-256 hash of normalized question text."""
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def upsert_paper(paper_id, metadata, json_file_path, source_file_path=None):
    """Insert or update all data for a paper: exam_papers, paper_metadata, questions, subparts."""
    session = get_session()
    try:
        # 1. exam_papers table
        paper_values = {
            "paper_id": paper_id,
            "pdf_path": str(source_file_path) if source_file_path else str(json_file_path),
        }
        stmt = pg_insert(ExamPaper).values(**paper_values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["paper_id"],
            set_={
                "pdf_path": paper_values["pdf_path"],
                "created_at": func.now(),
            },
        )
        session.execute(stmt)

        # 2. paper_metadata table
        meta_values = {
            "paper_id": paper_id,
            "subject_code": metadata.get("subject_code", "UNKNOWN"),
            "subject_name": metadata.get("subject_name", "Unknown"),
            "program": metadata.get("program", "Unknown"),
            "department": metadata.get("branch"),
            "semester": metadata.get("semester", 0),
            "academic_year": metadata.get("academic_year", "Unknown"),
            "exam_type": metadata.get("exam_type", "Unknown"),
            "exam_name": metadata.get("exam_name"),
            "time_duration": metadata.get("time_duration", "Unknown"),
            "max_marks": metadata.get("max_marks", 0),
        }
        stmt = pg_insert(PaperMetadata).values(**meta_values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["paper_id"],
            set_={k: v for k, v in meta_values.items() if k != "paper_id"},
        )
        session.execute(stmt)

        # 3. Load questions from JSON file
        json_path = Path(json_file_path)
        if json_path.exists():
            data = json.loads(json_path.read_text(encoding="utf-8"))
            questions = data.get("questions", [])

            for q in questions:
                q_text = q.get("question_text", "")
                q_hash = _hash_text(q_text) if q_text else ""
                q_id = f"{paper_id}_{q_hash[:8]}"

                q_values = {
                    "q_id": q_id,
                    "paper_id": paper_id,
                    "question_id": q.get("question_id", ""),
                    "unit": q.get("unit"),
                    "question_text": {"type": "text", "value": q_text},
                    "marks": q.get("marks") or 0,
                    "question_hash": q_hash,
                    "question_ai_tags": q.get("ai_tags"),
                    "question_ai_confidence": q.get("ai_confidence"),
                    "question_syllabus_topics": q.get("syllabus_topics"),
                }
                stmt = pg_insert(Question).values(**q_values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["q_id"],
                    set_={k: v for k, v in q_values.items() if k != "q_id"},
                )
                session.execute(stmt)

                # 4. Subparts
                for sp in q.get("subparts", []):
                    sp_text = sp.get("text", "")
                    sp_hash = _hash_text(sp_text) if sp_text else None
                    s_id = f"{q_id}_{sp.get('subpart_id', 'x')}"

                    sp_values = {
                        "s_id": s_id,
                        "q_id": q_id,
                        "paper_id": paper_id,
                        "subpart_id": sp.get("subpart_id", ""),
                        "text": {"type": "text", "value": sp_text},
                        "marks": sp.get("marks") or 0,
                        "subquestion_hash": sp_hash,
                        "subpart_ai_tags": sp.get("ai_tags"),
                        "subpart_ai_confidence": sp.get("ai_confidence"),
                        "subpart_syllabus_topics": sp.get("syllabus_topics"),
                    }
                    stmt = pg_insert(Subpart).values(**sp_values)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["s_id"],
                        set_={k: v for k, v in sp_values.items() if k != "s_id"},
                    )
                    session.execute(stmt)

        session.commit()
        print(f"  [db] Upserted: {paper_id}")
    except Exception as e:
        session.rollback()
        print(f"  [db] Error inserting {paper_id}: {e}")
        raise
    finally:
        session.close()
