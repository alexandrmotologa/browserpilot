"""Session recording, replay archiving, and structured data export engine."""

import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("browserpilot.server.recorder")

SESSIONS_DIR = Path("sessions")
PROFILES_DIR = Path("profiles")


class SessionArchiveManager:
    """Manages persisting mission traces, replaying previous runs, and structured dataset export."""

    @staticmethod
    def save_session(
        session_id: str,
        goal: str,
        steps: list[dict[str, Any]],
        total_tokens: int,
        total_cost_usd: float,
        final_answer: str | None = None,
        extracted_data: Any = None,
    ) -> Path:
        """Serialize complete mission execution trace to sessions directory."""
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        archive_path = SESSIONS_DIR / f"{session_id}.json"

        trace = {
            "session_id": session_id,
            "goal": goal,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_steps": len(steps),
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost_usd,
            "final_answer": final_answer,
            "extracted_data": extracted_data,
            "steps": steps,
        }

        archive_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
        logger.info(f"Archived mission session trace to {archive_path}")
        return archive_path

    @staticmethod
    def list_archived_sessions() -> list[dict[str, Any]]:
        """List summary metadata for all previously recorded agent missions."""
        if not SESSIONS_DIR.exists():
            return []

        summaries: list[dict[str, Any]] = []
        for file in sorted(SESSIONS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                summaries.append({
                    "session_id": data.get("session_id", file.stem),
                    "goal": data.get("goal", ""),
                    "created_at": data.get("created_at", ""),
                    "total_steps": data.get("total_steps", 0),
                    "total_cost_usd": data.get("total_cost_usd", 0.0),
                    "has_extracted_data": data.get("extracted_data") is not None,
                })
            except Exception as ex:
                logger.debug(f"Failed to read session file {file}: {ex}")

        return summaries

    @staticmethod
    def get_archived_session(session_id: str) -> dict[str, Any] | None:
        """Load complete session execution trace for playback and analysis."""
        target = SESSIONS_DIR / f"{session_id}.json"
        if not target.exists():
            return None
        return json.loads(target.read_text(encoding="utf-8"))

    @staticmethod
    def export_csv(data: list[dict[str, Any]]) -> str:
        """Convert a list of dictionaries into standard CSV formatted string."""
        if not data:
            return ""

        # Extract headers from keys of the first item (and union with other items)
        fieldnames: list[str] = []
        for item in data:
            for k in item.keys():
                if k not in fieldnames:
                    fieldnames.append(k)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
