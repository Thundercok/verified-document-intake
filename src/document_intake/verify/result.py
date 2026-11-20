"""Common result type for every verifier.

A verifier never says "correct". It says whether two independent statements of the same fact
agree (MATCH), disagree (MISMATCH), or cannot be compared (UNDETERMINED). A selective gate may
auto-accept only on MATCH, should route MISMATCH to a human, and must treat UNDETERMINED as
"no evidence", not as a pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Verdict(StrEnum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True)
class Check:
    verifier: str
    verdict: Verdict
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.verdict is Verdict.MATCH


def match(verifier: str, detail: str = "") -> Check:
    return Check(verifier, Verdict.MATCH, detail)


def mismatch(verifier: str, detail: str = "") -> Check:
    return Check(verifier, Verdict.MISMATCH, detail)


def undetermined(verifier: str, detail: str = "") -> Check:
    return Check(verifier, Verdict.UNDETERMINED, detail)
