from fractions import Fraction

import pytest

from backend.content import questions, validate_all
from backend.fractions_engine import AnswerFormatError, check_answer, correct_answer, parse_answer


def Q(**kw):
    return {"id": "t", "pool": "t", "skill_id": "add_sub_unlike", **kw}


def test_content_loads_and_every_question_has_an_exact_answer():
    counts = validate_all()
    assert counts["questions"] == len(questions()) >= 60
    for q in questions().values():
        assert isinstance(correct_answer(q), Fraction)


@pytest.mark.parametrize("raw,val", [("5/6", Fraction(5, 6)), (" 10 / 12 ", Fraction(5, 6)), ("1 1/2", Fraction(3, 2)),
                                     ("3", Fraction(3)), ("-1/4", Fraction(-1, 4)), ("2/-4", Fraction(-1, 2))])
def test_parse_valid(raw, val):
    assert parse_answer(raw).value == val


@pytest.mark.parametrize("raw", ["", "  ", "abc", "1/0", "0.5", "1//2", "x" * 30, "1 1/0"])
def test_parse_invalid(raw):
    with pytest.raises(AnswerFormatError):
        parse_answer(raw)


def test_correct_and_equivalent_answers():
    q = Q(type="add", a="1/2", b="1/3")
    assert check_answer(q, "5/6").correct
    r = check_answer(q, "10/12")
    assert r.correct and "simplify" in r.notes[0].lower()


def test_incorrect_answers_and_patterns():
    q = Q(type="add", a="1/2", b="1/3")
    r = check_answer(q, "2/5")
    assert r.valid and not r.correct and r.pattern == "ADD_ACROSS" and r.expected == "5/6"
    assert check_answer(q, "2/6").pattern == "NUMERATOR_NOT_SCALED"
    assert check_answer(Q(type="add", a="1/2", b="1/4"), "2/4").pattern == "KEEP_ONE_DENOMINATOR"
    assert check_answer(Q(type="sub", a="3/4", b="1/2"), "2/2").pattern == "SUB_ACROSS"
    assert check_answer(q, "7/9").pattern is None  # wrong, no known pattern


def test_invalid_answer_is_not_graded():
    r = check_answer(Q(type="add", a="1/2", b="1/3"), "five sixths")
    assert not r.valid and r.error


def test_simplify_requires_lowest_terms():
    q = Q(type="simplify", a="6/8")
    assert check_answer(q, "3/4").correct
    r = check_answer(q, "6/8")
    assert not r.correct and r.pattern == "NOT_SIMPLIFIED"


def test_equivalent_lcd_compare():
    eq = Q(type="equivalent", a="1/2", target=8)
    assert check_answer(eq, "4").correct
    assert check_answer(eq, "7").pattern == "EQUIV_ADD_SAME"
    assert not check_answer(eq, "9/2").valid  # needs a whole number
    lcd = Q(type="lcd", a="1/4", b="1/6")
    assert check_answer(lcd, "12").correct
    assert check_answer(lcd, "24").pattern == "COMMON_NOT_LOWEST"
    assert check_answer(lcd, "10").pattern == "ADD_ACROSS"
    cmp_ = Q(type="compare", a="1/3", b="1/8")
    assert check_answer(cmp_, "1/3").correct
    assert check_answer(cmp_, "1/8").pattern == "BIGGER_DENOMINATOR_BIGGER"
    assert not check_answer(cmp_, "1/2").valid
