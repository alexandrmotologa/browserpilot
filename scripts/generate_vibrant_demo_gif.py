"""Generate a high-fidelity, vibrant animated demo GIF with visible cursor movements,
live step-by-step telemetry updates, a11y badge reveals, and data extraction.
"""

import asyncio
import base64
import json
import math
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from playwright.async_api import async_playwright
import uvicorn

import sys
PROJECT_ROOT = Path("B:/workgit/browserpilot")
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from browserpilot.server.app import create_app
from browserpilot.server.routes import state
from browserpilot.server.ws_telemetry import telemetry_hub
from browserpilot.agent.actions import ActionCommand
from browserpilot.agent.planner import AgentPlanner, AgentStep
from browserpilot.dom.a11y_tree import AccessibilityTreeParser, ActionableElement
from capture_real_assets import MockBrowserManager, build_synthetic_web_frame

DOCS_DIR = Path("B:/workgit/browserpilot/docs/images")
FRAMES_DIR = Path("B:/workgit/browserpilot/vibrant_frames")
PORT = 9675


def start_server_daemon():
    app = create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.8)
    return server


def get_status_dict(planner, override_status=None):
    if not planner:
        return {"status": "idle", "goal": "", "total_steps": 0, "total_tokens": 0, "total_cost_usd": 0.0}
    status = override_status or ("completed" if planner.is_done else "running")
    return {
        "session_id": planner.session_id,
        "status": status,
        "goal": planner.goal,
        "total_steps": len(planner.steps),
        "total_tokens": planner.total_prompt_tokens + planner.total_completion_tokens,
        "total_cost_usd": planner.total_cost_usd,
        "takeover_required": False,
        "co_pilot_mode": False,
        "awaiting_approval": False,
        "final_answer": planner.final_answer,
        "has_extracted_data": bool(planner.extracted_data),
    }


async def render_frame_base64() -> tuple[str, list[ActionableElement]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.set_content(build_synthetic_web_frame())
        await page.wait_for_timeout(200)
        elements = await AccessibilityTreeParser.parse_page(page)
        screenshot_bytes = await page.screenshot(type="jpeg", quality=90)
        await browser.close()
        return base64.b64encode(screenshot_bytes).decode("utf-8"), elements


async def setup_cursor(page):
    await page.evaluate("""() => {
        if (document.getElementById('virtual-agent-cursor')) return;
        const cursor = document.createElement('div');
        cursor.id = 'virtual-agent-cursor';
        cursor.innerHTML = `
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" style="filter: drop-shadow(0 3px 6px rgba(0,0,0,0.9));">
                <path d="M5.5 3.21V20.8c0 .45.54.67.85.35l4.86-4.86a.5.5 0 0 1 .35-.15h6.87a.5.5 0 0 0 .35-.85L6.35 2.85a.5.5 0 0 0-.85.36z" fill="#38bdf8" stroke="#0284c7" stroke-width="1.5"/>
                <circle cx="6" cy="4" r="2.5" fill="#ffffff" />
            </svg>
            <div id="virtual-cursor-ripple" style="position: absolute; top: 0; left: 0; width: 36px; height: 36px; border-radius: 50%; border: 2px solid #38bdf8; opacity: 0; pointer-events: none; transform: translate(-50%, -50%) scale(0.2); transition: all 0.35s ease-out;"></div>
        `;
        cursor.style.position = 'fixed';
        cursor.style.top = '0px';
        cursor.style.left = '0px';
        cursor.style.zIndex = '999999';
        cursor.style.pointerEvents = 'none';
        cursor.style.transform = 'translate(-100px, -100px)';
        cursor.style.transition = 'transform 0.04s linear';
        document.body.appendChild(cursor);
    }""")


async def set_cursor_pos(page, x: float, y: float, click_ripple: bool = False):
    await page.evaluate(f"""() => {{
        const c = document.getElementById('virtual-agent-cursor');
        if (!c) return;
        c.style.transform = 'translate({x:.1f}px, {y:.1f}px)';
        if ({str(click_ripple).lower()}) {{
            const rip = document.getElementById('virtual-cursor-ripple');
            if (rip) {{
                rip.style.opacity = '1';
                rip.style.transform = 'translate(-50%, -50%) scale(1.6)';
                setTimeout(() => {{
                    rip.style.opacity = '0';
                    rip.style.transform = 'translate(-50%, -50%) scale(0.2)';
                }}, 300);
            }}
        }}
    }}""")


async def run_vibrant_capture():
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    for f in FRAMES_DIR.glob("*.png"):
        f.unlink()

    print("Rendering synthetic frame...")
    frame_b64, elements = await render_frame_base64()

    # Pre-setup server state in initial idle state
    state.browser_manager = MockBrowserManager()
    state.latest_frame = frame_b64
    state.cached_elements = elements
    state.planner = None

    print("Starting background server...")
    server = start_server_daemon()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use 1360x840 for optimal 16:10 balance
        page = await browser.new_page(viewport={"width": 1360, "height": 840})
        await page.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle")
        await page.wait_for_timeout(800)
        await setup_cursor(page)

        frame_num = 0

        async def capture_frame():
            nonlocal frame_num
            path = FRAMES_DIR / f"frame_{frame_num:03d}.png"
            await page.screenshot(path=str(path))
            frame_num += 1

        print("Phase 1: Goal Entry & Setup...")
        full_goal = "Scrape top 5 AI stories from Hacker News and extract discussion statistics into JSON"

        # Position cursor near goal input
        await set_cursor_pos(page, 320, 560)
        await capture_frame()

        goal_box = page.locator("textarea").first
        await goal_box.click()

        # Type goal incrementally
        words = full_goal.split(" ")
        typed_text = ""
        for i, word in enumerate(words):
            typed_text += (" " if i > 0 else "") + word
            await goal_box.fill(typed_text)
            # Capture every 2-3 words to keep pacing punchy
            if i % 2 == 0 or i == len(words) - 1:
                await capture_frame()
            await asyncio.sleep(0.04)

        # Set Start URL
        url_input = page.locator("input[placeholder='https://news.ycombinator.com']").first
        await url_input.fill("https://news.ycombinator.com")
        await capture_frame()

        # Move cursor toward 'Launch Mission' button
        # Button is near bottom-left of MissionControls
        launch_btn = page.locator("button:has-text('Launch Mission')").first
        btn_box = await launch_btn.bounding_box()
        bx, by = 135.0, 785.0
        if btn_box:
            bx = btn_box["x"] + btn_box["width"] / 2
            by = btn_box["y"] + btn_box["height"] / 2

        # 4 steps flight toward launch button
        for step in range(4):
            t = (step + 1) / 4.0
            cx = 320 + (bx - 320) * t
            cy = 560 + (by - 560) * t
            await set_cursor_pos(page, cx, cy)
            await capture_frame()

        # Click launch button with ripple
        await set_cursor_pos(page, bx, by, click_ripple=True)
        await capture_frame()

        # Transition status to RUNNING
        print("Phase 2: Launching Mission & Step 1 GOTO...")
        state.planner = AgentPlanner(goal=full_goal)
        state.planner.session_id = "sess_demo"
        step1 = AgentStep(
            step_number=1,
            url="https://news.ycombinator.com",
            title="Hacker News",
            thought="Navigate to Hacker News home and inspect top ranked submissions using a11y tree.",
            action=ActionCommand(action="goto", url="https://news.ycombinator.com"),
            prompt_tokens=420,
            completion_tokens=60,
            total_tokens=480,
            cost_usd=0.0011,
            latency_ms=280.0,
        )
        state.planner.steps = [step1]
        state.planner.total_prompt_tokens = 420
        state.planner.total_completion_tokens = 60
        state.planner.total_cost_usd = 0.0011

        await telemetry_hub.broadcast({
            "type": "step_update",
            "step": step1.model_dump(),
        })
        await page.wait_for_timeout(300)

        # Pulse on step 1 with badges visible
        for _ in range(4):
            await capture_frame()

        print("Phase 3: Autonomous Planning & Bézier Cursor Flight to Badge [8]...")
        # Step 2 thought: target element [8] Upvote button
        step2 = AgentStep(
            step_number=2,
            url="https://news.ycombinator.com",
            title="Hacker News",
            thought="Target element [8] 'Upvote (342)' to inspect discussion thread on autonomous browser agents.",
            action=ActionCommand(action="click", element_id=8),
            prompt_tokens=480,
            completion_tokens=80,
            total_tokens=560,
            cost_usd=0.0013,
            latency_ms=190.0,
        )

        # Animate cursor flying along cubic Bézier curve toward element [8] Upvote button
        # In the 1360x840 layout, the canvas is on the left
        # Target coordinate of Upvote (342) button inside the canvas is approximately x: 670, y: 220
        start_x, start_y = bx, by
        target_x, target_y = 665.0, 218.0

        p1_x = start_x + 50
        p1_y = start_y - 200
        p2_x = target_x - 100
        p2_y = target_y + 120

        curve_steps = 14
        for i in range(1, curve_steps + 1):
            t = i / float(curve_steps)
            # Cubic Bézier formula
            u = 1 - t
            bx_t = (u**3)*start_x + 3*(u**2)*t*p1_x + 3*u*(t**2)*p2_x + (t**3)*target_x
            by_t = (u**3)*start_y + 3*(u**2)*t*p1_y + 3*u*(t**2)*p2_y + (t**3)*target_y

            # subtle human jitter
            jitter = math.sin(t * 12.0) * 1.5
            await set_cursor_pos(page, bx_t + jitter, by_t + jitter)
            await capture_frame()
            await asyncio.sleep(0.04)

        print("Phase 4: Element Click & Step 2 Verification...")
        # Click element [8] with visible ripple
        await set_cursor_pos(page, target_x, target_y, click_ripple=True)
        await capture_frame()
        await capture_frame()

        # Broadcast Step 2 executed
        state.planner.steps = [step1, step2]
        state.planner.total_prompt_tokens = 900
        state.planner.total_completion_tokens = 140
        state.planner.total_cost_usd = 0.0024

        await telemetry_hub.broadcast({
            "type": "step_update",
            "step": step2.model_dump(),
        })
        await page.wait_for_timeout(300)

        for _ in range(4):
            await capture_frame()

        print("Phase 5: Step 3 Data Extraction & Payload Table Reveal...")
        step3 = AgentStep(
            step_number=3,
            url="https://news.ycombinator.com/item?id=4189201",
            title="BrowserPilot: Autonomous a11y & stealth web agent | Hacker News",
            thought="Extract discussion statistics and developer benchmarks into structured dataset.",
            action=ActionCommand(
                action="extract_data",
                extracted_data=[
                    {"category": "Token Savings", "metric": "82%", "baseline": "Screenshot multimodal agents"},
                    {"category": "Bypass Rate", "metric": "98.4%", "baseline": "Cloudflare Turnstile & DataDome"},
                    {"category": "Latency / Step", "metric": "320ms", "baseline": "Vision API latency"},
                ],
            ),
            prompt_tokens=520,
            completion_tokens=180,
            total_tokens=700,
            cost_usd=0.0014,
            latency_ms=310.0,
        )

        state.planner.steps = [step1, step2, step3]
        state.planner.total_prompt_tokens = 1420
        state.planner.total_completion_tokens = 420
        state.planner.total_cost_usd = 0.0038
        state.planner.has_extracted_data = True
        state.planner.extracted_data = step3.action.extracted_data

        await telemetry_hub.broadcast({
            "type": "step_update",
            "step": step3.model_dump(),
        })
        await page.wait_for_timeout(300)

        # Move cursor to inspect extracted data in timeline (right column)
        ext_x, ext_y = 1040.0, 560.0
        for i in range(5):
            t = (i + 1) / 5.0
            cx = target_x + (ext_x - target_x) * t
            cy = target_y + (ext_y - target_y) * t
            await set_cursor_pos(page, cx, cy)
            await capture_frame()

        for _ in range(4):
            await capture_frame()

        print("Phase 6: Mission Completed Final Answer Card...")
        state.planner.is_done = True
        final_ans = "Successfully extracted 5 top stories from Hacker News. Computed token savings of 82% vs vision baselines with 0 bot challenges triggered."
        state.planner.final_answer = final_ans

        await telemetry_hub.broadcast({
            "type": "session_completed",
            "final_answer": final_ans,
            "has_extracted_data": True,
        })
        await page.wait_for_timeout(300)

        # Move cursor slightly over JSON download button
        await set_cursor_pos(page, 1180, 230)
        for _ in range(12):
            await capture_frame()

        # Capture updated desktop and mobile screenshots while we are in this beautiful completed state!
        print("Capturing updated high-fidelity static screenshots...")
        # Desktop (1440x900)
        dt_page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await dt_page.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle")
        await dt_page.wait_for_timeout(500)
        await dt_page.screenshot(path=str(DOCS_DIR / "browserpilot_desktop.png"))
        print("Updated browserpilot_desktop.png")

        # Co-Pilot Modal (1440x900)
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
        await dt_page.wait_for_timeout(600)
        await dt_page.screenshot(path=str(DOCS_DIR / "browserpilot_copilot.png"))
        print("Updated browserpilot_copilot.png")

        # Dismiss Co-Pilot modal
        await telemetry_hub.broadcast({"type": "step_approved"})
        await dt_page.wait_for_timeout(300)

        # Session Replay Modal (1440x900)
        missions_btn = dt_page.locator("button:has-text('Missions')")
        if await missions_btn.count() > 0:
            await missions_btn.click()
            await dt_page.wait_for_timeout(500)
            first_session = dt_page.locator("div:has-text('sess_hacker_news_ai')").first
            if await first_session.count() > 0:
                await first_session.click()
                await dt_page.wait_for_timeout(600)
            await dt_page.screenshot(path=str(DOCS_DIR / "browserpilot_replay.png"))
            print("Updated browserpilot_replay.png")

        await dt_page.close()

        # Mobile (390x844)
        mb_page = await browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        await mb_page.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle")
        await mb_page.wait_for_timeout(500)
        await mb_page.screenshot(path=str(DOCS_DIR / "browserpilot_mobile.png"))
        await mb_page.close()
        print("Updated browserpilot_mobile.png")

        await page.close()
        await browser.close()

    print(f"Captured {frame_num} vibrant frames. Compiling with FFmpeg at 10 FPS...")
    gif_out = DOCS_DIR / "browserpilot_demo.gif"
    palette = FRAMES_DIR / "palette.png"

    # 2-pass high quality GIF with Lanczos scaling and diffuse dithering
    cmd1 = [
        "ffmpeg", "-y",
        "-framerate", "10",
        "-i", str(FRAMES_DIR / "frame_%03d.png"),
        "-vf", "fps=10,scale=1080:-1:flags=lanczos,palettegen=stats_mode=diff",
        str(palette),
    ]
    subprocess.run(cmd1, check=True)

    cmd2 = [
        "ffmpeg", "-y",
        "-framerate", "10",
        "-i", str(FRAMES_DIR / "frame_%03d.png"),
        "-i", str(palette),
        "-lavfi", "fps=10,scale=1080:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3",
        str(gif_out),
    ]
    subprocess.run(cmd2, check=True)

    size_kb = os.path.getsize(gif_out) / 1024
    print(f"DONE! Generated {gif_out} ({size_kb:.1f} KB, {frame_num} frames at 10 FPS)")

    # Clean up frames
    shutil.rmtree(FRAMES_DIR, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(run_vibrant_capture())
