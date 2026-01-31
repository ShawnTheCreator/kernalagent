import pytest

from app.reasoning.intent_analyzer import IntentAnalyzer


def _make_analyzer() -> IntentAnalyzer:
    return IntentAnalyzer()


def test_parse_response_valid_json():
    analyzer = _make_analyzer()
    response = '{"intent":"single_action","confidence":0.9,"reasoning":"ok","actions":[]}'
    parsed = analyzer._parse_response(response)
    assert parsed is not None
    assert parsed["intent"] == "single_action"


def test_parse_response_code_fence():
    analyzer = _make_analyzer()
    response = """```json
{"intent":"multi_step","confidence":0.8,"reasoning":"ok","actions":[]}
```"""
    parsed = analyzer._parse_response(response)
    assert parsed is not None
    assert parsed["intent"] == "multi_step"


def test_parse_response_with_wrapped_text():
    analyzer = _make_analyzer()
    response = (
        "Here is your plan:\n"
        '{"intent":"single_action","confidence":0.7,"reasoning":"ok","actions":[]}\n'
        "Thanks!"
    )
    parsed = analyzer._parse_response(response)
    assert parsed is not None
    assert parsed["confidence"] == 0.7


def test_parse_response_unterminated_string():
    analyzer = _make_analyzer()
    response = '{"intent":"multi_step","confidence":0.9,"reasoning":"unterminated, "actions":[]}'
    parsed = analyzer._parse_response(response)
    assert parsed is None
