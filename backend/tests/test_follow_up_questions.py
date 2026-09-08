from app.rag.faq import FAQ_ITEMS, get_faq_suggestions, match_faq
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


def test_faq_suggestions_are_user_friendly_and_short():
    suggestions = get_faq_suggestions()
    assert suggestions
    assert all(len(item) <= 80 for item in suggestions)
    assert any("map" in item.lower() or "navigation" in item.lower() for item in suggestions)


def test_known_faq_question_returns_simple_answer():
    matched = match_faq("why is my map not working?")
    assert matched is not None
    assert "wifi" in matched["answer"].lower() or "internet" in matched["answer"].lower() or "sync" in matched["answer"].lower()
    assert matched["question"] in FAQ_ITEMS[0]["question"] or matched["question"] in [item["question"] for item in FAQ_ITEMS]


def test_unrelated_question_does_not_receive_an_faq_answer():
    assert match_faq("my app is not syncing") is None
