"""Recapture browserpilot_replay.png with active session screenshot frame."""

import asyncio
import sys
import threading
import time
from pathlib import Path
from playwright.async_api import async_playwright
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from browserpilot.server.app import create_app
from capture_real_assets import render_frame_base64, setup_live_mission_state

DOCS_DIR = Path("B:/workgit/browserpilot/docs/images")


def start_server_daemon(port=9672):
    app = create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(1.8)
    return server


async def main():
    frame_b64 = await render_frame_base64()
    setup_live_mission_state(frame_b64)

    port = 9672
    start_server_daemon(port)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(f"http://127.0.0.1:{port}", wait_until="networkidle")
        await page.wait_for_timeout(800)

        # Open missions archive modal
        await page.click("button:has-text('Missions')")
        await page.wait_for_timeout(500)

        # Open sess_hacker_news_ai
        await page.click("text=sess_hacker_news_ai")
        await page.wait_for_timeout(900)

        replay_path = DOCS_DIR / "browserpilot_replay.png"
        await page.screenshot(path=str(replay_path))
        print(f"Captured {replay_path}")

        await page.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
