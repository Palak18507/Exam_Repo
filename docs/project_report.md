# Design and Implementation of an Exam Paper Management System using DBMS

**Department of Computer Science and Engineering**
**Indira Gandhi Delhi Technical University for Women**
Kashmere Gate, Delhi
Academic Session 2025-2026, B.Tech 4th Semester

**Submitted by:** NEHA BINU (13201012024), PALAK (14001012024)
**Submitted to:** Ms. Tamal Misra

---

## Table of Contents

| Chapter | Content | Page No. |
|---------|---------|----------|
| 1 | Introduction — Background, Problem Statement, Objectives | 04 |
| 2 | Dataset Description — Source, Data Attributes, Data Processing Overview | 05 |
| 3 | Proposed System — Overview, Features | 07 |
| 4 | System Design — ER Diagram, Database Schema, Table Description, Relationships & Constraints | 08 |
| 5 | Workflow of the Project — Input, Extraction, Processing, Storage, Retrieval | 12 |
| 6 | Implementation & Screenshots | 16 |
| 7 | Conclusion | 22 |

---

## 1. INTRODUCTION

### 1.1 Background of Project

In academic institutions, past examination papers are an essential resource for students to prepare effectively for exams. However, these papers are often scattered across different sources such as physical libraries, personal collections, or unorganized digital folders. This lack of centralization makes it difficult for students to access relevant papers efficiently, and even more difficult for them to identify recurring question patterns across years.

With the increasing volume of academic data, there is a need for a structured system that can store, organize, and retrieve exam papers along with the individual questions inside them. A Database Management System (DBMS) provides a reliable solution for handling such structured data by ensuring consistency, reducing redundancy, and enabling fast query processing.

This project implements a centralized exam paper repository for IGDTUW using a PostgreSQL relational database, a FastAPI backend, and a web-based frontend. Uploaded exam papers are automatically parsed and decomposed into their metadata, questions, and subparts, which are stored across normalized tables. In addition to structured SQL search, the system supports duplicate detection through SHA-256 hashing of question text and semantic similarity search using sentence embeddings stored in a ChromaDB vector index.

### 1.2 Problem Statement

The current method of storing and accessing examination papers is inefficient and unorganized. Most institutions rely on physical storage or basic digital storage systems that do not support structured querying or advanced search capabilities. As a result, students and faculty members face several challenges while trying to access relevant exam papers.

Some of the key issues in the existing system include:

- Lack of a centralized repository for storing exam papers
- Difficulty in searching papers based on specific criteria such as subject, semester, department, or academic year
- Redundant storage of the same data in multiple locations
- Absence of structured representation of questions and their subparts
- Inefficient retrieval of information due to lack of indexing and relationships
- Inability to identify questions that repeat across papers or that are conceptually similar
- No access control separating student-facing search from librarian-facing uploads

Without a proper database system and an ingestion pipeline that converts unstructured PDFs into queryable records, managing large amounts of academic content becomes increasingly complex. Therefore, there is a need for a structured, database-driven system that can efficiently store, manage, and retrieve exam papers along with their associated metadata, support fast filtered and semantic querying, minimize redundancy, and enforce role-based access.

### 1.3 Objectives of the Project

The primary objective of this project is to design and implement a database management system that provides a centralized platform for storing, retrieving, and analysing examination papers.

The specific objectives of the project are as follows:

- To design a relational database schema for storing exam papers, metadata, questions, and subparts
- To organize data into multiple normalized tables linked through primary and foreign keys
- To ensure data integrity and consistency using constraints such as NOT NULL, UNIQUE, and FOREIGN KEY
- To reduce data redundancy through normalization and SHA-256 hashing of question text
- To enable efficient retrieval of data through SQL queries, B-tree indexes, and composite indexes on frequently filtered columns
- To provide filtering and search functionality based on attributes such as subject, semester, department, academic year, and exam type
- To support detection of frequently asked and semantically similar questions using content hashing and vector embeddings
- To enforce role-based access control for admin, librarian, and student users through JWT authentication
- To design a system that can be scaled to accommodate large datasets in the future

In addition to these objectives, the project demonstrates the practical application of DBMS concepts such as schema design, normalization, indexing, foreign-key relationships, and query optimization alongside a pipeline that converts unstructured PDF/DOCX input into structured records.

---

## 2. DATASET DESCRIPTION

### 2.1 Source of Dataset

The dataset used in this project consists of past examination papers collected from Indira Gandhi Delhi Technical University for Women (IGDTUW). These papers are available in digital formats such as PDF and DOCX and cover multiple programs, departments, and exam periods (Mid Term and End Term for 2024 and 2025).

The data is either manually uploaded by authorized librarians through the web interface, or batch-processed from a folder using the ingestion pipeline. Each document contains semi-structured information such as subject details, exam information, units, questions, and subparts. The ingestion pipeline is also able to watch a folder and automatically process any new paper dropped into it.

### 2.2 Data Attributes

The dataset is organized into five entities, each containing specific attributes. These attributes are distributed across different tables in the database to ensure proper normalization and efficient data management.

**1. Exam Papers Entity**
Represents the basic record of each uploaded paper.
- `paper_id` — unique identifier, deterministic (e.g. `BCS301_2025_ENDSEM`)
- `created_at` — timestamp of record creation
- `pdf_path` — storage path of the original PDF or DOCX file

**2. Paper Metadata Entity**
Stores descriptive information linked 1:1 to each exam paper.
- `subject_code`, `subject_name`
- `program` (e.g. B.Tech, MCA, MBA)
- `department` (CSE, ECE, IT, AI&ML, MAE, etc.)
- `semester` (integer)
- `academic_year` (e.g. 2024-25)
- `exam_type` (Mid-Term / End-Term)
- `exam_name`
- `time_duration`
- `max_marks`

**3. Questions Entity**
Each individual question extracted from a paper is stored as its own record.
- `q_id` — surrogate primary key
- `paper_id` — foreign key to `exam_papers`
- `question_id` — question number as it appears on the paper (Q1, Q2, …)
- `unit` — unit or topic the question belongs to
- `question_text` — JSON-encoded text of the question
- `marks`
- `question_hash` — SHA-256 hash of the normalized question text, used for duplicate and frequency detection
- `question_ai_tags`, `question_ai_confidence`, `question_syllabus_topics` — optional AI-generated metadata

**4. Subparts Entity**
Stores sub-questions such as (a), (b), (c) of a parent question.
- `s_id` — surrogate primary key
- `q_id` — foreign key to `questions`
- `paper_id` — foreign key to `exam_papers`
- `subpart_id` — label (a, b, c, …)
- `text` — JSON-encoded text of the subpart
- `marks`
- `subquestion_hash` — SHA-256 hash for duplicate detection
- `subpart_ai_tags`, `subpart_ai_confidence`, `subpart_syllabus_topics` — optional AI-generated metadata

**5. Users Entity**
Manages user accounts for authentication and authorization.
- `id` — UUID primary key
- `email` — restricted to the `@igdtuw.ac.in` domain, unique
- `password_hash` — bcrypt hash
- `role` — one of `admin`, `librarian`, `student`
- `created_at`, `last_active`

By dividing the dataset into these entities, the system ensures efficient organization, avoids redundancy, and supports both exact-match and similarity-based retrieval.

### 2.3 Data Processing Overview

The dataset undergoes several processing steps before being stored in the database:

- **Text Extraction** — raw text is extracted from PDF files using PyMuPDF. If the extracted text is shorter than 200 characters (indicating a scanned document), the system falls back to Tesseract OCR. DOCX files are processed with `python-docx`, including table contents.
- **Data Cleaning** — unstructured text is cleaned of extra whitespace and formatting artifacts.
- **Parsing** — regular-expression patterns identify subject code, subject name, program, semester (digit, Roman, or word form), academic year, exam type, duration, and maximum marks. The parser splits text by UNIT, then by question numbers (Q1, Q2, …), and further into subparts (a, b, c).
- **Structuring** — the extracted information is written to a structured JSON document.
- **Hashing** — each question and subpart text is normalized and hashed with SHA-256 to enable exact-match duplicate detection.
- **Database Insertion** — structured records are upserted into PostgreSQL through SQLAlchemy.
- **Vector Indexing** — each question is encoded using the `all-MiniLM-L6-v2` sentence-transformer model into a 384-dimensional embedding and stored in a ChromaDB collection for semantic search.
- **Optional AI Tagging** — if an Ollama LLM is available locally, each question is tagged with 3–5 keywords, a confidence score, and inferred syllabus topics, which are cached by hash.

This pipeline ensures that unstructured exam papers are transformed into a structured, indexed, and semantically searchable form suitable for database storage and querying.

---

## 3. PROPOSED SYSTEM

### 3.1 Overview of the System

The proposed system is a centralized database-driven application designed to store, manage, and retrieve examination papers efficiently. It comprises three main layers: a web-based frontend, a FastAPI backend server, and a PostgreSQL database supported by a ChromaDB vector index.

Authorized librarians can upload individual papers through the interface or drop multiple files into a watched folder for automatic processing. Each upload triggers an ingestion pipeline that extracts text, parses questions, and inserts structured records into the database. Students can log in through a web interface using their institutional email and search for papers using multiple filters such as subject, semester, department, academic year, and exam type. They can also view individual questions, browse frequently repeated questions, and perform semantic similarity searches on question content.

Unlike traditional file-based storage systems, this system organizes data into multiple related tables, enabling efficient querying, minimizing redundancy, and supporting advanced analytical features such as repetition detection and topic clustering.

### 3.2 Features of the System

The key features of the proposed system include:

- Centralized storage of exam papers in a structured PostgreSQL database
- Automated ingestion pipeline for PDF and DOCX documents with OCR fallback
- Single-file, batch, and watch-mode processing using a thread pool
- Efficient search and filtering based on subject, semester, department, academic year, and exam type
- Structured hierarchical storage of questions and subparts
- SHA-256 content hashing for duplicate detection and frequently-asked question analysis
- Semantic similarity search using sentence embeddings stored in ChromaDB
- Optional AI-based tagging and syllabus-topic labelling using a local Ollama LLM
- Role-based access control (admin, librarian, student) with JWT authentication
- Institutional email restriction (`@igdtuw.ac.in`) for signup
- Job-tracking system that reports upload progress in real time
- Composite indexes on frequently queried columns for fast retrieval

These features improve accessibility, maintainability, analytical capability, and performance compared to traditional document-based storage.

---

## 4. SYSTEM DESIGN

### 4.1 ER Diagram

The Entity-Relationship (ER) diagram represents the logical structure of the database and illustrates how the five entities relate to each other.

```
+-------------------+        1:1        +----------------------+
|   exam_papers     |------------------>|   paper_metadata     |
| PK paper_id       |                   | PK/FK paper_id       |
|    created_at     |                   |    subject_code      |
|    pdf_path       |                   |    subject_name      |
+---------+---------+                   |    program           |
          | 1:Many                      |    department        |
          v                             |    semester          |
+-------------------+                   |    academic_year     |
|    questions      |                   |    exam_type         |
| PK q_id           |                   |    exam_name         |
| FK paper_id       |                   |    time_duration     |
|    question_id    |                   |    max_marks         |
|    unit           |                   +----------------------+
|    question_text  |
|    marks          |
|    question_hash  |
|    ai_tags*       |
+---------+---------+
          | 1:Many
          v
+-------------------+
|     subparts      |
| PK s_id           |
| FK q_id           |
|    paper_id       |
|    subpart_id     |
|    text           |
|    marks          |
|    subquestion_hash|
|    ai_tags*       |
+-------------------+

+---------------------+
|        users        |     (independent)
| PK id (UUID)        |
|    email (unique)   |
|    password_hash    |
|    role             |
|    created_at       |
|    last_active      |
+---------------------+
```

**Relationships**
- `exam_papers` → `paper_metadata` — 1:1 (each paper has exactly one metadata record)
- `exam_papers` → `questions` — 1:Many (a paper contains many questions, each belonging to one paper)
- `questions` → `subparts` — 1:Many (a question may have multiple subparts)
- `users` — independent; interacts with the system through authenticated API calls

### 4.2 Database Schema

The schema is implemented in PostgreSQL through SQLAlchemy models. Tables are created automatically at application startup via `Base.metadata.create_all()`.

- **exam_papers** (`paper_id` PK, `created_at`, `pdf_path`)
- **paper_metadata** (`paper_id` PK/FK → exam_papers, `subject_code`, `subject_name`, `program`, `department`, `semester`, `academic_year`, `exam_type`, `exam_name`, `time_duration`, `max_marks`)
- **questions** (`q_id` PK, `paper_id` FK, `question_id`, `unit`, `question_text` JSON, `marks`, `question_hash` CHAR(64), plus optional AI fields)
- **subparts** (`s_id` PK, `q_id` FK, `paper_id`, `subpart_id`, `text` JSON, `marks`, `subquestion_hash` CHAR(64), plus optional AI fields)
- **users** (`id` UUID PK, `email` UNIQUE, `password_hash`, `role`, `created_at`, `last_active`)

### 4.3 Table Description

| Table | Purpose |
|-------|---------|
| `exam_papers` | One row per uploaded paper; stores the file path and creation timestamp |
| `paper_metadata` | Descriptive metadata extracted from the header of the paper |
| `questions` | One row per question parsed from the paper, including its hash for repetition detection |
| `subparts` | One row per labelled subpart of a question (a, b, c, …) |
| `users` | User accounts for authentication; role determines API access |

### 4.4 Relationships & Constraints

- **Primary Keys** on every entity guarantee uniqueness.
- **Foreign Keys** enforce referential integrity:
  - `paper_metadata.paper_id` → `exam_papers.paper_id` (ON DELETE CASCADE)
  - `questions.paper_id` → `exam_papers.paper_id` (ON DELETE CASCADE)
  - `subparts.q_id` → `questions.q_id` (ON DELETE CASCADE)
- **NOT NULL** constraints on required columns such as `email`, `password_hash`, and `role`.
- **UNIQUE** constraint on `users.email` prevents duplicate accounts.
- **Indexes** for performance:
  - `paper_metadata` — composite indexes on (`subject_code`, `semester`, `academic_year`) and (`department`, `semester`, `exam_type`)
  - `questions` — index on `question_hash`
  - `subparts` — index on `subquestion_hash`
  - `users` — index on `email`
- **Content Hashing** — SHA-256 hash of normalized question and subpart text replaces a traditional UNIQUE constraint by allowing the same text to be stored once per paper while still being groupable across papers.

Together, these constraints and indexes preserve data integrity and keep search and repetition queries efficient as the dataset grows.

---

## 5. WORKFLOW OF THE PROJECT

### 5.1 Overview of Workflow

The workflow describes how unstructured exam paper documents are converted into structured, queryable, and semantically searchable records. The system follows a pipeline-based approach in which data flows through several stages: input, text extraction, processing and structuring, database insertion, vector indexing, optional AI tagging, and finally retrieval through the API.

### 5.2 Data Input Stage

Papers enter the system through one of three modes:

- **Manual upload** — a librarian uploads a single file through the frontend. The backend stores the file, creates a job entry, and processes the file in a background thread.
- **Batch processing** — multiple files inside a folder are processed using a thread pool (`ThreadPoolExecutor`, default four workers).
- **Watch mode** — the `watchdog` library monitors a folder and automatically processes any new file dropped into it.

Every job is assigned an ID and progress messages (`0% → 100%`) so the frontend can display live status.

### 5.3 Text Extraction Stage

The extraction module (`scripts/extraction/pdf_to_text.py`) performs the following:

- For **PDF files**, text is extracted page-by-page using **PyMuPDF** (`fitz`).
- If the resulting text is shorter than 200 characters — indicating a scanned or image-based PDF — the system falls back to **Tesseract OCR** via `pytesseract` and `Pillow`.
- For **DOCX files**, `python-docx` reads paragraphs and table cells.

The output is a plain `.txt` file stored under `data/extracted_text/`.

### 5.4 Data Processing and Structuring

The cleaning module (`scripts/cleaning/text_to_json.py`) performs:

- **Data cleaning** — collapsing whitespace and removing formatting artifacts.
- **Metadata extraction** — regex patterns capture subject code (tolerating spaces and dashes), subject name, program, semester (digits, Roman numerals, or words), academic year, exam type, time duration, and maximum marks.
- **Question segmentation** — the parser splits the text by UNIT markers, then by question numbers (Q1, Q2, …).
- **Subpart detection** — nested (a), (b), (c) markers are captured as individual subparts.
- **Paper ID generation** — a deterministic ID of the form `{subject_code}_{year}_{exam_type}` (e.g. `BCS301_2025_ENDSEM`) is assigned.

The result is a structured JSON document in `data/cleaned_json/`.

### 5.5 Database Storage

The insertion module (`scripts/db/insert.py`) uses SQLAlchemy to upsert records into the four content tables. Each question and subpart text is normalized (lower-cased, whitespace collapsed) and hashed with SHA-256 before insertion; the hash is stored in `question_hash` and `subquestion_hash` respectively.

Composite indexes on frequently queried columns accelerate filtered retrieval. Foreign keys with `ON DELETE CASCADE` guarantee that deleting an exam paper cleanly removes its metadata, questions, and subparts.

After database insertion, the vector builder (`scripts/chroma/builder.py`) constructs a rich text string for each question (subject, unit, marks, text, AI tags if present) and encodes it into a 384-dimensional embedding using `all-MiniLM-L6-v2`. Embeddings are stored in a ChromaDB collection at `data/chroma_db/`.

If a local Ollama server is running, the optional AI tagger (`scripts/ai/tagger.py`) enriches each question with 3–5 keyword tags, a confidence score, and inferred syllabus topics. Results are cached by content hash so identical questions are not re-tagged.

### 5.6 Data Retrieval and Search

Retrieval is exposed through the FastAPI service (`scripts/api/server.py`):

- **Filtered search** — `/api/papers`, `/api/filters`, `/api/suggestions` combine free-text search with exact-match filters on subject, semester, department, academic year, and exam type.
- **Question browsing** — `/api/paper/{id}/questions` and `/api/question/{q_id}` return questions and their subparts in hierarchical form.
- **Repetition analysis** — `/api/questions/repeated`, `/api/repeated/question/{hash}`, and `/api/repeated/subpart/{hash}` group questions that share a hash to surface frequently asked items.
- **Semantic search** — `/api/semantic/search`, `/api/semantic/similar/{q_id}`, and `/api/semantic/topics` use the ChromaDB vector index to return conceptually similar questions, even when wording differs.
- **Authentication** — `/api/auth/signup`, `/api/auth/login`, `/api/auth/me` handle JWT-based login. Role-based dependencies (`require_student`, `require_librarian`, `require_admin`) gate downstream endpoints.

Thanks to indexed columns, normalized storage, and the vector store, retrieval remains fast even as the dataset grows.

---

## 6. IMPLEMENTATION AND SCREENSHOTS

### 6.1 Overview of Implementation

The system is implemented as a three-tier application:

- **Frontend** — static HTML/CSS/JS served from `librayrepoUI/`, consisting of four pages: `index.html` (portal), `login.html`, `student.html`, and `librarian.html`. JavaScript (`script.js`) handles tab navigation, form validation, API calls, role-based routing, filtering, and file downloads.
- **Backend** — FastAPI application (`scripts/api/server.py`) exposing REST endpoints, with authentication routes in `scripts/auth/routes.py` and JWT middleware in `scripts/auth/middleware.py`.
- **Database** — PostgreSQL 16 running in Docker (`exam_db` container) on port 5432, with ChromaDB as a secondary vector store at `data/chroma_db/`.

The backend is run with Uvicorn:
```
cd scripts
python -m uvicorn api.server:app --host 0.0.0.0 --port 8001
```

### 6.2 User Interface

The system provides a user-friendly interface with four pages:

- **Login page** (`login.html`) — allows sign-in and signup, with client-side validation that restricts signup emails to `@igdtuw.ac.in`.
- **Portal / Homepage** (`index.html`) — archive overview, quick stats, and navigation.
- **Student dashboard** (`student.html`) — three tabs: *Search*, *Question Bank*, and *Frequently Asked*. Stats cards display total papers, subjects covered, papers added this year, and the current trending subject.
- **Librarian dashboard** (`librarian.html`) — upload form, managed papers table, and a live job-progress tracker for ongoing ingestion tasks.

*[Insert screenshot: Login page]*
*[Insert screenshot: Homepage / Dashboard]*

### 6.3 Search and Filtering Functionality

One of the key features of the system is its ability to search and filter exam papers efficiently. Users can combine free-text search with multiple filters:

- **Free-text search** — matches against subject name, subject code, department, and program.
- **Filters** — subject code, department, semester, exam type, and academic year.
- **Autocomplete** — `/api/suggestions` returns suggestions that start with and contain the current query.

Because filter values are stored in indexed columns, queries are served directly against structured data instead of scanning document text. The system also supports advanced analytical queries:

- *Frequently Asked* — fetched via `/api/questions/repeated`, ranked by hash occurrence count.
- *Related Questions* — fetched via `/api/semantic/similar/{q_id}`, powered by the ChromaDB vector store.
- *Topic clustering* — `/api/semantic/topics` groups questions of a given subject into semantic clusters.

*[Insert screenshot: Search page]*
*[Insert screenshot: Filters applied]*
*[Insert screenshot: Search results]*

### 6.4 Display of Questions and Data

The system provides a structured view of exam content that goes beyond opening raw documents. Instead of scrolling through a PDF to locate a single question, users browse, filter, and group questions directly from the database.

**Hierarchical question view.** Each question is stored as an independent record in the `questions` table and is linked to its parent paper through a foreign key. Its subparts (a, b, c, …) are stored as separate records in the `subparts` table, each linked to its parent question. When a user opens a paper, the interface renders this structure as a nested list — the question text and marks at the top, followed by its subparts indented beneath — preserving the original layout while keeping every unit individually addressable.

**Filtered question bank.** The *Question Bank* tab lets users retrieve questions across multiple papers using the same filters available for paper search: subject code, department, semester, academic year, and exam type. Because questions are normalized into their own table with indexed metadata joins, the filter query runs directly against structured columns instead of scanning document text. Users can, for example, retrieve "all Unit-3 questions from Operating Systems end-term papers" in a single view.

**Frequently asked and related questions.** During ingestion, every question and subpart text is normalized and hashed with SHA-256. Questions that appear in more than one paper produce identical hashes, which allows the system to group them and surface a *Frequently Asked* list ranked by occurrence count. Selecting a repeated question shows every paper in which it has appeared, along with its unit and marks, giving students a direct view of recurring patterns across semesters. In addition, every question is encoded as a 384-dimensional vector stored in ChromaDB, enabling a *Related Questions* lookup that returns semantically similar questions even when the wording differs. This is particularly useful for topic-based preparation, since conceptually identical questions phrased differently are still grouped together.

*[Insert screenshot: Questions view (hierarchical)]*
*[Insert screenshot: Frequently Asked tab]*
*[Insert screenshot: Related / similar questions]*

### 6.5 Database Implementation

The database is implemented using PostgreSQL (running in a Docker container named `exam_db`). Data is stored across five related tables linked by foreign keys. SQLAlchemy ORM performs insertions, queries, and updates, and PostgreSQL-level constraints enforce integrity.

Composite indexes on `(subject_code, semester, academic_year)` and `(department, semester, exam_type)` accelerate filtered searches, while indexes on `question_hash` and `subquestion_hash` make repetition queries efficient. ChromaDB, stored separately at `data/chroma_db/`, holds sentence-embedding vectors for semantic search and is queried alongside PostgreSQL when needed.

The tech stack includes:

| Component | Technology |
|-----------|-----------|
| Frontend | HTML / CSS / JavaScript |
| Backend | FastAPI (Python) |
| ORM | SQLAlchemy |
| Database | PostgreSQL 16 (Docker) |
| Vector DB | ChromaDB |
| Embedding Model | all-MiniLM-L6-v2 (sentence-transformers) |
| PDF Extraction | PyMuPDF + Tesseract OCR fallback |
| DOCX Extraction | python-docx |
| Authentication | JWT (python-jose) + bcrypt |
| File Monitoring | watchdog |
| Optional LLM | Ollama (Mistral model) for AI tagging |

*[Insert screenshot: Database tables in pgAdmin or terminal]*
*[Insert screenshot: Sample SQL query output]*
*[Insert screenshot: ChromaDB semantic search response]*

---

## 7. CONCLUSION

This project successfully demonstrates the design and implementation of a database-driven system for managing and retrieving examination papers. By applying core DBMS concepts — entity-relationship modelling, normalization, foreign-key constraints, and indexing — the system provides a structured and efficient way to handle academic data.

The system transforms unstructured exam-paper documents into organized data stored across five related tables. This approach reduces data redundancy, ensures data integrity, and enables efficient querying. The relationships between exam papers, metadata, questions, and subparts allow the system to represent complex hierarchical content in a logical and manageable form.

Beyond simple storage, the project extends the DBMS with two additional layers: SHA-256 content hashing for detecting repeated and frequently asked questions across papers, and sentence-embedding vectors stored in ChromaDB for semantic similarity search. Together, these turn a flat repository of PDFs into a queryable knowledge base that surfaces recurring patterns and conceptually related questions — not just exact text matches. Role-based access control, enforced through JWT authentication, ensures that student search, librarian uploads, and administrative actions are cleanly separated.

Overall, the project achieves its objective of creating a centralized, indexed, and analysable repository for exam papers using database-management techniques. It demonstrates how proper relational design, combined with content hashing and vector search, can enhance data organization, optimize retrieval performance, and provide a scalable solution for managing large academic datasets.
