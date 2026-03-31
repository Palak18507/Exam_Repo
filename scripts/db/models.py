from sqlalchemy import Column, String, Integer, Numeric, Index, DateTime, JSON, ForeignKey, func
from db.database import Base


class ExamPaper(Base):
    __tablename__ = "exam_papers"

    paper_id = Column(String, primary_key=True)
    created_at = Column(DateTime, server_default=func.now())
    pdf_path = Column(String, nullable=False)


class PaperMetadata(Base):
    __tablename__ = "paper_metadata"

    paper_id = Column(String, ForeignKey("exam_papers.paper_id", ondelete="CASCADE"), primary_key=True)
    subject_code = Column(String, nullable=False, index=True)
    subject_name = Column(String, nullable=False)
    program = Column(String, nullable=False)
    department = Column(String, nullable=True, index=True)
    semester = Column(Integer, nullable=False)
    academic_year = Column(String, nullable=False, index=True)
    exam_type = Column(String, nullable=False, index=True)
    exam_name = Column(String, nullable=True)
    time_duration = Column(String, nullable=False)
    max_marks = Column(Numeric, nullable=False)

    __table_args__ = (
        Index("ix_meta_subj_sem_year", "subject_code", "semester", "academic_year"),
        Index("ix_meta_dept_sem_exam", "department", "semester", "exam_type"),
    )

    def __repr__(self):
        return f"<PaperMetadata {self.paper_id}: {self.subject_name}>"


class Question(Base):
    __tablename__ = "questions"

    q_id = Column(String, primary_key=True)
    paper_id = Column(String, ForeignKey("exam_papers.paper_id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(String, nullable=False)
    unit = Column(String, nullable=True)
    question_text = Column(JSON, nullable=False)
    marks = Column(Numeric, nullable=False)
    question_hash = Column(String(64), nullable=False, index=True)
    question_ai_tags = Column(JSON, nullable=True)
    question_ai_confidence = Column(JSON, nullable=True)
    question_syllabus_topics = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_q_hash", "question_hash"),
    )

    def __repr__(self):
        return f"<Question {self.q_id}>"


class Subpart(Base):
    __tablename__ = "subparts"

    s_id = Column(String, primary_key=True)
    q_id = Column(String, ForeignKey("questions.q_id", ondelete="CASCADE"), nullable=False, index=True)
    paper_id = Column(String, nullable=False, index=True)
    subpart_id = Column(String, nullable=False)
    text = Column(JSON, nullable=False)
    marks = Column(Numeric, nullable=False)
    subquestion_hash = Column(String(64), nullable=True, index=True)
    subpart_ai_tags = Column(JSON, nullable=True)
    subpart_ai_confidence = Column(JSON, nullable=True)
    subpart_syllabus_topics = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<Subpart {self.s_id}>"
