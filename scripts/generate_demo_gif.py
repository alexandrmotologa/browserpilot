"""Generate high-quality animated demo GIF and detailed session replay screenshot."""

import asyncio
import base64
import math
import os
import shutil
import subprocess
import threading
import time
import sys
from pathlib import Path

# Add project root and scripts dir to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from playwright.async_api import async_playwright
import uvicorn
from browserpilot.server.app import create_app
from browserpilot.server.routes import state
from browserpilot.server.ws_telemetry import telemetry_hub

from capture_real_assets import (
    MockBrowserManager,
    build_synthetic_web_frame,
    get_mock_actionable_elements,
    render_frame_base64,
    setup_live_mission_state,
)

DOCS_DIR = Path("B:/workgit/browserpilot/docs/images")
FRAMES_DIR = Path("B:/workgit/browserpilot/gif_frames")


def start_server_daemon(port=9670):
    app = create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.8)
    return server


async def run_gif_and_replay_capture():
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    for f in FRAMES_DIR.glob("*.png"):
        f.unlink()

    print("Rendering base frame...")
    frame_b64 = await render_frame_base64()
    setup_live_mission_state(frame_b64)

    port = 9670
    print(f"Starting server on port {port}...")
    start_server_daemon(port)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Capture Replay with active scrubber loaded
        print("Capturing active Session Replay scrubber screenshot...")
        replay_page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await replay_page.goto(f"http://127.0.0.1:{port}", wait_until="networkidle")
        await replay_page.wait_for_timeout(800)

        # Click Missions button
        await replay_page.click("button:has-text('Missions')")
        await replay_page.wait_for_timeout(500)

        # Click the session card
        session_card = replay_page.locator("text=sess_hacker_news_ai").first
        if await session_card.count() > 0:
            await session_card.click()
            await replay_page.wait_for_timeout(800)

        replay_path = DOCS_DIR / "browserpilot_replay.png"
        await replay_page.screenshot(path=str(replay_path))
        print(f"Updated {replay_path}")
        await replay_page.close()

        # 2. Record frames for animated demo GIF
        print("Recording animated GIF frames...")
        gif_page = await browser.new_page(viewport={"width": 1280, "height": 780})
        await gif_page.goto(f"http://127.0.0.1:{port}", wait_until="networkidle")
        await gif_page.wait_for_timeout(800)

        frame_num = 0

        # Phase 1: Static observe state with pulsing badge overlays (3 frames)
        for _ in range(3):
            await gif_page.screenshot(path=str(FRAMES_DIR / f"frame_{frame_num:03d}.png"))
            frame_num += 1
            await asyncio.sleep(0.12)

        # Phase 2: Mouse cursor moves in a realistic cubic Bézier trajectory from bottom center toward Badge [7]
        # Target: Button [7] 'Upvote (342)' near top right of canvas
        # Canvas coordinates: start (380, 480) -> control points -> target (720, 218)
        start_x, start_y = 360, 480
        target_x, target_y = 705, 215

        steps = 8
        for i in range(1, steps + 1):
            t = i / float(steps)
            # Smoothstep easing
            ease = t * t * (3 - 2 * t)
            # Add subtle jitter
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

        # Phase 4: Hover over Step 3 Extracted Data / Action History
        hist_x, hist_y = 1040, 520
        await gif_page.mouse.move(hist_x, hist_y)
        await gif_page.wait_for_timeout(300)
        for _ in range(4):
            await gif_page.screenshot(path=str(FRAMES_DIR / f"frame_{frame_num:03d}.png"))
            frame_num += 1
            await asyncio.sleep(0.12)

        await gif_page.close()
        await browser.close()

    print(f"Captured {frame_num} frames. Compiling with ffmpeg...")
    gif_out = DOCS_DIR / "browserpilot_demo.gif"
    palette = FRAMES_DIR / "palette.png"

    # 2-pass high quality GIF with Lanczos scaling and diffuse dithering
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
    print(f"Successfully generated {gif_out} ({file_size_kb:.1f} KB)")

    shutil.rmtree(FRAMES_DIR, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(run_gif_and_replay_capture())
