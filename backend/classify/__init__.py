"""Is this a land record at all, and if so what kind?

This runs *before* any field is extracted. Nothing downstream may invent a khasra number for
a page that is a restaurant bill.
"""
from .land import DOCUMENT_TYPES, classify, detect_scripts

__all__ = ["DOCUMENT_TYPES", "classify", "detect_scripts"]
