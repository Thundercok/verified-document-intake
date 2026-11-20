"""Synthetic dossiers and OCR-like noise for measuring verifiers as error detectors.

Nothing here is real data: names come from small pools, identifiers are generated to be
structurally valid and are not looked up anywhere.
"""

from .noise import Corruption, corrupt
from .people import Person, make_amount, make_cccd, make_mst, make_person, with_changes

__all__ = ["Corruption", "Person", "corrupt", "make_amount", "make_cccd", "make_mst", "make_person", "with_changes"]
