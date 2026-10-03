"""Per-session keyword index for retrieval arbitration (Spec §3.1, §4.1).

Lowercase -> token boundary on non-alphanumerics -> drop pure-digit tokens,
stopwords, and tokens shorter than 2 -> Snowball/Porter stem. Stored as a
JSON-encoded list on Session.kw_index_json.

The index is populated at ingestion time from each chunk's text and used at
chat time to compute a boolean `retrieval_required` flag for prompt injection.
"""

import json
import re

import snowballstemmer
from sqlalchemy.orm import Session

from db.models import Session as SessionModel

STEMMER = snowballstemmer.stemmer("english")

STOPWORDS = frozenset(
    """
    the and for are but not you all any can had her was one our out his
    has she will with this that have from they their what when where who
    would there been being were than then them these those into which
    such only also some more most than too very does done about over
    before after between under above below while because each both other
    same different something nothing anything every here come came went
    of to in is it on at be as or an do if my up so no we he by am us me
    """.split()
)

# P4.2: admit digit-bearing and 2-char tokens (ipv4, 3nf, ai, ml); pure-digit
# tokens carry no topical signal and are dropped in build_from_text.
_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")
_HAS_LETTER_RE = re.compile(r"[a-z]")


def build_from_text(text: str) -> set[str]:
    if not text:
        return set()
    tokens = [
        t
        for t in _TOKEN_RE.findall(text.lower())
        if _HAS_LETTER_RE.search(t) and t not in STOPWORDS
    ]
    return set(STEMMER.stemWords(tokens))


def merge_into_session(db: Session, session_id: str, new_stems: set[str]) -> None:
    # B-13: FOR UPDATE on the read-union-write; concurrent ingestions for one
    # session otherwise last-write-win with a stale base set. No-op on SQLite.
    # Taken at the END of the ingestion pipeline, so hold time is only the
    # final flush+commit.
    row = db.get(SessionModel, session_id, with_for_update=True)
    if row is None:
        raise ValueError(f"session not found: {session_id}")
    current = set(json.loads(row.kw_index_json or "[]"))
    merged = current | set(new_stems)
    row.kw_index_json = json.dumps(sorted(merged))


def match_required(query: str, kw_index) -> bool:
    if not kw_index:
        return False
    if isinstance(kw_index, list):
        kw_index = set(kw_index)
    return bool(build_from_text(query) & kw_index)
