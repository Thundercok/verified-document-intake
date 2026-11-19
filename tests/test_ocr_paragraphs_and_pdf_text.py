"""Tests for OCR soft-wrap paragraph reconstruction and PDF copied-text cleanup."""

import pytest

from document_intake.ocr_paragraphs import POLICY, apply_line_joins, prepare_ocr_text
from document_intake.pdf_text import clean_copied_text


def test_joins_wrapped_lines_and_hyphenation_inside_a_paragraph() -> None:
    text, joins = clean_copied_text(
        "based on com-\nplex recurrent\nnetworks.\n\nNext paragraph."
    )
    assert text == "based on complex recurrent networks.\n\nNext paragraph."
    assert joins == 2


def test_ligatures_soft_hyphens_and_list_items() -> None:
    text, joins = clean_copied_text("signiﬁcantly e\u00adffective\n1. first item\n2. second item")
    assert text == "significantly effective\n1. first item\n2. second item"
    assert joins == 0


def test_capitalised_continuation_keeps_its_hyphen() -> None:
    assert clean_copied_text("state-of-the-\nArt models")[0] == "state-of-the- Art models"


def test_prepare_ocr_text_joins_aligned_prose_and_preserves_lists() -> None:
    tokens = [
        {"text": "Ủy ban nhân dân xã xác nhận", "bbox": [10, 10, 200, 30]},
        {"text": "thông tin cư trú hợp lệ.", "bbox": [12, 34, 210, 54]},
        {"text": "1. Mục thứ nhất", "bbox": [10, 62, 180, 82]},
    ]
    text, raw, meta = prepare_ocr_text(tokens)
    assert meta["policy"] == POLICY
    assert meta["joined_line_indexes"] == [0]
    assert "Ủy ban nhân dân xã xác nhận thông tin cư trú hợp lệ." in text
    assert "\n1. Mục thứ nhất" in text
    assert raw.count("\n") == 2


def test_apply_line_joins_rejects_out_of_bounds_index() -> None:
    with pytest.raises(ValueError, match="ocr_join_invalid"):
        apply_line_joins("only one line", [0])
