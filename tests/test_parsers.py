"""Unit tests for the cells that usually corrupt an education workbook."""

from ntedu.common import (
    canonical_jurisdiction,
    clean_school_name,
    normalise_name,
    parse_number,
    parse_percent_points,
    parse_rate,
)


def test_suppressed_tokens_are_null_not_zero():
    for token in ["np", "NP", "..", "-", "–", "n/a", "", None]:
        assert parse_number(token) is None
        assert parse_rate(token) is None


def test_rates_accept_percents_and_proportions():
    assert parse_rate("81.5%") == 0.815
    assert parse_rate(81.5) == 0.815
    assert parse_rate(0.815) == 0.815
    assert parse_rate("np <12") is None
    assert parse_percent_points("45%") == 45


def test_out_of_range_rates_are_rejected():
    assert parse_rate(150) is None
    assert parse_rate(-1) is None


def test_school_name_strips_asterisks_and_counts_them():
    name, markers = clean_school_name("Alekarenge School**")
    assert name == "Alekarenge School"
    assert markers == 2
    assert normalise_name("St Mary's") == "st mary s"


def test_jurisdiction_strips_footnotes():
    assert canonical_jurisdiction("NT (a)") == "NT"
    assert canonical_jurisdiction("Australia") == "Aust"
