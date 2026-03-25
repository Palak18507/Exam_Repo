import re
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import EXTRACTED_TEXT_DIR, CLEANED_JSON_DIR


SEMESTER_MAP = {
    "first": 1, "second": 2, "third": 3, "fourth": 4,
    "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
    "i": 1, "ii": 2, "iii": 3, "iv": 4,
    "v": 5, "vi": 6, "vii": 7, "viii": 8,
}


def _clean(value):
    """Strip whitespace, trailing commas, parentheses, and normalize spaces."""
    value = value.strip()
    value = re.sub(r'[,)\(]+$', '', value)
    value = re.sub(r'^[,)\(]+', '', value)
    value = re.sub(r'\s+', ' ', value)
    return value.strip()


def safe_eval_marks(expr):
    """Safely evaluate marks expressions like '5*4=20', '2x3', '5+5' without eval()."""
    expr = re.sub(r'\s+', '', expr.lower().replace('x', '*'))

    if '=' in expr:
        try:
            return float(expr.split('=')[-1])
        except (ValueError, IndexError):
            return None

    try:
        if '*' in expr:
            a, b = expr.split('*', 1)
            return float(a) * float(b)
        elif '+' in expr:
            return sum(float(x) for x in expr.split('+'))
        elif expr.replace('.', '').isdigit():
            return float(expr)
    except (ValueError, TypeError):
        pass

    return None


def parse_metadata(text):
    """Extract paper metadata from raw text."""
    metadata = {}

    # Subject code: handles "AMC-101", "AMC 102", "AMC  208" (multiple spaces/dashes)
    code_match = re.search(r'Subject\s*Code\s*:\s*([A-Z]{3})[\s\-]*(\d{3})', text, re.IGNORECASE)
    if code_match:
        metadata["subject_code"] = code_match.group(1).upper() + code_match.group(2)

    # Subject name: capture until end of line, then clean
    name_match = re.search(r'Subject\s*:\s*(.+)', text, re.IGNORECASE)
    if name_match:
        metadata["subject_name"] = _clean(name_match.group(1))

    # Program: handles "(Course Name: BBA) (Semester..." and "Course Name: MBA, Semester..."
    program_match = re.search(r'Course\s*Name\s*:\s*(.+?)[\),]\s*(?:\(?\s*Semester)', text, re.IGNORECASE)
    if program_match:
        metadata["program"] = _clean(program_match.group(1))

    # Semester: handles digits (2), roman numerals (II), words (Third)
    sem_match = re.search(r'Semester\s*:\s*([^\)\n]+)', text, re.IGNORECASE)
    if sem_match:
        raw_sem = sem_match.group(1).strip().rstrip(')')
        raw_sem_lower = raw_sem.lower().strip()
        if raw_sem.isdigit():
            metadata["semester"] = int(raw_sem)
        elif raw_sem_lower in SEMESTER_MAP:
            metadata["semester"] = SEMESTER_MAP[raw_sem_lower]

    # Academic year: first 4-digit year found
    year_match = re.search(r'(20\d{2})', text)
    if year_match:
        metadata["academic_year"] = (
            year_match.group(1) + "-" + str(int(year_match.group(1)) + 1)
        )

    # Exam type: "Mid-Term", "End-Term", or "Supplementary"
    exam_match = re.search(r'(Mid|End)\s*-?\s*Term\s+Examination', text, re.IGNORECASE)
    if exam_match:
        kind = exam_match.group(1).capitalize()
        metadata["exam_type"] = kind + "Sem"
        metadata["exam_name"] = kind + "-Term Examination"
    elif re.search(r'Supplementary\s+Examination', text, re.IGNORECASE):
        metadata["exam_type"] = "Supplementary"
        metadata["exam_name"] = "Supplementary Examination"

    # Exam mode
    mode_match = re.search(r'((?:Off|On)\s*-?\s*Line)', text, re.IGNORECASE)
    if mode_match:
        raw_mode = mode_match.group(1).strip()
        metadata["exam_mode"] = re.sub(r'\s+', '', raw_mode).capitalize()

    # Time duration: handles "3 Hours", "1 ½Hours", "1.5 Hours", "1½ Hours"
    time_match = re.search(r'Time\s*:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    if time_match:
        metadata["time_duration"] = _clean(time_match.group(1))

    # Max marks
    marks_match = re.search(r'Maximum\s+Marks\s*:\s*(\d{1,3})', text, re.IGNORECASE)
    if marks_match:
        metadata["max_marks"] = int(marks_match.group(1))

    return metadata, year_match


def build_paper_id(metadata, year_match):
    """Generate a unique paper_id from metadata."""
    if "subject_code" not in metadata or not year_match:
        return None
    return (
        metadata["subject_code"]
        + "_"
        + str(int(year_match.group(1)) + 1)
        + "_"
        + metadata.get("exam_type", "UNKNOWN").upper()
    )


def split_by_units(text):
    units = {None: []}
    current_unit = None

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        upper = line.upper()
        if upper.startswith("UNIT"):
            parts = upper.split()
            if len(parts) >= 2:
                current_unit = f"UNIT {parts[1]}"
                units.setdefault(current_unit, [])
            continue

        units.setdefault(current_unit, []).append(line)

    return units


def split_questions_in_units(units):
    questions = []

    for unit, lines in units.items():
        current_qid = None
        buffer = []

        for line in lines:
            if line.startswith("Q") and len(line) > 1 and line[1].isdigit():
                if current_qid:
                    questions.append({
                        "question_id": current_qid,
                        "unit": unit,
                        "raw_text": " ".join(buffer).strip()
                    })

                parts = line.split(maxsplit=1)
                current_qid = parts[0]
                buffer = [parts[1]] if len(parts) > 1 else []

            elif current_qid:
                buffer.append(line)

        if current_qid:
            questions.append({
                "question_id": current_qid,
                "unit": unit,
                "raw_text": " ".join(buffer).strip()
            })

    return questions


def parse_question_details(question):
    raw = question["raw_text"]
    marks = None

    for m in re.findall(r'\(([^)]*)\)', raw):
        result = safe_eval_marks(m)
        if result is not None:
            marks = result
            break

    subparts = []
    has_subparts = re.search(r'(^|\s)([a-h])\)', raw)

    if has_subparts:
        subs = list(re.finditer(r'(^|\s)([a-h])\)\s*(.*?)(?=(\s[a-h]\)|$))', raw, re.S))
        per = marks / len(subs) if marks else None

        for sp in subs:
            clean = re.sub(r'\([^)]*\)|CO\d+', '', sp.group(3))
            clean = re.sub(r'\s+', ' ', clean).strip()
            subparts.append({
                "subpart_id": sp.group(2),
                "text": clean,
                "marks": per
            })

        question_text = "Attempt all parts."
    else:
        clean = re.sub(r'\([^)]*\)|CO\d+', '', raw)
        question_text = re.sub(r'\s+', ' ', clean).strip()

    return {
        "question_id": question["question_id"],
        "unit": question["unit"],
        "question_text": question_text,
        "marks": marks,
        "subparts": subparts
    }


def process_text_file(txt_path, output_dir=None):
    """Convert a single .txt file to structured JSON. Returns (json_path, paper_metadata, paper_id) or None."""
    txt_path = Path(txt_path)
    output_dir = Path(output_dir) if output_dir else CLEANED_JSON_DIR

    text = txt_path.read_text(encoding="utf-8")

    metadata, year_match = parse_metadata(text)
    paper_id = build_paper_id(metadata, year_match)

    if not paper_id:
        print(f"  [clean] Skipping {txt_path.name} (missing critical metadata)")
        return None

    units = split_by_units(text)
    raw_questions = split_questions_in_units(units)
    questions = [parse_question_details(q) for q in raw_questions]

    final_dict = {
        "paper_id": paper_id,
        "paper_metadata": metadata,
        "questions": questions
    }

    output_path = output_dir / f"{paper_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_dict, f, indent=2, ensure_ascii=False)

    print(f"  [clean] {txt_path.name} -> {paper_id}.json")

    return output_path, metadata, paper_id


def process_folder(input_dir=None):
    """Process all .txt files in a folder. Returns list of (json_path, metadata, paper_id)."""
    folder = Path(input_dir) if input_dir else EXTRACTED_TEXT_DIR
    results = []

    for txt_file in sorted(folder.glob("*.txt")):
        result = process_text_file(txt_file)
        if result:
            results.append(result)

    return results


if __name__ == "__main__":
    process_folder()
