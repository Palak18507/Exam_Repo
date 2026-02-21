# Database Schema – Exam Repository System

## Overview
This document defines the relational database schema for the **AI-enabled Exam Repository System**.

The database is designed to:
- Store exam paper metadata and questions
- Support AI-generated metadata (tags, difficulty, vectors)
- Enable keyword-based and semantic search
- Support librarian approval and role-based access

The database uses **MySQL / MariaDB** and is designed to integrate with a **Laravel-based web application**.

---

## Design Principles

- PDFs are stored on disk; only file paths are stored in the database
- JSON is used as an intermediate pipeline format
- AI metadata is additive and does not overwrite original data
- Relative file paths are used for deployment safety
- Schema supports both Mid-Sem and End-Sem papers

---

## Table: `programs`

Stores academic programs offered by the institution.

| Column Name | Type | Description |
|-----------|------|------------|
| program_id | INT (PK) | Unique program identifier |
| program_code | VARCHAR | Short code (MBA, BMS, MCA) |
| program_name | VARCHAR | Full program name |

---

## Table: `subjects`

Stores subject-level information (mapped from Excel master data).

| Column Name | Type | Description |
|------------|------|------------|
| subject_id | INT (PK) | Unique subject identifier |
| subject_code | VARCHAR | Subject code (e.g., AMC152) |
| subject_name | VARCHAR | Subject name |
| program_id | INT (FK) | References `programs.program_id` |
| semester | INT | Semester number |
| department | VARCHAR | Department name |

---

## Table: `exam_papers`

Stores metadata for each exam paper.

| Column Name | Type | Description |
|-------------|------|------------|
| paper_id | INT (PK) | Unique paper identifier |
| subject_id | INT (FK) | References `subjects.subject_id` |
| academic_year | VARCHAR | Academic year (YYYY–YYYY) |
| exam_type | ENUM | MidSem / EndSem |
| exam_name | VARCHAR | Name of examination |
| time_duration | VARCHAR | Duration of exam |
| max_marks | INT | Maximum marks |
| file_path | VARCHAR | Relative path to PDF |
| is_approved | BOOLEAN | Librarian approval flag |
| created_at | TIMESTAMP | Record creation time |

---

## Table: `questions`

Stores questions and sub-questions from exam papers.

| Column Name | Type | Description |
|---------------------|------|-------------|
| question_id | INT (PK) | Unique question identifier |
| paper_id | INT (FK) | References `exam_papers.paper_id` |
| parent_question_id | INT (FK, NULL) | Self-reference for subparts |
| unit | VARCHAR | UNIT I, UNIT II, etc. |
| question_number | VARCHAR | Q1, Q2(a), etc. |
| question_text | TEXT | Question text |
| marks | FLOAT | Marks allocated |

**Note:**
- If `parent_question_id` is NULL → main question
- If not NULL → sub-question (a, b, c)

---

## Table: `ai_metadata`

Stores AI-generated enrichment for questions.

| Column Name | Type | Description |
|-------------|------|------------|
| ai_id | INT (PK) | Unique AI metadata identifier |
| question_id | INT (FK) | References `questions.question_id` |
| keywords | JSON | AI-generated keywords |
| topics | JSON | Mapped syllabus topics |
| difficulty | VARCHAR | Easy / Medium / Hard |
| vector_id | VARCHAR | Reference to vector database |

---

## Table: `users`

Stores system users for role-based access.

| Column Name | Type | Description |
|-----------|------|------------|
| user_id | INT (PK) | Unique user identifier |
| name | VARCHAR | User name |
| email | VARCHAR | Login email |
| role | ENUM | Librarian / Student |

---

## JSON to Database Mapping Summary

| JSON Component | Database Table |
|---------------|----------------|
| paper_metadata | exam_papers |
| subject details | subjects |
| program | programs |
| questions[] | questions |
| subparts[] | questions (self-reference) |
| AI fields | ai_metadata |

---

## Data Flow Summary

