"""Master script to recapture all responsive UI screenshots and animated demo GIF."""

import asyncio
import math
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from playwright.async_api import async_playwright
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from browserpilot.agent.actions import ActionCommand
from browserpilot.agent.planner import AgentStep
from browserpilot.server.app import create_app
from browserpilot.server.routes import state
from browserpilot.server.ws_telemetry import telemetry_hub
from capture_real_assets import (
    render_frame_base64,
    setup_live_mission_state,
)

DOCS_DIR = PROJECT_ROOT / "docs" / "images"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR = PROJECT_ROOT / "gif_frames_recapture"


def start_server_daemon(port=9675):
    app = create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(1.8)
    return server


async def main():
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    for f in FRAMES_DIR.glob("*.png"):
        f.unlink()

    print("Rendering web frame and configuring live mission state...")
    frame_b64 = await render_frame_base64()
    setup_live_mission_state(frame_b64)

    port = 9675
    print(f"Starting server on port {port}...")
    start_server_daemon(port)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ----------------------------------------------------
        # 1. Desktop Studio Screenshot (1440x900)
        # ----------------------------------------------------
        print("Capturing 1440x900 Desktop Studio screenshot...")
        desktop_page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await desktop_page.goto(f"http://127.0.0.1:{port}", wait_until="networkidle")
        await desktop_page.wait_for_timeout(1000)

        desktop_path = DOCS_DIR / "browserpilot_desktop.png"
        await desktop_page.screenshot(path=str(desktop_path))
        print(f"Saved: {desktop_path}")
        await desktop_page.close()

        # ----------------------------------------------------
        # 2. Mobile Responsive Screenshot (390x844)
        # ----------------------------------------------------
        print("Capturing 390x844 Mobile Responsive screenshot...")
        mobile_page = await browser.new_page(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        )
        await mobile_page.goto(f"http://127.0.0.1:{port}", wait_until="networkidle")
        await mobile_page.wait_for_timeout(1000)

        mobile_path = DOCS_DIR / "browserpilot_mobile.png"
        await mobile_page.screenshot(path=str(mobile_path))
        print(f"Saved: {mobile_path}")
        await mobile_page.close()

        # ----------------------------------------------------
        # 3. Co-Pilot Step Approval Modal (1440x900)
        # ----------------------------------------------------
        print("Capturing Co-Pilot Step Approval screenshot...")
        copilot_page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await copilot_page.goto(f"http://127.0.0.1:{port}", wait_until="networkidle")
        await copilot_page.wait_for_timeout(600)

        state.planner.awaiting_approval = True
        copilot_step = AgentStep(
            step_number=4,
            url="https://news.ycombinator.com/item?id=4189201",
            title="BrowserPilot: Autonomous a11y & stealth web agent | Hacker News",
            thought="Target element [7] 'Upvote (342)' to submit upvote action. Requires co-pilot confirmation before mutating state.",
            action=ActionCommand(action="click", element_id=7),
            prompt_tokens=450,
            completion_tokens=65,
            total_tokens=515,
            cost_usd=0.0012,
            latency_ms=210.0,
        )
        await telemetry_hub.broadcast({
            "type": "step_awaiting_approval",
            "step": copilot_step.model_dump(),
        })
        await copilot_page.wait_for_timeout(700)

        copilot_path = DOCS_DIR / "browserpilot_copilot.png"
        await copilot_page.screenshot(path=str(copilot_path))
        print(f"Saved: {copilot_path}")

        # Reset approval state
        state.planner.awaiting_approval = False
        await telemetry_hub.broadcast({"type": "step_approved"})
        await copilot_page.close()

        # ----------------------------------------------------
        # 4. Session Replay Scrubber Modal (1440x900)
        # ----------------------------------------------------
        print("Capturing Session Replay Scrubber screenshot...")
        replay_page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await replay_page.goto(f"http://127.0.0.1:{port}", wait_until="networkidle")
        await replay_page.wait_for_timeout(600)

        # Click Missions button in header
        await replay_page.click("button:has-text('Missions')")
        await replay_page.wait_for_timeout(400)

        # Click on sess_hacker_news_ai
        await replay_page.click("text=sess_hacker_news_ai")
        await replay_page.wait_for_timeout(800)

        replay_path = DOCS_DIR / "browserpilot_replay.png"
        await replay_page.screenshot(path=str(replay_path))
        print(f"Saved: {replay_path}")
        await replay_page.close()

        # ----------------------------------------------------
        # 5. Animated Demo GIF Capture (1280x780)
        # ----------------------------------------------------
        print("Recording frames for animated demo GIF...")
        gif_page = await browser.new_page(viewport={"width": 1280, "height": 780})
        await gif_page.goto(f"http://127.0.0.1:{port}", wait_until="networkidle")
        await gif_page.wait_for_timeout(800)

        frame_num = 0

        # Phase 1: Static observation with a11y numbered badges
        for _ in range(4):
            await gif_page.screenshot(path=str(FRAMES_DIR / f"frame_{frame_num:03d}.png"))
            frame_num += 1
            await asyncio.sleep(0.1)

        # Phase 2: Mouse cursor moves in human-like cubic Bézier curve toward element [7]
        start_x, start_y = 360, 480
        target_x, target_y = 705, 215

        steps = 8
        for i in range(1, steps + 1):
            t = i / float(steps)
            ease = t * t * (3 - 2 * t)
            jitter_x = math.sin(t * 8.0) * 3.0
            jitter_y = math.cos(t * 6.0) * 2.0
            cx = start_x + (target_x - start_x) * ease + jitter_x
            cy = start_y + (target_y - start_y) * ease + jitter_y

            await gif_page.mouse.move(cx, cy)
            await gif_page.screenshot(path=str(FRAMES_DIR / f"frame_{frame_num:03d}.png"))
            frame_num += 1
            await asyncio.sleep(0.08)

        # Phase 3: Click down on badge [7]
        await gif_page.mouse.down()
        await gif_page.screenshot(path=str(FRAMES_DIR / f"frame_{frame_num:03d}.png"))
        frame_num += 1
        await asyncio.sleep(0.1)

        await gif_page.mouse.up()
        await gif_page.screenshot(path=str(FRAMES_DIR / f"frame_{frame_num:03d}.png"))
        frame_num += 1
        await asyncio.sleep(0.1)

        # Phase 4: Hover over Step 3 Extracted Data
        hist_x, hist_y = 1040, 520
        await gif_page.mouse.move(hist_x, hist_y)
        await gif_page.wait_for_timeout(300)
        for _ in range(4):
            await gif_page.screenshot(path=str(FRAMES_DIR / f"frame_{frame_num:03d}.png"))
            frame_num += 1
            await asyncio.sleep(0.1)

        await gif_page.close()
        await browser.close()

    print(f"Captured {frame_num} frames. Compiling with ffmpeg...")
    gif_out = DOCS_DIR / "browserpilot_demo.gif"
    palette = FRAMES_DIR / "palette.png"

    cmd1 = [
        "ffmpeg", "-y",
        "-framerate", "7",
        "-i", str(FRAMES_DIR / "frame_%03d.png"),
        "-vf", "fps=7,scale=960:-1:flags=lanczos,palettegen=stats_mode=diff",
        str(palette),
    ]
    subprocess.run(cmd1, check=True)

    cmd2 = [
        "ffmpeg", "-y",
        "-framerate", "7",
        "-i", str(FRAMES_DIR / "frame_%03d.png"),
        "-i", str(palette),
        "-lavfi", "fps=7,scale=960:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3",
        str(gif_out),
    ]
    subprocess.run(cmd2, check=True)

    file_size_kb = os.path.getsize(gif_out) / 1024
    print(f"Generated {gif_out} ({file_size_kb:.1f} KB)")
    shutil.rmtree(FRAMES_DIR, ignore_errors=True)
    print("All visual assets successfully refreshed!")


if __name__ == "__main__":
    asyncio.run(main())
