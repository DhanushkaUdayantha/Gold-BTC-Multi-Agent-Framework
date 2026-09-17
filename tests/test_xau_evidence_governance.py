"""
Unit tests for XAU Forward Accumulation Tracker & Evidence Governance.
Verifies:
- N < 50 enforces INSUFFICIENT_EVIDENCE
- 50 <= N < 100 transitions to PROVISIONAL_RESEARCH
- N >= 100 allows QUALIFIED
- Backwards compatible API properties
"""
import pytest
import sqlite3
from src.research.governance.forward_accumulation_tracker import XAUForwardAccumulationTracker

@pytest.fixture
def isolated_db(tmp_path):
    db_file = str(tmp_path / "test_tracker.db")
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            CREATE TABLE forward_shadow_signals (
                signal_id TEXT PRIMARY KEY,
                asset TEXT NOT NULL,
                status TEXT NOT NULL,
                realized_r REAL
            )
        """)
    return db_file

def test_xau_tracker_insufficient_evidence_when_under_50(isolated_db):
    """When resolved N < 50, status MUST be INSUFFICIENT_EVIDENCE."""
    with sqlite3.connect(isolated_db) as conn:
        for i in range(45):
            conn.execute(
                "INSERT INTO forward_shadow_signals VALUES (?, 'XAU/USD', 'RESOLVED_WIN', 1.0)",
                (f"XAU-{i}",)
            )
        conn.commit()

    tracker = XAUForwardAccumulationTracker(db_path=isolated_db)
    progress = tracker.get_progress()

    assert progress.resolved_count == 45
    assert progress.governance_status == "INSUFFICIENT_EVIDENCE"
    assert progress.deficit_to_milestone_1 == 5
    assert progress.deficit_to_milestone_2 == 55
    assert tracker.is_fully_qualified is False

def test_xau_tracker_provisional_research_when_50_to_99(isolated_db):
    """When 50 <= N < 100, status transitions to PROVISIONAL_RESEARCH."""
    with sqlite3.connect(isolated_db) as conn:
        for i in range(75):
            conn.execute(
                "INSERT INTO forward_shadow_signals VALUES (?, 'XAU/USD', 'RESOLVED_WIN', 1.0)",
                (f"XAU-{i}",)
            )
        conn.commit()

    tracker = XAUForwardAccumulationTracker(db_path=isolated_db)
    progress = tracker.get_progress()

    assert progress.resolved_count == 75
    assert progress.governance_status == "PROVISIONAL_RESEARCH"
    assert progress.deficit_to_milestone_1 == 0
    assert progress.deficit_to_milestone_2 == 25
    assert tracker.is_fully_qualified is False

def test_xau_tracker_qualified_when_100_or_more(isolated_db):
    """When N >= 100, status becomes QUALIFIED."""
    with sqlite3.connect(isolated_db) as conn:
        for i in range(105):
            conn.execute(
                "INSERT INTO forward_shadow_signals VALUES (?, 'XAU/USD', 'RESOLVED_WIN', 1.0)",
                (f"XAU-{i}",)
            )
        conn.commit()

    tracker = XAUForwardAccumulationTracker(db_path=isolated_db)
    progress = tracker.get_progress()

    assert progress.resolved_count == 105
    assert progress.governance_status == "QUALIFIED"
    assert progress.deficit_to_milestone_1 == 0
    assert progress.deficit_to_milestone_2 == 0
    assert tracker.is_fully_qualified is True
