"""Prepare sample session archives with embedded screenshot frames for BrowserPilot."""

import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from browserpilot.server.session_recorder import SessionArchiveManager, SESSIONS_DIR, PROFILES_DIR
from capture_real_assets import render_frame_base64

async def main():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    frame_b64 = await render_frame_base64()

    # 1. Archive 1: Hacker News AI & Autonomous Agents
    SessionArchiveManager.save_session(
        session_id="sess_hacker_news_ai",
        goal="Extract top 10 discussions on autonomous web agents from Hacker News",
        steps=[
            {
                "step_number": 1,
                "url": "https://news.ycombinator.com",
                "title": "Hacker News",
                "thought": "Navigate to Hacker News home and parse DOM accessibility nodes for story rankings.",
                "action": {"action": "goto", "url": "https://news.ycombinator.com"},
                "total_tokens": 420,
                "cost_usd": 0.0011,
                "latency_ms": 280.0,
                "screenshot_base64": frame_b64,
            },
            {
                "step_number": 2,
                "url": "https://news.ycombinator.com",
                "title": "Hacker News",
                "thought": "Locate search input field [5] and submit query for 'browser automation agents'.",
                "action": {"action": "type", "element_id": 5, "text": "browser automation agents", "press_enter": True},
                "total_tokens": 680,
                "cost_usd": 0.0017,
                "latency_ms": 320.0,
                "screenshot_base64": frame_b64,
            },
            {
                "step_number": 3,
                "url": "https://news.ycombinator.com/item?id=4189201",
                "title": "BrowserPilot: Autonomous a11y & stealth web agent | Hacker News",
                "thought": "Extract top search results and vote counts into structured JSON dataset.",
                "action": {
                    "action": "extract_data",
                    "extracted_data": [
                        {"rank": 1, "title": "BrowserPilot: Autonomous a11y & stealth web agent", "points": 342, "comments": 89},
                        {"rank": 2, "title": "Why accessibility trees are 80% cheaper than vision screenshots", "points": 287, "comments": 114},
                        {"rank": 3, "title": "Evading Cloudflare Turnstile and DataDome with Chromium CDP patches", "points": 219, "comments": 67},
                        {"rank": 4, "title": "Cubic Bézier mouse trajectories in Playwright", "points": 174, "comments": 43},
                    ]
                },
                "total_tokens": 1120,
                "cost_usd": 0.0028,
                "latency_ms": 410.0,
                "screenshot_base64": frame_b64,
            },
            {
                "step_number": 4,
                "url": "https://news.ycombinator.com/item?id=4189201",
                "title": "BrowserPilot: Autonomous a11y & stealth web agent | Hacker News",
                "thought": "Goal accomplished with 4 relevant discussions extracted and verified.",
                "action": {"action": "finish", "answer": "Extracted top discussions on browser automation agents with point totals."},
                "total_tokens": 620,
                "cost_usd": 0.0015,
                "latency_ms": 150.0,
                "screenshot_base64": frame_b64,
            }
        ],
        total_tokens=2840,
        total_cost_usd=0.0071,
        final_answer="Successfully scraped top Hacker News stories and discussions regarding autonomous agents.",
        extracted_data=[
            {"rank": 1, "title": "BrowserPilot: Autonomous a11y & stealth web agent", "points": 342, "comments": 89},
            {"rank": 2, "title": "Why accessibility trees are 80% cheaper than vision screenshots", "points": 287, "comments": 114},
            {"rank": 3, "title": "Evading Cloudflare Turnstile and DataDome with Chromium CDP patches", "points": 219, "comments": 67},
            {"rank": 4, "title": "Cubic Bézier mouse trajectories in Playwright", "points": 174, "comments": 43},
        ]
    )

    # 2. Archive 2: GitHub Trending
    SessionArchiveManager.save_session(
        session_id="sess_github_trending",
        goal="Audit trending browser automation repositories on GitHub",
        steps=[
            {
                "step_number": 1,
                "url": "https://github.com/trending",
                "title": "Trending repositories on GitHub today",
                "thought": "Navigate to GitHub trending page and isolate repository cards.",
                "action": {"action": "goto", "url": "https://github.com/trending"},
                "total_tokens": 510,
                "cost_usd": 0.0012,
                "latency_ms": 310.0,
                "screenshot_base64": frame_b64,
            },
            {
                "step_number": 2,
                "url": "https://github.com/trending",
                "title": "Trending repositories on GitHub today",
                "thought": "Click on language filter dropdown [6] to filter by Python repositories.",
                "action": {"action": "click", "element_id": 6},
                "total_tokens": 730,
                "cost_usd": 0.0018,
                "latency_ms": 220.0,
                "screenshot_base64": frame_b64,
            },
            {
                "step_number": 3,
                "url": "https://github.com/trending/python",
                "title": "Trending Python repositories on GitHub today",
                "thought": "Recorded trending Python automation engines and star trajectories.",
                "action": {"action": "finish", "answer": "Found trending Python projects with browser automation focus."},
                "total_tokens": 600,
                "cost_usd": 0.0012,
                "latency_ms": 140.0,
                "screenshot_base64": frame_b64,
            }
        ],
        total_tokens=1840,
        total_cost_usd=0.0042,
        final_answer="Found trending Python projects with browser automation focus."
    )

    # 3. Profile
    profile_data = {
        "cookies": [
            {"name": "session_id", "value": "xyz123stealth", "domain": ".github.com", "path": "/"}
        ],
        "origins": []
    }
    (PROFILES_DIR / "github-auth.json").write_text(json.dumps(profile_data, indent=2), encoding="utf-8")
    print("Fixtures created with screenshots.")

if __name__ == "__main__":
    asyncio.run(main())
