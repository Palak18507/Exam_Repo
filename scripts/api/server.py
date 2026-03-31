"""
FastAPI server for the Exam Papers Archive.

Run with:
    cd scripts
    python -m uvicorn api.server:app --reload --port 8001
"""

import shutil
import threading
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, cast, String, desc

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import PROJECT_ROOT
from db.database import get_session, init_db
from db.models import ExamPaper, PaperMetadata, Question, Subpart

app = FastAPI(title="Exam Papers Archive API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# ─── GET /api/filters ───────────────────────────────────────────
@app.get("/api/filters")
def get_filters():
    """Return all unique values for each filterable field."""
    session = get_session()
    try:
        def distinct_values(column):
            return sorted([
                r[0] for r in session.query(column).distinct().all()
                if r[0] is not None
            ])

        return {
            "branches": distinct_values(PaperMetadata.department),
            "semesters": sorted([
                r[0] for r in session.query(PaperMetadata.semester).distinct().all()
                if r[0] is not None and r[0] > 0
            ]),
            "academic_years": distinct_values(PaperMetadata.academic_year),
            "exam_types": distinct_values(PaperMetadata.exam_type),
            "subjects": [
                {"code": r[0], "name": r[1]}
                for r in session.query(
                    PaperMetadata.subject_code,
                    PaperMetadata.subject_name,
                ).distinct().order_by(PaperMetadata.subject_code).all()
                if r[0] is not None
            ],
        }
    finally:
        session.close()


# ─── GET /api/stats ──────────────────────────────────────────────
@app.get("/api/stats")
def get_stats():
    """Return aggregate stats for the analytics cards."""
    session = get_session()
    try:
        total = session.query(func.count(PaperMetadata.paper_id)).scalar()
        subjects = session.query(
            func.count(func.distinct(PaperMetadata.subject_code))
        ).scalar()

        trending_row = (
            session.query(
                PaperMetadata.subject_name,
                func.count(PaperMetadata.paper_id).label("cnt"),
            )
            .filter(PaperMetadata.subject_name.isnot(None))
            .group_by(PaperMetadata.subject_name)
            .order_by(func.count(PaperMetadata.paper_id).desc())
            .first()
        )

        latest_year = (
            session.query(PaperMetadata.academic_year)
            .order_by(PaperMetadata.academic_year.desc())
            .first()
        )
        this_year_count = 0
        if latest_year and latest_year[0]:
            this_year_count = (
                session.query(func.count(PaperMetadata.paper_id))
                .filter(PaperMetadata.academic_year == latest_year[0])
                .scalar()
            )

        return {
            "totalPapers": total,
            "subjectsCovered": subjects,
            "trendingTopic": trending_row[0] if trending_row else "N/A",
            "addedThisYear": this_year_count,
        }
    finally:
        session.close()


# ─── GET /api/suggestions ────────────────────────────────────────
@app.get("/api/suggestions")
def get_suggestions(q: str = Query("", min_length=1)):
    """Return autocomplete suggestions for the search bar."""
    session = get_session()
    try:
        starts = f"{q}%"
        contains = f"%{q}%"

        starts_names = [
            r[0] for r in session.query(func.distinct(PaperMetadata.subject_name))
            .filter(PaperMetadata.subject_name.ilike(starts))
            .order_by(PaperMetadata.subject_name).limit(5).all() if r[0]
        ]
        starts_codes = [
            r[0] for r in session.query(func.distinct(PaperMetadata.subject_code))
            .filter(PaperMetadata.subject_code.ilike(starts))
            .order_by(PaperMetadata.subject_code).limit(5).all() if r[0]
        ]
        starts_branches = [
            r[0] for r in session.query(func.distinct(PaperMetadata.department))
            .filter(PaperMetadata.department.ilike(starts)).limit(5).all() if r[0]
        ]
        contains_names = [
            r[0] for r in session.query(func.distinct(PaperMetadata.subject_name))
            .filter(PaperMetadata.subject_name.ilike(contains))
            .order_by(PaperMetadata.subject_name).limit(5).all() if r[0]
        ]

        seen = set()
        results = []
        for item in starts_branches + starts_codes + starts_names + contains_names:
            key = item.strip().lower()
            if key not in seen:
                seen.add(key)
                results.append(item.strip())
            if len(results) >= 10:
                break
        return results
    finally:
        session.close()


# ─── 1. GET /api/search ─────────────────────────────────────────
@app.get("/api/search")
@app.get("/api/papers")
def search_papers(
    search: str = Query("", description="Free-text search"),
    subject_name: str = Query("", description="Filter by subject name"),
    subject_code: str = Query("", description="Filter by subject code"),
    branch: str = Query("", description="Filter by branch/department"),
    department: str = Query("", description="Alias for branch"),
    semester: str = Query("", description="Filter by semester number"),
    exam_type: str = Query("", description="Filter by exam type"),
    academic_year: str = Query("", description="Filter by academic year"),
):
    """Search and filter exam papers."""
    session = get_session()
    try:
        q = session.query(PaperMetadata).join(ExamPaper)
        dept = branch or department

        if search:
            pattern = f"%{search}%"
            q = q.filter(
                or_(
                    PaperMetadata.subject_name.ilike(pattern),
                    PaperMetadata.subject_code.ilike(pattern),
                    PaperMetadata.paper_id.ilike(pattern),
                    PaperMetadata.department.ilike(pattern),
                    PaperMetadata.program.ilike(pattern),
                )
            )
        if subject_name:
            q = q.filter(PaperMetadata.subject_name.ilike(f"%{subject_name}%"))
        if subject_code:
            q = q.filter(PaperMetadata.subject_code == subject_code)
        if dept:
            q = q.filter(PaperMetadata.department == dept)
        if semester:
            q = q.filter(PaperMetadata.semester == int(semester))
        if exam_type:
            q = q.filter(PaperMetadata.exam_type == exam_type)
        if academic_year:
            q = q.filter(PaperMetadata.academic_year == academic_year)

        results = q.order_by(
            PaperMetadata.academic_year.desc(),
            PaperMetadata.subject_code,
        ).all()

        return {
            "papers": [
                {
                    "paper_id": r.paper_id,
                    "subject_code": r.subject_code,
                    "subject_name": r.subject_name,
                    "program": r.program,
                    "department": r.department,
                    "semester": r.semester,
                    "academic_year": r.academic_year,
                    "exam_type": r.exam_type,
                    "exam_name": r.exam_name,
                    "time_duration": r.time_duration,
                    "max_marks": float(r.max_marks) if r.max_marks else None,
                }
                for r in results
            ]
        }
    finally:
        session.close()


# ─── 2. GET /api/paper/{paper_id} ───────────────────────────────
@app.get("/api/paper/{paper_id}")
def get_paper_details(paper_id: str):
    """Fetch full paper details and metadata."""
    session = get_session()
    try:
        paper = session.query(ExamPaper).filter_by(paper_id=paper_id).first()
        meta = session.query(PaperMetadata).filter_by(paper_id=paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        return {
            "paper": {
                "paper_id": paper.paper_id,
                "file_path": paper.pdf_path,
                "created_at": str(paper.created_at) if paper.created_at else None,
            },
            "metadata": {
                "subject_code": meta.subject_code,
                "subject_name": meta.subject_name,
                "program": meta.program,
                "department": meta.department,
                "semester": meta.semester,
                "academic_year": meta.academic_year,
                "exam_type": meta.exam_type,
                "exam_name": meta.exam_name,
                "time_duration": meta.time_duration,
                "max_marks": float(meta.max_marks) if meta.max_marks else None,
            } if meta else None,
        }
    finally:
        session.close()


# ─── 3. GET /api/paper/{paper_id}/questions ──────────────────────
@app.get("/api/paper/{paper_id}/questions")
def get_paper_questions(paper_id: str):
    """Returns all questions and subparts for a paper."""
    session = get_session()
    try:
        questions = session.query(Question).filter_by(paper_id=paper_id).order_by(Question.question_id).all()
        if not questions:
            raise HTTPException(status_code=404, detail="No questions found for this paper")

        result = []
        for q in questions:
            subparts = session.query(Subpart).filter_by(q_id=q.q_id).order_by(Subpart.subpart_id).all()
            result.append({
                "q_id": q.q_id,
                "question_id": q.question_id,
                "unit": q.unit,
                "question_text": q.question_text,
                "marks": float(q.marks) if q.marks else None,
                "question_hash": q.question_hash,
                "ai_tags": q.question_ai_tags,
                "ai_confidence": q.question_ai_confidence,
                "syllabus_topics": q.question_syllabus_topics,
                "subparts": [
                    {
                        "s_id": sp.s_id,
                        "subpart_id": sp.subpart_id,
                        "text": sp.text,
                        "marks": float(sp.marks) if sp.marks else None,
                        "subquestion_hash": sp.subquestion_hash,
                        "ai_tags": sp.subpart_ai_tags,
                        "ai_confidence": sp.subpart_ai_confidence,
                        "syllabus_topics": sp.subpart_syllabus_topics,
                    }
                    for sp in subparts
                ],
            })

        return {"questions": result}
    finally:
        session.close()


# ─── 4. GET /api/question/{q_id} ────────────────────────────────
@app.get("/api/question/{q_id}")
def get_question(q_id: str):
    """Fetch a specific question with its subparts."""
    session = get_session()
    try:
        q = session.query(Question).filter_by(q_id=q_id).first()
        if not q:
            raise HTTPException(status_code=404, detail="Question not found")

        subparts = session.query(Subpart).filter_by(q_id=q_id).order_by(Subpart.subpart_id).all()

        return {
            "question": {
                "q_id": q.q_id,
                "paper_id": q.paper_id,
                "question_id": q.question_id,
                "unit": q.unit,
                "question_text": q.question_text,
                "marks": float(q.marks) if q.marks else None,
                "question_hash": q.question_hash,
            },
            "subparts": [
                {
                    "s_id": sp.s_id,
                    "subpart_id": sp.subpart_id,
                    "text": sp.text,
                    "marks": float(sp.marks) if sp.marks else None,
                }
                for sp in subparts
            ],
        }
    finally:
        session.close()


# ─── 5. GET /api/repeated/question/{hash} ───────────────────────
@app.get("/api/repeated/question/{hash}")
def get_repeated_questions(hash: str):
    """Returns all questions that have the same hash (repeated across papers)."""
    session = get_session()
    try:
        questions = session.query(Question).filter_by(question_hash=hash).all()
        return {
            "repeated_questions": [
                {
                    "q_id": q.q_id,
                    "paper_id": q.paper_id,
                    "question_id": q.question_id,
                    "unit": q.unit,
                    "question_text": q.question_text,
                    "marks": float(q.marks) if q.marks else None,
                }
                for q in questions
            ]
        }
    finally:
        session.close()


# ─── 6. GET /api/repeated/subpart/{hash} ────────────────────────
@app.get("/api/repeated/subpart/{hash}")
def get_repeated_subparts(hash: str):
    """Returns repeated sub-questions by hash."""
    session = get_session()
    try:
        subparts = session.query(Subpart).filter_by(subquestion_hash=hash).all()
        return {
            "repeated_subparts": [
                {
                    "s_id": sp.s_id,
                    "q_id": sp.q_id,
                    "paper_id": sp.paper_id,
                    "subpart_id": sp.subpart_id,
                    "text": sp.text,
                    "marks": float(sp.marks) if sp.marks else None,
                }
                for sp in subparts
            ]
        }
    finally:
        session.close()


# ─── GET /api/questions/search ───────────────────────────────────
@app.get("/api/questions/search")
def search_questions(
    search: str = Query("", description="Free-text search in question text"),
    branch: str = Query("", description="Filter by department"),
    subject_code: str = Query("", description="Filter by subject code"),
    limit: int = Query(50, description="Max results"),
):
    """Search questions across all papers. Used by Question Bank tab."""
    session = get_session()
    try:
        q = session.query(Question, PaperMetadata).join(
            PaperMetadata, Question.paper_id == PaperMetadata.paper_id
        ).filter(~cast(Question.question_text, String).ilike("%Attempt all parts%"))

        if search:
            pattern = f"%{search}%"
            q = q.filter(cast(Question.question_text, String).ilike(pattern))
        if branch:
            q = q.filter(PaperMetadata.department == branch)
        if subject_code:
            q = q.filter(PaperMetadata.subject_code == subject_code)

        results = q.limit(limit).all()

        return {
            "questions": [
                {
                    "q_id": question.q_id,
                    "question_id": question.question_id,
                    "question_text": question.question_text,
                    "unit": question.unit,
                    "marks": float(question.marks) if question.marks else None,
                    "question_hash": question.question_hash,
                    "paper_id": question.paper_id,
                    "subject_name": meta.subject_name,
                    "subject_code": meta.subject_code,
                    "department": meta.department,
                    "academic_year": meta.academic_year,
                    "exam_type": meta.exam_type,
                }
                for question, meta in results
            ]
        }
    finally:
        session.close()


# ─── GET /api/questions/repeated ─────────────────────────────────
@app.get("/api/questions/repeated")
def get_all_repeated_questions(
    branch: str = Query("", description="Filter by department"),
    subject_code: str = Query("", description="Filter by subject code"),
    search: str = Query("", description="Filter by text"),
    min_count: int = Query(2, description="Min appearances to count as repeated"),
):
    """Returns questions that appear in 2+ papers (by hash). Used by Frequently Asked tab."""
    session = get_session()
    try:
        # Find hashes that appear in multiple papers
        hash_q = (
            session.query(
                Question.question_hash,
                func.count(func.distinct(Question.paper_id)).label("paper_count"),
            )
            .join(PaperMetadata, Question.paper_id == PaperMetadata.paper_id)
            .filter(Question.question_hash != "")
            .filter(~cast(Question.question_text, String).ilike("%Attempt all parts%"))
        )

        if branch:
            hash_q = hash_q.filter(PaperMetadata.department == branch)
        if search:
            hash_q = hash_q.filter(cast(Question.question_text, String).ilike(f"%{search}%"))

        # When a subject is selected, only show repeats within that exact subject.
        # Widening to prefix/department showed unrelated results (e.g., Cyber Security
        # for Business Communication) — so we keep it strict.
        scope_filters = []
        if subject_code:
            scope_filters = [
                PaperMetadata.subject_code == subject_code,
            ]
        else:
            scope_filters = [None]  # no subject filter

        results = []
        for scope_filter in scope_filters:
            scoped_q = hash_q
            if scope_filter is not None:
                scoped_q = scoped_q.filter(scope_filter)

            scoped_q = (
                scoped_q.group_by(Question.question_hash)
                .having(func.count(func.distinct(Question.paper_id)) >= min_count)
                .order_by(func.count(func.distinct(Question.paper_id)).desc())
                .limit(50)
            )

            repeated_hashes = scoped_q.all()
            if repeated_hashes:
                for qhash, paper_count in repeated_hashes:
                    instances = (
                        session.query(Question, PaperMetadata)
                        .join(PaperMetadata, Question.paper_id == PaperMetadata.paper_id)
                        .filter(Question.question_hash == qhash)
                        .all()
                    )
                    if instances:
                        first_q, _ = instances[0]
                        results.append({
                            "question_hash": qhash,
                            "question_text": first_q.question_text,
                            "paper_count": paper_count,
                            "instances": [
                                {
                                    "q_id": q.q_id,
                                    "paper_id": q.paper_id,
                                    "subject_name": m.subject_name,
                                    "subject_code": m.subject_code,
                                    "department": m.department,
                                    "academic_year": m.academic_year,
                                    "exam_type": m.exam_type,
                                }
                                for q, m in instances
                            ],
                        })
                break  # found results at this scope, stop widening

        return {"repeated": results}
    finally:
        session.close()


# ─── GET /api/papers/{paper_id}/download ─────────────────────────
@app.get("/api/papers/{paper_id}/download")
def download_paper(paper_id: str):
    """Serve the original PDF/docx file for download."""
    session = get_session()
    try:
        paper = session.query(ExamPaper).filter_by(paper_id=paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        source = Path(paper.pdf_path) if paper.pdf_path else None
        if not source or not source.exists():
            raise HTTPException(status_code=404, detail="Source file not found on disk")

        return FileResponse(
            path=str(source),
            filename=source.name,
            media_type="application/octet-stream",
        )
    finally:
        session.close()


# ─── SEMANTIC SEARCH (ChromaDB) ──────────────────────────────────

try:
    from chroma.search import semantic_search, find_similar, find_topic_clusters
    _chroma_ok = True
except ImportError:
    _chroma_ok = False


@app.get("/api/semantic/topics")
def get_topic_clusters(
    subject_name: str = Query("", description="Filter by subject name"),
    department: str = Query("", description="Filter by department/branch"),
    threshold: float = Query(0.65, description="Similarity threshold (0.5-0.95)"),
):
    """Cluster questions by topic — finds frequently asked concepts even if worded differently."""
    if not _chroma_ok:
        raise HTTPException(status_code=503, detail="ChromaDB not available")

    filters = {}
    if subject_name:
        filters["subject_name"] = subject_name
    elif department:
        filters["department"] = department

    if not filters:
        # Global — limit to avoid huge computation
        filters = {}

    clusters = find_topic_clusters(filters, similarity_threshold=threshold)
    total_appearances = sum(c["count"] for c in clusters)
    return {
        "topics": clusters,
        "total_topics": len(clusters),
        "total_appearances": total_appearances,
    }


@app.get("/api/semantic/search")
def semantic_question_search(
    query: str = Query("", min_length=1, description="Natural language query"),
    department: str = Query("", description="Filter by department"),
    semester: int = Query(0, description="Filter by semester"),
    exam_type: str = Query("", description="Filter by exam type"),
    subject_name: str = Query("", description="Filter by subject name"),
    top_k: int = Query(15, description="Number of results"),
):
    """Semantic search — finds questions by meaning, not just keywords."""
    if not _chroma_ok:
        raise HTTPException(status_code=503, detail="ChromaDB not available")

    filters = {}
    if department:
        filters["department"] = department
    if semester:
        filters["semester"] = semester
    if exam_type:
        filters["exam_type"] = exam_type
    if subject_name:
        filters["subject_name"] = subject_name

    results = semantic_search(query, filters=filters or None, top_k=top_k)
    return {"results": results}


@app.get("/api/semantic/similar/{q_id}")
def similar_questions_endpoint(q_id: str, top_k: int = Query(10)):
    """Find questions similar to a given question."""
    if not _chroma_ok:
        raise HTTPException(status_code=503, detail="ChromaDB not available")

    session = get_session()
    try:
        q = session.query(Question).filter_by(q_id=q_id).first()
        if not q:
            raise HTTPException(status_code=404, detail="Question not found")

        q_text = q.question_text.get("value", "") if isinstance(q.question_text, dict) else str(q.question_text)
        results = find_similar(q_text, top_k=top_k)
        results = [r for r in results if r["id"] != q_id]
        return {"results": results}
    finally:
        session.close()


# ─── LIBRARIAN ENDPOINTS ─────────────────────────────────────────

UPLOAD_DIR = PROJECT_ROOT / "data" / "raw_pdfs" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


import uuid
import time

# ─── JOB TRACKING ──────────────────────────────────────────────
PIPELINE_JOBS = {}


def create_job(file_name):
    job_id = str(uuid.uuid4())
    PIPELINE_JOBS[job_id] = {
        "file_name": file_name,
        "status": "processing",
        "progress": 0,
        "message": "Starting pipeline...",
        "created_at": time.time(),
    }
    return job_id


def update_job(job_id, progress, message):
    if job_id in PIPELINE_JOBS:
        PIPELINE_JOBS[job_id]["progress"] = progress
        PIPELINE_JOBS[job_id]["message"] = message


def complete_job(job_id, paper_id=None):
    if job_id in PIPELINE_JOBS:
        PIPELINE_JOBS[job_id]["status"] = "completed"
        PIPELINE_JOBS[job_id]["progress"] = 100
        PIPELINE_JOBS[job_id]["message"] = "Completed successfully"
        if paper_id:
            PIPELINE_JOBS[job_id]["paper_id"] = paper_id


def fail_job(job_id, error):
    if job_id in PIPELINE_JOBS:
        PIPELINE_JOBS[job_id]["status"] = "failed"
        PIPELINE_JOBS[job_id]["message"] = str(error)


@app.get("/api/job/{job_id}")
def get_job_status(job_id: str):
    """Get pipeline job progress (polled by frontend after upload)."""
    job = PIPELINE_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _run_pipeline_async(file_path, job_id=None):
    """Run the pipeline in a background thread with progress tracking."""
    try:
        if job_id:
            update_job(job_id, 10, "Extracting text from document...")

        from extraction.pdf_to_text import process_file
        from config import EXTRACTED_TEXT_DIR, CLEANED_JSON_DIR, get_branch
        from cleaning.text_to_json import process_text_file
        from db.insert import upsert_paper

        # Step 1: Extract
        txt_path = process_file(file_path, EXTRACTED_TEXT_DIR)
        if not txt_path:
            if job_id:
                fail_job(job_id, "Unsupported file format")
            return

        if job_id:
            update_job(job_id, 30, "Parsing exam structure...")

        # Step 2: Parse
        result = process_text_file(txt_path, CLEANED_JSON_DIR)
        if not result:
            if job_id:
                fail_job(job_id, "Could not extract metadata")
            return

        json_path, metadata, paper_id = result
        metadata["branch"] = get_branch(metadata.get("subject_code"))

        # Step 3: AI Tagging (optional — skips if Ollama not running)
        if job_id:
            update_job(job_id, 50, "Running AI tagging...")

        try:
            from ai.tagger import enrich_exam_json, is_ollama_available
            if is_ollama_available():
                import json as json_lib
                data = json_lib.loads(json_path.read_text(encoding="utf-8"))
                enriched, metrics = enrich_exam_json(data)
                json_path.write_text(json_lib.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"  [ai] Tagged {paper_id}: {metrics['llm_calls']} calls in {metrics['total_time']}s")
            else:
                print(f"  [ai] Ollama not running, skipping AI tagging")
        except Exception as e:
            print(f"  [ai] Tagging skipped: {e}")

        if job_id:
            update_job(job_id, 70, "Saving to database...")

        # Step 4: DB insert
        upsert_paper(paper_id, metadata, json_path, source_file_path=file_path)

        # Step 5: ChromaDB index
        if job_id:
            update_job(job_id, 85, "Indexing for search...")

        try:
            import json as json_lib
            from chroma.builder import insert_paper_to_chroma
            data = json_lib.loads(json_path.read_text(encoding="utf-8"))
            count = insert_paper_to_chroma(paper_id, metadata, data.get("questions", []))
            print(f"  [chroma] {count} vectors indexed")
        except Exception as e:
            print(f"  [chroma] Warning: {e}")

        if job_id:
            complete_job(job_id, paper_id)

        print(f"  [upload] Pipeline completed for {file_path.name}")
    except Exception as e:
        if job_id:
            fail_job(job_id, str(e))
        print(f"  [upload] Pipeline failed for {file_path.name}: {e}")


@app.post("/api/upload")
async def upload_paper(
    file: UploadFile = File(..., description="PDF or DOCX file"),
):
    """Upload a paper — saves file and triggers the full pipeline."""
    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Validate file size (max 20MB)
    contents = await file.read()
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 20MB.")

    # Save the file
    save_path = UPLOAD_DIR / file.filename
    # Avoid overwriting — add suffix if file exists
    counter = 1
    while save_path.exists():
        stem = Path(file.filename).stem
        save_path = UPLOAD_DIR / f"{stem}_{counter}{ext}"
        counter += 1

    save_path.write_bytes(contents)
    print(f"  [upload] Saved: {save_path.name} ({len(contents)} bytes)")

    # Quick check: extract text and generate paper_id to see if it already exists
    is_reupload = False
    existing_paper_id = None
    existing_uploaded_at = None
    try:
        from extraction.pdf_to_text import process_file as extract_file
        from cleaning.text_to_json import parse_metadata, build_paper_id
        from config import EXTRACTED_TEXT_DIR

        txt_path = extract_file(save_path, EXTRACTED_TEXT_DIR)
        if txt_path:
            text = txt_path.read_text(encoding="utf-8")
            metadata, year_match = parse_metadata(text)
            paper_id = build_paper_id(metadata, year_match)
            if paper_id:
                session = get_session()
                try:
                    existing = session.query(ExamPaper).filter_by(paper_id=paper_id).first()
                    if existing:
                        is_reupload = True
                        existing_paper_id = paper_id
                        existing_uploaded_at = existing.created_at.isoformat() if existing.created_at else None
                finally:
                    session.close()
    except Exception:
        pass  # If quick check fails, just proceed normally

    # Create job for tracking
    job_id = create_job(file.filename)

    # Run pipeline in background thread with job tracking
    thread = threading.Thread(target=_run_pipeline_async, args=(save_path, job_id), daemon=True)
    thread.start()

    if is_reupload:
        return {
            "status": "reupload",
            "job_id": job_id,
            "message": f"Paper '{existing_paper_id}' was already uploaded. Re-processing with updated file.",
            "paper_id": existing_paper_id,
            "previously_uploaded_at": existing_uploaded_at,
            "file_size": len(contents),
        }

    return {
        "status": "processing",
        "job_id": job_id,
        "message": f"New paper uploaded! Pipeline processing '{file.filename}'...",
        "file_path": str(save_path),
        "file_size": len(contents),
    }


@app.get("/api/librarian/papers")
def get_librarian_papers(
    limit: int = Query(50, description="Max papers to return"),
    offset: int = Query(0, description="Offset for pagination"),
):
    """List all papers for the librarian manage table, newest first."""
    session = get_session()
    try:
        total = session.query(ExamPaper).count()

        papers = (
            session.query(ExamPaper, PaperMetadata)
            .outerjoin(PaperMetadata, ExamPaper.paper_id == PaperMetadata.paper_id)
            .order_by(desc(ExamPaper.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "total": total,
            "papers": [
                {
                    "paper_id": p.paper_id,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "pdf_path": p.pdf_path,
                    "subject_code": m.subject_code if m else None,
                    "subject_name": m.subject_name if m else None,
                    "department": m.department if m else None,
                    "semester": m.semester if m else None,
                    "academic_year": m.academic_year if m else None,
                    "exam_type": m.exam_type if m else None,
                }
                for p, m in papers
            ],
        }
    finally:
        session.close()


@app.delete("/api/paper/{paper_id}")
def delete_paper(paper_id: str):
    """Delete a paper and all its data."""
    session = get_session()
    try:
        paper = session.query(ExamPaper).filter_by(paper_id=paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Delete in order: subparts -> questions -> metadata -> paper
        session.query(Subpart).filter_by(paper_id=paper_id).delete()
        session.query(Question).filter_by(paper_id=paper_id).delete()
        session.query(PaperMetadata).filter_by(paper_id=paper_id).delete()
        session.query(ExamPaper).filter_by(paper_id=paper_id).delete()
        session.commit()

        return {"status": "deleted", "paper_id": paper_id}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
