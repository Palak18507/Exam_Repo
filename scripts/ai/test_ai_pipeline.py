import json
from tagger import enrich_exam_json

print("\n>>> TEST FILE LOADED <<<\n")


def test_end_to_end_pipeline():
    print(">>> TEST FUNCTION STARTED <<<")

    # ---------- Load input ----------
    print(">>> Opening input_paper.json <<<")
    with open("input_paper.json") as f:
        raw = json.load(f)

    print(">>> input_paper.json loaded successfully <<<")
    print(f">>> Number of questions in input: {len(raw.get('questions', []))} <<<")

    # ---------- Call enrichment ----------
    print("\n>>> CALLING enrich_exam_json <<<")
    enriched = enrich_exam_json(raw)
    print(">>> enrich_exam_json RETURNED <<<\n")

    # ---------- Structural assertions ----------
    print(">>> Running structural assertions <<<")
    assert "questions" in enriched
    assert len(enriched["questions"]) > 0

    q = enriched["questions"][0]

    # ---------- Question-level AI fields ----------
    print(">>> Checking question-level AI fields <<<")
    assert "question_hash" in q
    assert "ai_tags" in q
    assert "ai_confidence" in q
    assert "syllabus_topics" in q

    # ---------- Subpart-level AI fields ----------
    if q.get("subparts"):
        print(">>> Checking subpart-level AI fields <<<")
        sp = q["subparts"][0]
        assert "subquestion_hash" in sp
        assert "ai_tags" in sp
        assert "ai_confidence" in sp
        assert "syllabus_topics" in sp
    else:
        print(">>> No subparts found, skipping subpart checks <<<")

    print("\n✅ End-to-end AI enrichment test passed\n")
