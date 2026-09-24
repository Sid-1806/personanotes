"""Hand-set style values must land in the type the attribute already holds.

Storing the wrong type makes ``StyleProfileSchema`` fail to parse on the next
read, and that parse failure falls back to a *default* profile — so one bad
override could silently erase everything the system had learned. Anything that
can't be coerced is refused instead of written.
"""

import pytest
from fastapi import HTTPException

from app.api.routers.style import _coerce_attribute_value as coerce


def test_numeric_strings_become_floats():
    assert coerce("bullet_frequency", 0.0, "12.5") == 12.5
    assert coerce("bullet_frequency", 0.0, 7) == 7.0


def test_non_numeric_for_a_numeric_feature_is_refused():
    with pytest.raises(HTTPException) as excinfo:
        coerce("bullet_frequency", 0.0, "not-a-number")
    assert excinfo.value.status_code == 400


@pytest.mark.parametrize("given", ["false", "False", "no", "0", "off", ""])
def test_falsy_strings_are_false_not_true(given):
    # bool("false") is True in Python -- coercing naively would store the
    # opposite of what the user asked for.
    assert coerce("keyword_highlighting", False, given) is False


@pytest.mark.parametrize("given", ["true", "Yes", "1", "on", True])
def test_truthy_strings_are_true(given):
    assert coerce("keyword_highlighting", False, given) is True


def test_nonsense_boolean_is_refused():
    with pytest.raises(HTTPException) as excinfo:
        coerce("keyword_highlighting", False, "maybe")
    assert excinfo.value.status_code == 400


def test_comma_separated_string_becomes_a_list():
    assert coerce("preferred_sections", [], "Intro, Body , Summary") == [
        "Intro",
        "Body",
        "Summary",
    ]


def test_list_input_is_cleaned_not_rejected():
    assert coerce("preferred_sections", [], ["A", "  B  ", ""]) == ["A", "B"]


def test_dict_feature_rejects_a_scalar_instead_of_raising_500():
    # This used to escape as an unhandled 500.
    with pytest.raises(HTTPException) as excinfo:
        coerce("formatting_preferences", {}, "not-a-dict")
    assert excinfo.value.status_code == 400


def test_dict_feature_accepts_an_object():
    assert coerce("formatting_preferences", {}, {"bold_terms": True}) == {"bold_terms": True}


def test_string_feature_accepts_anything_stringable():
    assert coerce("tone", "Academic", "Conversational") == "Conversational"
