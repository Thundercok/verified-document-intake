"""Field verifiers and normalisers for Vietnamese administrative documents.

Every verifier returns a `Check` with verdict MATCH, MISMATCH or UNDETERMINED. Only MATCH may let
a selective gate auto-accept a field. Stdlib only.
"""

from .address import Address, compare_addresses, parse_address, resolve_province
from .dates import PartialDate, compare_dates, parse_date
from .ids import Cccd, check_cccd_consistency, check_cccd_format, compare_identifiers, parse_cccd
from .mst import check_mst, mst_check_digit, parse_mst
from .number_words import check_amount, number_to_words, parse_amount_digits, parse_number_words
from .result import Check, Verdict
from .text import clean, compare_names, fold_diacritics, place_tone, text_key

__all__ = [
    "Address",
    "Cccd",
    "Check",
    "PartialDate",
    "Verdict",
    "check_amount",
    "check_cccd_consistency",
    "check_cccd_format",
    "check_mst",
    "clean",
    "compare_addresses",
    "compare_dates",
    "compare_identifiers",
    "compare_names",
    "fold_diacritics",
    "mst_check_digit",
    "number_to_words",
    "parse_address",
    "parse_amount_digits",
    "parse_cccd",
    "parse_date",
    "parse_mst",
    "parse_number_words",
    "place_tone",
    "resolve_province",
    "text_key",
]
