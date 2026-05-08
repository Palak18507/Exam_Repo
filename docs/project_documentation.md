# IGDTUW Exam Papers Archive — Project Documentation

## 1. Project Overview

A centralized repository system for past examination question papers at Indira Gandhi Delhi Technical University for Women. Librarians upload exam papers (PDF/DOCX), the system automatically extracts, parses, and indexes them. Students search and access papers through a web interface with smart filtering and semantic search.

---

## 2. Architecture

```
+-------------------+       +------------------+       +------------------+
|                   |       |                  |       |                  |
|  Frontend (HTML)  | ----> |  FastAPI (Python) | ----> |  PostgreSQL (DB) |
|  student.html     |  HTTP |  api/server.py   |  SQL  |  Docker container |
|  librarian.html   |  API  |  auth/routes.py  |       |  Port 5432       |
|  login.html       |       |                  |       +------------------+
|  index.html       |       |                  |
|                   |       |                  |       +------------------+
+-------------------+       |                  | ----> |  ChromaDB        |
                            |                  | Vec.  |  Vector DB       |
                            +------------------+       |  data/chroma_db/ |
                                    |                  +------------------+
                                    |
                                    v
                            +------------------+
                            |  Pipeline        |
                            |  PDF -> Text     |
                            |  Text -> JSON    |
                            |  JSON -> DB      |
                            |  JSON -> Vectors |
                            +------------------+
```

---

## 3. ER Diagram

```
+-----------------------------+
|        exam_papers          |
|-----------------------------|
| PK  paper_id      VARCHAR   |
|     created_at    TIMESTAMP |
|     pdf_path      VARCHAR   |
+-------------+---------------+
              | 1:1
              v
+-----------------------------+
|      paper_metadata         |
|-----------------------------|
| PK  paper_id      VARCHAR   | --FK--> exam_papers.paper_id
|     subject_code  VARCHAR   |
|     subject_name  VARCHAR   |
|     program       VARCHAR   |
|     department    VARCHAR   |
|     semester      INTEGER   |
|     academic_year VARCHAR   |
|     exam_type     VARCHAR   |
|     exam_name     VARCHAR   |
|     time_duration VARCHAR   |
|     max_marks     NUMERIC   |
+-------------+---------------+
              | 1:Many
              v
+-----------------------------+
|        questions            |
|-----------------------------|
| PK  q_id           VARCHAR  |
| FK  paper_id       VARCHAR  | --FK--> exam_papers.paper_id
|     question_id    VARCHAR  |
|     unit           VARCHAR  |
|     question_text  JSON     |
|     marks          NUMERIC  |
|     question_hash  CHAR(64) |
|     question_ai_tags       JSON  |
|     question_ai_confidence JSON  |
|     question_syllabus_topics JSON|
+-------------+---------------+
              | 1:Many
              v
+-----------------------------+
|        subparts             |
|-----------------------------|
| PK  s_id            VARCHAR |
| FK  q_id            VARCHAR | --FK--> questions.q_id
|     paper_id        VARCHAR |
|     subpart_id      VARCHAR |
|     text            JSON    |
|     marks           NUMERIC |
|     subquestion_hash CHAR(64)|
|     subpart_ai_tags        JSON  |
|     subpart_ai_confidence  JSON  |
|     subpart_syllabus_topics JSON |
+-----------------------------+

+-----------------------------+
|          users              |
|-----------------------------|
| PK  id             UUID    |
|     email          VARCHAR  | (unique, @igdtuw.ac.in only)
|     password_hash  VARCHAR  |
|     role           VARCHAR  | (admin/librarian/student)
|     created_at     TIMESTAMP|
+-----------------------------+
```

### Relationships
- exam_papers --> paper_metadata: 1:1 (every paper has one metadata record)
- exam_papers --> questions: 1:Many (one paper has many questions)
- questions --> subparts: 1:Many (one question can have subparts a, b, c...)

### Indexes
- paper_metadata: (subject_code, semester, academic_year), (department, semester, exam_type)
- questions: question_hash (for duplicate detection)
- subparts: subquestion_hash (for duplicate detection)

---

## 4. Pipeline Workflow

### Input
PDF or DOCX exam paper files (uploaded by librarian or batch processed from folder)

### Step 1: Document to Text (extraction/pdf_to_text.py)
- **Input**: PDF or DOCX file
- **Method**: PyMuPDF extracts text from PDF pages. If text < 200 chars, falls back to Tesseract OCR. For DOCX, uses python-docx to extract paragraphs and table text.
- **Output**: Plain .txt file in data/extracted_text/

### Step 2: Text to JSON (cleaning/text_to_json.py)
- **Input**: Plain text file
- **Method**: Regex patterns extract metadata (subject code, name, program, semester, year, exam type, duration, marks). Question parser splits by UNIT, then by Q1/Q2/etc, detects subparts (a/b/c), extracts marks.
- **Output**: Structured JSON file in data/cleaned_json/
- **Key**: Generates paper_id like "BCS301_2025_ENDSEM"

### Step 3: JSON to PostgreSQL (db/insert.py)
- **Input**: JSON file + metadata dict
- **Method**: SQLAlchemy ORM upserts into 4 tables (exam_papers, paper_metadata, questions, subparts). Computes SHA-256 hash for each question/subpart text.
- **Output**: Records in PostgreSQL database

### Step 4: JSON to ChromaDB Vectors (chroma/builder.py)
- **Input**: JSON questions + metadata
- **Method**: For each question/subpart, builds a rich text string combining subject, unit, marks, question text, AI tags, and syllabus topics. SentenceTransformer (all-MiniLM-L6-v2) encodes this into a 384-dimensional vector. ChromaDB stores the vector with metadata for filtered search.
- **Output**: Vectors in data/chroma_db/

### Step 5: AI Tagging — Optional (ai/tagger.py)
- **Input**: JSON questions
- **Method**: Ollama LLM (Mistral model) generates 3-5 keyword tags, confidence scores, and syllabus topics per question. Uses SHA-256 cache to avoid re-processing identical questions.
- **Output**: Enriched JSON with ai_tags, ai_confidence, syllabus_topics fields

### Pipeline Modes
- `--file paper.pdf` — process one file
- `--folder data/raw_pdfs/` — batch process all files (4 parallel workers)
- `--watch data/raw_pdfs/` — auto-process new files on drop (watchdog)

---

## 5. Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | HTML/CSS/JS | Student and librarian UI |
| Backend | FastAPI (Python) | REST API server |
| Database | PostgreSQL 16 (Docker) | Structured data storage |
| Vector DB | ChromaDB | Semantic search embeddings |
| Embedding Model | all-MiniLM-L6-v2 | 384-dim sentence embeddings |
| LLM (optional) | Ollama + Mistral | AI tagging of questions |
| PDF Extraction | PyMuPDF + Tesseract | Text extraction from PDFs |
| DOCX Extraction | python-docx | Text extraction from Word docs |
| ORM | SQLAlchemy | Database operations |
| Auth | JWT + bcrypt | Authentication and authorization |
| File Monitoring | watchdog | Auto-process new uploads |
| Containerization | Docker | PostgreSQL hosting |

---

## 6. API Endpoints

### Authentication
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | /api/auth/signup | Public | Register (igdtuw.ac.in email only) |
| POST | /api/auth/login | Public | Login, returns JWT token |
| GET | /api/auth/me | Authenticated | Get current user info |

### Papers (Student + Librarian)
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | /api/papers | Student+ | Search/filter papers |
| GET | /api/paper/{id} | Student+ | Paper details + metadata |
| GET | /api/paper/{id}/questions | Student+ | All questions for a paper |
| GET | /api/papers/{id}/download | Student+ | Download original PDF |
| GET | /api/filters | Student+ | Dropdown filter values |
| GET | /api/stats | Student+ | Analytics (total papers, subjects, etc.) |
| GET | /api/suggestions | Student+ | Search autocomplete |

### Questions (Student + Librarian)
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | /api/questions/search | Student+ | Keyword search across questions |
| GET | /api/question/{q_id} | Student+ | Single question with subparts |
| GET | /api/questions/repeated | Student+ | Frequently asked (hash-based) |
| GET | /api/repeated/question/{hash} | Student+ | All papers with same question |
| GET | /api/repeated/subpart/{hash} | Student+ | All papers with same subpart |

### Semantic Search (Student + Librarian)
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | /api/semantic/search | Student+ | Vector similarity search |
| GET | /api/semantic/similar/{q_id} | Student+ | Find similar questions |
| GET | /api/semantic/topics | Student+ | Topic clustering for a subject |

### Librarian Only
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | /api/upload | Librarian+ | Upload paper (triggers pipeline) |
| GET | /api/librarian/papers | Librarian+ | Manage papers table |
| DELETE | /api/papers/{id} | Librarian+ | Delete a paper |

---

## 7. Data Statistics

- **Total Papers**: 584
- **Subjects Covered**: 392
- **Departments**: 14 (CSE, ECE, IT, AI&ML, MBA, MCA, MAE, etc.)
- **Questions in DB**: ~3,718
- **Subparts in DB**: ~2,771
- **ChromaDB Vectors**: ~7,472
- **Exam Periods**: End Term 2024, End Term 2025, Mid Term 2025

---

## 8. Environment Variables (.env)

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=exam_papers
DB_USER=postgres
DB_PASSWORD=postgres
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=mistral
API_PORT=8001
JWT_SECRET=your-secret-key-here
```

---

## 9. Startup Commands

1. Start Docker Desktop
2. `docker start exam_db`
3. `cd scripts && python -m uvicorn api.server:app --host 0.0.0.0 --port 8001`

### Pipeline Commands
- Single file: `python run_pipeline.py --file path/to/paper.pdf`
- Batch: `python run_pipeline.py --folder data/raw_pdfs/`
- Watch mode: `python run_pipeline.py --watch data/raw_pdfs/`

---

## 10. Deployment

### University Server
1. Install Docker, Python 3.10+, Nginx
2. Clone repo, create venv, install requirements
3. Start PostgreSQL via Docker
4. Run pipeline to populate DB
5. Start API with gunicorn
6. Serve frontend via Nginx
7. (Optional) Install Ollama for AI tagging

### Configuration for Production
- Update .env with production database credentials
- Set a strong JWT_SECRET
- Update script.js API_BASE to production URL
- Configure Nginx reverse proxy for /api/ routes
