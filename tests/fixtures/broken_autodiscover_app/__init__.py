"""Fixture package with a broken parent import."""

from importlib import import_module

import_module("tests.fixtures.missing_dependency")
