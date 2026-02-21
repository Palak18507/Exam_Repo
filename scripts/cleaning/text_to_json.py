import re
import json
import os

INPUT_DIR = "../../data/extracted_text"
OUTPUT_DIR = "../../data/cleaned_json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

for filename in os.listdir(INPUT_DIR):
    if not filename.lower().endswith(".txt"):
        continue

    input_path = os.path.join(INPUT_DIR, filename)

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    # ---------------- PAPER METADATA ----------------
    paper_metadata = {}

    code_match = re.search(r'Subject Code: ([A-Z]{3})\-?\s?(\d{3})', text, re.IGNORECASE)
    if code_match:
        paper_metadata["subject_code"] = code_match.group(1) + code_match.group(2)

    name_match = re.search(r'Subject: ([a-zA-Z- ]+)[\n]', text, re.IGNORECASE)
    if name_match:
        paper_metadata["subject_name"] = name_match.group(1)

    program_match = re.search(r'Course Name\s?:\s?(.+)\,?\s*Semester', text, re.IGNORECASE)
    if program_match:
        paper_metadata["program"] = program_match.group(1)

    sem_match = re.search(r'Semester\s?:\s?<?(\d)>?', text, re.IGNORECASE)
    if sem_match:
        paper_metadata["semester"] = int(sem_match.group(1))

    year_match = re.search(r'(20\d{2})', text)
    if year_match:
        paper_metadata["academic_year"] = (
            year_match.group(1) + "-" + str(int(year_match.group(1)) + 1)
        )

    exam_match = re.search(r'(\w{3})\-Term Examination', text, re.IGNORECASE)
    if exam_match:
        paper_metadata["exam_type"] = exam_match.group(1) + "Sem"
        paper_metadata["exam_name"] = exam_match.group(1) + "-Term Examination"

    mode_match = re.search(r'(O\w+line)', text, re.IGNORECASE)
    if mode_match:
        paper_metadata["exam_mode"] = mode_match.group(1)

    time_match = re.search(r'(\d+ Hours)', text, re.IGNORECASE)
    if time_match:
        paper_metadata["time_duration"] = time_match.group(1)

    marks_match = re.search(r'Maximum Marks\s?:\s?(\d{1,3})', text, re.IGNORECASE)
    if marks_match:
        paper_metadata["max_marks"] = int(marks_match.group(1))

    # ---------------- PAPER ID ----------------
    if "subject_code" not in paper_metadata or not year_match:
        print(f"⚠️ Skipping {filename} (missing critical metadata)")
        continue

    paper_id = (
        paper_metadata["subject_code"]
        + "_"
        + str(int(year_match.group(1)) + 1)
        + "_"
        + paper_metadata["exam_type"].upper()
    )

    # ---------------- PARSING FUNCTIONS ----------------
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
            expr = m.replace(" ", "")
            try:
                if '=' in expr:
                    marks = float(expr.split('=')[-1])
                elif '+' in expr or '*' in expr:
                    marks = float(eval(expr))
                elif expr.isdigit():
                    marks = float(expr)
                if marks is not None:
                    break
            except:
                pass

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

    # ---------------- BUILD JSON ----------------
    units = split_by_units(text)
    raw_questions = split_questions_in_units(units)
    questions = [parse_question_details(q) for q in raw_questions]

    final_dict = {
        "paper_id": paper_id,
        "paper_metadata": paper_metadata,
        "questions": questions
    }

    output_path = os.path.join(OUTPUT_DIR, f"{paper_id}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_dict, f, indent=2, ensure_ascii=False)

    print(f"✅ {filename} → {paper_id}.json")
