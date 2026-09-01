from app.rag.generator import build_follow_up_answer, needs_follow_up


def test_vague_query_requires_clarification():
    assert needs_follow_up("help me") is True
    assert needs_follow_up("my car has a problem") is True


def test_specific_query_does_not_require_clarification():
    assert needs_follow_up("DTC P10301 for a 2022 FF truck") is False
    assert needs_follow_up("engine warning light on, battery drain issue") is False


def test_follow_up_answer_has_questions():
    answer = build_follow_up_answer("my vehicle is not working")
    assert "which vehicle" in answer.lower()
    assert "symptom" in answer.lower() or "issue" in answer.lower()
