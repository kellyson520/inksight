import pytest
from core.periodic_table import get_element_of_the_day, get_element_by_number, ELEMENTS_COUNT


def test_periodic_table_has_elements():
    assert ELEMENTS_COUNT >= 50


def test_get_element_by_number():
    h = get_element_by_number(1)
    assert h["symbol"] == "H"
    assert h["name_zh"] == "氢"
    assert h["name_en"] == "Hydrogen"

    fe = get_element_by_number(26)
    assert fe["symbol"] == "Fe"
    assert fe["name_zh"] == "铁"
    assert fe["atomic_number"] == 26


def test_get_element_of_the_day():
    elem = get_element_of_the_day("2026-09-07")
    assert "symbol" in elem
    assert "name_zh" in elem
    assert "name_en" in elem
    assert "atomic_number" in elem
    assert "atomic_mass" in elem
    assert "category" in elem
    assert "summary" in elem
    assert "fun_fact" in elem
