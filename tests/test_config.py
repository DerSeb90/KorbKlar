import os

from supermarkt import config


def test_env_int_falls_back_on_invalid_value(monkeypatch):
    monkeypatch.setenv("SUPERMARKT_TEST_INT", "kaputt")
    assert config._env_int("SUPERMARKT_TEST_INT", 25, 5, 120) == 25


def test_env_int_applies_bounds(monkeypatch):
    monkeypatch.setenv("SUPERMARKT_TEST_INT", "-10")
    assert config._env_int("SUPERMARKT_TEST_INT", 25, 5, 120) == 5
    monkeypatch.setenv("SUPERMARKT_TEST_INT", "999")
    assert config._env_int("SUPERMARKT_TEST_INT", 25, 5, 120) == 120


def test_env_text_uses_default_for_blank_value(monkeypatch):
    monkeypatch.setenv("SUPERMARKT_TEST_TEXT", "   ")
    assert config._env_text("SUPERMARKT_TEST_TEXT", "fallback") == "fallback"
