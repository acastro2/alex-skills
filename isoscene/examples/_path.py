"""Puts the repository root on sys.path, so the examples run from a checkout without installing."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
