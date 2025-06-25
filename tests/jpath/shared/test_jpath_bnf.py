# test_jpath_bnf.py
"""Test the symbol building metods in jpath_bnf.py"""

import re
from typing import Pattern

import pytest

from killerbunny.shared.jpath_bnf import (pattern_str, concat, alternatives, \
                                          plus_rep, star_rep, n_rep, min_max_rep, optional)

# Test data for pattern_str
pattern_str_tests = [
    ('foo', 'foo', "Simple string should remain unchanged"),
    (re.compile(r'\d+'), r'\d+', "Pattern object should return its pattern string"),
    (re.compile(r'[a-z]+'), r'[a-z]+', "Pattern object with character class should return its pattern string")
]

@pytest.mark.parametrize("input_pattern, expected_pattern, msg", pattern_str_tests)
def test_pattern_str(input_pattern: str | Pattern[str], expected_pattern: str, msg: str) -> None:
    """Test that pattern_str() correctly extracts pattern string from both string and Pattern inputs."""
    actual = pattern_str(input_pattern)
    assert actual == expected_pattern, msg

# Test data for concat
concat_tests = [
    ( ['foo', 'bar'],  '(?:(?:foo)(?:bar))', "Simple strings should be concatenated with non-capturing groups"  ),
    ( [r'\d+', r'[a-z]+'], r'(?:(?:\d+)(?:[a-z]+))', "Patterns with special regex chars should be properly grouped" ),
    ( [re.compile('xyz'), 'abc'], '(?:(?:xyz)(?:abc))',  "Mix of Pattern objects and strings should work" )
]
@pytest.mark.parametrize("input_patterns, expected_pattern, msg", concat_tests)
def test_concat(input_patterns: list[str | Pattern[str]], expected_pattern: str, msg: str) -> None:
    """Test that concat() correctly joins patterns with non-capturing groups."""
    actual: str = concat(input_patterns)
    assert actual == expected_pattern, msg

# Test data for alternatives
alternatives_tests = [
    ( ['foo', 'bar'], '(?:(?:foo)|(?:bar))', "Simple strings should be joined with alternation" ),
    ( [r'\d+', r'[a-z]+'], r'(?:(?:\d+)|(?:[a-z]+))', "Patterns with special regex chars should be preserved"),
    ( [re.compile('xyz'), re.compile('abc')], '(?:(?:xyz)|(?:abc))', "Pattern objects should use their string representations" )
]
@pytest.mark.parametrize("input_patterns, expected_pattern, msg", alternatives_tests)
def test_alternatives(input_patterns: list[str | Pattern[str]], expected_pattern: str, msg: str) -> None:
    """Test that alternatives() correctly joins patterns with alternation."""
    actual: str = alternatives(input_patterns)
    assert actual == expected_pattern, msg

# Test data for plus_rep
plus_rep_tests = [
    ('foo', '(?:foo)+', "Simple string pattern should be wrapped in one-or-more syntax"),
    (r'\d+', r'(?:\d+)+', "Pattern with special regex chars should preserve escaping"),
    ('a|b', '(?:a|b)+', "Pattern with alternation should preserve alternation operator"),
    (re.compile('xyz'), '(?:xyz)+', "Pattern object input should use pattern's string representation")
]

@pytest.mark.parametrize("input_pattern, expected_pattern, msg", plus_rep_tests)
def test_plus_rep(input_pattern: str | Pattern[str], expected_pattern: str, msg: str) -> None:
    """Test that plus_rep() correctly wraps patterns in the one-or-more regex syntax."""
    actual: Pattern[str] = plus_rep(input_pattern)
    assert actual.pattern == expected_pattern, msg

# Test data for star_rep
star_rep_tests = [
    ('foo', '(?:foo)*', "Simple string pattern should be wrapped in zero-or-more syntax"),
    (r'\d+', r'(?:\d+)*', "Pattern with special regex chars should preserve escaping"),
    ('a|b', '(?:a|b)*', "Pattern with alternation should preserve alternation operator"),
    (re.compile('xyz'), '(?:xyz)*', "Pattern object input should use pattern's string representation")
]

@pytest.mark.parametrize("input_pattern, expected_pattern, msg", star_rep_tests)
def test_star_rep(input_pattern: str | Pattern[str], expected_pattern: str, msg: str) -> None:
    """Test that star_rep() correctly wraps patterns in the zero-or-more regex syntax."""
    actual: str = star_rep(input_pattern)
    assert actual == expected_pattern, msg

# Test data for n_rep
n_rep_tests = [
    (('foo', 2), '(?:foo){2}', "Simple string pattern should repeat exact number of times"),
    ((r'\d+', 3), r'(?:\d+){3}', "Pattern with special regex chars should preserve escaping"),
    (('a|b', 4), '(?:a|b){4}', "Pattern with alternation should preserve alternation operator"),
    ((re.compile('xyz'), 2), '(?:xyz){2}', "Pattern object input should use pattern's string representation")
]

@pytest.mark.parametrize("input_tuple, expected_pattern, msg", n_rep_tests)
def test_n_rep(input_tuple: tuple[str | Pattern[str], int], expected_pattern: str, msg: str) -> None:
    """Test that n_rep() correctly wraps patterns with the exact repetition count."""
    pattern, n = input_tuple
    actual: Pattern[str] = n_rep(n, pattern)
    assert actual.pattern == expected_pattern, msg

# Test data for min_max_rep
min_max_rep_tests = [
    (('foo', 2, 3), '(?:foo){2,3}', "Simple string pattern should repeat within range"),
    ((r'\d+', 1, 4), r'(?:\d+){1,4}', "Pattern with special regex chars should preserve escaping"),
    (('a|b', 0, 2), '(?:a|b){0,2}', "Pattern with alternation should preserve alternation operator"),
    ((re.compile('xyz'), 1, 3), '(?:xyz){1,3}', "Pattern object input should use pattern's string representation")
]

@pytest.mark.parametrize("input_tuple, expected_pattern, msg", min_max_rep_tests)
def test_min_max_rep(input_tuple: tuple[str | Pattern[str], int, int], expected_pattern: str, msg: str) -> None:
    """Test that min_max_rep() correctly wraps patterns with min/max repetition range."""
    pattern, min_val, max_val = input_tuple
    actual: Pattern[str] = min_max_rep(min_val, max_val, pattern)
    assert actual.pattern == expected_pattern, msg


# Parametrized test data for the optional function.
optional_tests = [
    ('foo', '(?:foo)?', "Simple string pattern should be wrapped in optional syntax"),
    (r'\d+', r'(?:\d+)?', "Pattern with special regex chars should preserve escaping"),
    ('a|b', '(?:a|b)?', "Pattern with alternation should preserve alternation operator"),
    (re.compile('xyz'), '(?:xyz)?', "Pattern object input should use pattern's string representation"),
]
@pytest.mark.parametrize("input_pattern, expected_pattern, msg", optional_tests)
def test_optional(input_pattern: str | Pattern[str], expected_pattern: str, msg: str) -> None:
    """Test that optional() correctly wraps patterns in the optional regex syntax."""
    actual: Pattern[str] = optional(input_pattern)
    assert actual.pattern == expected_pattern, msg

