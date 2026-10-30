"""Tests for session recording, archive serialization, and CSV/JSON data export."""

from pathlib import Path
from browserpilot.server.session_recorder import SessionArchiveManager


def test_session_archive_and_csv_export(tmp_path: Path) -> None:
    """Verify session trace persistence and CSV formatting."""
    extracted_records = [
        {"id": 1, "product": "Mechanical Keyboard", "price": "$129.99"},
        {"id": 2, "product": "Ergonomic Mouse", "price": "$79.50"},
    ]

    # Test CSV export helper
    csv_output = SessionArchiveManager.export_csv(extracted_records)
    assert "product,price" in csv_output or "id,product,price" in csv_output
    assert "Mechanical Keyboard" in csv_output
    assert "$79.50" in csv_output

    # Test session archiving
    test_session_id = "sess_unit_test_99"
    saved_file = SessionArchiveManager.save_session(
        session_id=test_session_id,
        goal="Extract product prices",
        steps=[{"step_number": 1, "thought": "Extract products", "action": {"action": "extract_data"}}],
        total_tokens=250,
        total_cost_usd=0.0005,
        final_answer="Extracted 2 items",
        extracted_data=extracted_records,
    )

    assert saved_file.exists()

    # Test retrieval
    loaded = SessionArchiveManager.get_archived_session(test_session_id)
    assert loaded is not None
    assert loaded["session_id"] == test_session_id
    assert loaded["total_steps"] == 1
    assert len(loaded["extracted_data"]) == 2

    # Clean up test session file
    if saved_file.exists():
        saved_file.unlink()
