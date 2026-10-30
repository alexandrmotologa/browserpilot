"""Generate high-fidelity UI screenshots and animated demo GIF for BrowserPilot."""

import asyncio
import base64
import json
import logging
import math
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from playwright.async_api import async_playwright
import uvicorn
from browserpilot.agent.actions import ActionCommand
from browserpilot.agent.planner import AgentPlanner, AgentStep
from browserpilot.dom.a11y_tree import ActionableElement
from browserpilot.server.app import create_app
from browserpilot.server.routes import state
from browserpilot.server.ws_telemetry import telemetry_hub

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("capture_assets")

DOCS_DIR = Path("B:/workgit/browserpilot/docs/images")
DOCS_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR = Path("B:/workgit/browserpilot/temp_gif_frames")


class MockBrowserManager:
    """Mock browser manager holding tabs metadata for screenshot captures."""
    engine_type = "patchright"
    pages = [1, 2]

    async def get_tabs(self):
        return [
            {
                "index": 0,
                "url": "https://news.ycombinator.com",
                "title": "Hacker News - Autonomous Agents Discussion",
                "is_active": True,
            },
            {
                "index": 1,
                "url": "https://github.com/trending",
                "title": "GitHub - Trending Web Scraping & Stealth Repositories",
                "is_active": False,
            },
        ]


def build_synthetic_web_frame() -> str:
    """Render a clean, high-tech webpage simulation at 1280x800 for authentic viewport streaming."""
    html_content = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0b0f19;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    width: 1280px;
    height: 800px;
    overflow: hidden;
  }
  header {
    background: #0f172a;
    border-bottom: 1px solid #1e293b;
    padding: 16px 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .brand { display: flex; align-items: center; gap: 12px; }
  .logo-box {
    width: 32px; height: 32px; background: #ff6600; border-radius: 6px;
    display: flex; align-items: center; justify-content: center; font-weight: bold; color: white; font-size: 18px;
  }
  .site-title { font-size: 16px; font-weight: 700; color: #f8fafc; }
  .nav-links { display: flex; gap: 20px; font-size: 13px; color: #94a3b8; }
  .nav-links a { color: inherit; text-decoration: none; }
  .nav-links a.active { color: #38bdf8; font-weight: 600; }
  .search-bar {
    background: #1e293b; border: 1px solid #334155; border-radius: 8px;
    padding: 7px 14px; font-size: 12px; color: #cbd5e1; width: 280px;
  }
  main {
    padding: 24px 32px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .story-card {
    background: #131c2e;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 14px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .story-left { display: flex; align-items: center; gap: 16px; }
  .rank { font-size: 18px; font-weight: 700; color: #64748b; width: 28px; text-align: center; }
  .story-title { font-size: 15px; font-weight: 600; color: #f1f5f9; margin-bottom: 4px; }
  .story-domain { font-size: 12px; color: #38bdf8; text-decoration: none; margin-left: 6px; }
  .meta { font-size: 12px; color: #64748b; display: flex; gap: 12px; align-items: center; }
  .vote-btn {
    background: #0284c7; color: white; border: none; border-radius: 6px;
    padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer;
  }
  .badge-tag {
    background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3);
    font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 500;
  }
</style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="logo-box">Y</div>
      <div class="site-title">Hacker News</div>
      <div class="nav-links">
        <a href="#" class="active">top</a>
        <a href="#">new</a>
        <a href="#">past</a>
        <a href="#">comments</a>
        <a href="#">ask</a>
        <a href="#">show</a>
        <a href="#">jobs</a>
      </div>
    </div>
    <input type="text" class="search-bar" value="browser automation agents..." readonly>
  </header>
  <main>
    <div class="story-card">
      <div class="story-left">
        <div class="rank">1.</div>
        <div>
          <div class="story-title">BrowserPilot: Autonomous a11y & stealth web agent <a href="#" class="story-domain">(github.com/browserpilot)</a></div>
          <div class="meta">
            <span>342 points</span>
            <span>by alexandrm</span>
            <span>2 hours ago</span>
            <span>89 comments</span>
            <span class="badge-tag">Show HN</span>
          </div>
        </div>
      </div>
      <button class="vote-btn">Upvote (342)</button>
    </div>

    <div class="story-card">
      <div class="story-left">
        <div class="rank">2.</div>
        <div>
          <div class="story-title">Why accessibility trees reduce LLM token usage by 80% <a href="#" class="story-domain">(deepmind.google)</a></div>
          <div class="meta">
            <span>287 points</span>
            <span>by techlead</span>
            <span>4 hours ago</span>
            <span>114 comments</span>
          </div>
        </div>
      </div>
      <button class="vote-btn">Upvote (287)</button>
    </div>

    <div class="story-card">
      <div class="story-left">
        <div class="rank">3.</div>
        <div>
          <div class="story-title">Evading Cloudflare Turnstile and DataDome with Chromium CDP patches <a href="#" class="story-domain">(blog.stealth.dev)</a></div>
          <div class="meta">
            <span>219 points</span>
            <span>by reverse_eng</span>
            <span>5 hours ago</span>
            <span>67 comments</span>
            <span class="badge-tag">Security</span>
          </div>
        </div>
      </div>
      <button class="vote-btn">Upvote (219)</button>
    </div>

    <div class="story-card">
      <div class="story-left">
        <div class="rank">4.</div>
        <div>
          <div class="story-title">Cubic Bézier mouse trajectories and micro-tremor simulation in Playwright <a href="#" class="story-domain">(arxiv.org)</a></div>
          <div class="meta">
            <span>174 points</span>
            <span>by ml_researcher</span>
            <span>7 hours ago</span>
            <span>43 comments</span>
          </div>
        </div>
      </div>
      <button class="vote-btn">Upvote (174)</button>
    </div>

    <div class="story-card">
      <div class="story-left">
        <div class="rank">5.</div>
        <div>
          <div class="story-title">Stagehand vs Browser-Use: Benchmarking web agent architectures <a href="#" class="story-domain">(benchmark.ai)</a></div>
          <div class="meta">
            <span>158 points</span>
            <span>by agentdev</span>
            <span>8 hours ago</span>
            <span>38 comments</span>
          </div>
        </div>
      </div>
      <button class="vote-btn">Upvote (158)</button>
    </div>
  </main>
</body>
</html>"""
    return html_content


def get_mock_actionable_elements() -> list[ActionableElement]:
    """Return realistic ActionableElements corresponding to the synthetic webpage."""
    return [
        ActionableElement(id=1, role="link", tag="a", name="Hacker News", x=28, y=16, width=120, height=32),
        ActionableElement(id=2, role="link", tag="a", name="top", x=160, y=22, width=30, height=20),
        ActionableElement(id=3, role="link", tag="a", name="new", x=200, y=22, width=30, height=20),
        ActionableElement(id=4, role="link", tag="a", name="comments", x=280, y=22, width=65, height=20),
        ActionableElement(id=5, role="searchbox", tag="input", name="Search", x=972, y=16, width=280, height=34),
        ActionableElement(id=6, role="link", tag="a", name="BrowserPilot: Autonomous a11y & stealth web agent", x=76, y=86, width=420, height=24),
        ActionableElement(id=7, role="button", tag="button", name="Upvote (342)", x=1150, y=82, width=102, height=32),
        ActionableElement(id=8, role="link", tag="a", name="Why accessibility trees reduce LLM token usage by 80%", x=76, y=176, width=480, height=24),
        ActionableElement(id=9, role="button", tag="button", name="Upvote (287)", x=1150, y=172, width=102, height=32),
        ActionableElement(id=10, role="link", tag="a", name="Evading Cloudflare Turnstile and DataDome with Chromium CDP patches", x=76, y=266, width=540, height=24),
        ActionableElement(id=11, role="button", tag="button", name="Upvote (219)", x=1150, y=262, width=102, height=32),
        ActionableElement(id=12, role="link", tag="a", name="Cubic Bézier mouse trajectories in Playwright", x=76, y=356, width=480, height=24),
        ActionableElement(id=13, role="button", tag="button", name="Upvote (174)", x=1150, y=352, width=102, height=32),
        ActionableElement(id=14, role="button", tag="button", name="Upvote (158)", x=1150, y=442, width=102, height=32),
    ]


async def render_frame_base64() -> str:
    """Use Playwright to render the synthetic HTML and return clean base64 JPEG."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.set_content(build_synthetic_web_frame())
        await page.wait_for_timeout(100)
        screenshot_bytes = await page.screenshot(type="jpeg", quality=90)
        await browser.close()
        return base64.b64encode(screenshot_bytes).decode("utf-8")


def setup_live_mission_state(frame_b64: str):
    """Populate FastAPI server state with an authentic running mission."""
    state.browser_manager = MockBrowserManager()
    state.latest_frame = frame_b64
    state.cached_elements = get_mock_actionable_elements()

    planner = AgentPlanner(
        goal="Scrape top 5 AI stories from Hacker News and extract discussion statistics into JSON"
    )
    planner.session_id = "sess_live_mission"
    planner.total_prompt_tokens = 1420
    planner.total_completion_tokens = 420
    planner.total_cost_usd = 0.0038
    planner.is_done = False

    step1 = AgentStep(
        step_number=1,
        url="https://news.ycombinator.com",
        title="Hacker News",
        thought="Navigate to Hacker News home and inspect the top ranked submissions using a11y tree.",
        action=ActionCommand(action="goto", url="https://news.ycombinator.com"),
        prompt_tokens=420,
        completion_tokens=60,
        total_tokens=480,
        cost_usd=0.0011,
        latency_ms=280.0,
    )
    step2 = AgentStep(
        step_number=2,
        url="https://news.ycombinator.com",
        title="Hacker News",
        thought="Target element [7] 'Upvote (342)' to inspect discussion thread on autonomous browser agents.",
        action=ActionCommand(action="click", element_id=7),
        prompt_tokens=480,
        completion_tokens=80,
        total_tokens=560,
        cost_usd=0.0013,
        latency_ms=190.0,
    )
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
        cost_usd=0.0016,
        latency_ms=310.0,
    )

    planner.steps = [step1, step2, step3]
    planner.extracted_data = [
        {"category": "Token Savings", "metric": "82%", "baseline": "Screenshot multimodal agents"},
        {"category": "Bypass Rate", "metric": "98.4%", "baseline": "Cloudflare Turnstile & DataDome"},
        {"category": "Latency / Step", "metric": "320ms", "baseline": "Vision API latency"},
    ]

    state.planner = planner


def run_server_in_thread():
    """Run uvicorn server in background thread."""
    app = create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=9668, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(2.0)
    return server


async def capture_all_assets():
    """Capture screenshots and compile the animated demo GIF."""
    print("Rendering synthetic browser frame...")
    frame_b64 = await render_frame_base64()
    setup_live_mission_state(frame_b64)

    print("Starting background server on port 9668...")
    server = run_server_in_thread()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Desktop Screenshot (1440x900)
        print("Capturing desktop screenshot (1440x900)...")
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://127.0.0.1:9668", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        desktop_path = DOCS_DIR / "browserpilot_desktop.png"
        await page.screenshot(path=str(desktop_path), full_page=False)
        print(f"Captured {desktop_path}")

        # 2. Mobile Screenshot (390x844)
        print("Capturing mobile screenshot (390x844)...")
        mobile_page = await browser.new_page(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15",
        )
        await mobile_page.goto("http://127.0.0.1:9668", wait_until="networkidle")
        await mobile_page.wait_for_timeout(1000)
        mobile_path = DOCS_DIR / "browserpilot_mobile.png"
        await mobile_page.screenshot(path=str(mobile_path), full_page=False)
        await mobile_page.close()
        print(f"Captured {mobile_path}")

        # 3. Co-Pilot Modal Screenshot (1440x900)
        print("Capturing Co-Pilot modal screenshot...")
        # Set state to awaiting approval
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
        await page.wait_for_timeout(800)
        copilot_path = DOCS_DIR / "browserpilot_copilot.png"
        await page.screenshot(path=str(copilot_path), full_page=False)
        print(f"Captured {copilot_path}")

        # Dismiss Co-Pilot modal
        state.planner.awaiting_approval = False
        await telemetry_hub.broadcast({"type": "step_approved"})
        await page.wait_for_timeout(400)

        # 4. Session Replay Modal Screenshot (1440x900)
        print("Capturing Session Replay modal screenshot...")
        # Click on Missions button
        missions_btn = page.locator("button:has-text('Missions')")
        if await missions_btn.count() > 0:
            await missions_btn.click()
            await page.wait_for_timeout(500)
            # Click on first archived session to open the scrubber
            first_session = page.locator("div:has-text('sess_hacker_news_ai')").first
            if await first_session.count() > 0:
                await first_session.click()
                await page.wait_for_timeout(600)

            replay_path = DOCS_DIR / "browserpilot_replay.png"
            await page.screenshot(path=str(replay_path), full_page=False)
            print(f"Captured {replay_path}")

            # Close modal
            close_btn = page.locator("button:has(svg.lucide-x)").first
            if await close_btn.count() > 0:
                await close_btn.click()
                await page.wait_for_timeout(300)

        # 5. Animated Demo GIF Capture
        print("Recording frames for animated demo GIF...")
        FRAMES_DIR.mkdir(parents=True, exist_ok=True)
        # Clear existing frames if any
        for f in FRAMES_DIR.glob("*.png"):
            f.unlink()

        # Let's set up a clean viewport at 1280x800 for the GIF
        gif_page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await gif_page.goto("http://127.0.0.1:9668", wait_until="networkidle")
        await gif_page.wait_for_timeout(600)

        frame_index = 0

        # Sub-sequence 1: Show live view with pulsing badges
        for _ in range(4):
            frame_path = FRAMES_DIR / f"frame_{frame_index:03d}.png"
            await gif_page.screenshot(path=str(frame_path))
            frame_index += 1
            await asyncio.sleep(0.1)

        # Sub-sequence 2: Move mouse cursor smoothly toward element badge [7]
        target_x = 760
        target_y = 230
        start_x = 400
        start_y = 500

        for i in range(8):
            t = i / 7.0
            # Ease in out
            ease = 0.5 - 0.5 * math.cos(t * math.pi)
            cur_x = start_x + (target_x - start_x) * ease
            cur_y = start_y + (target_y - start_y) * ease
            await gif_page.mouse.move(cur_x, cur_y)
            frame_path = FRAMES_DIR / f"frame_{frame_index:03d}.png"
            await gif_page.screenshot(path=str(frame_path))
            frame_index += 1
            await asyncio.sleep(0.08)

        # Sub-sequence 3: Click target
        await gif_page.mouse.down()
        frame_path = FRAMES_DIR / f"frame_{frame_index:03d}.png"
        await gif_page.screenshot(path=str(frame_path))
        frame_index += 1
        await asyncio.sleep(0.08)

        await gif_page.mouse.up()
        frame_path = FRAMES_DIR / f"frame_{frame_index:03d}.png"
        await gif_page.screenshot(path=str(frame_path))
        frame_index += 1

        # Sub-sequence 4: Trigger action feedback in timeline
        for _ in range(4):
            frame_path = FRAMES_DIR / f"frame_{frame_index:03d}.png"
            await gif_page.screenshot(path=str(frame_path))
            frame_index += 1
            await asyncio.sleep(0.1)

        await gif_page.close()
        await page.close()
        await browser.close()

    print(f"Captured {frame_index} frames. Compiling into animated GIF via ffmpeg...")
    gif_path = DOCS_DIR / "browserpilot_demo.gif"

    # Use 2-pass palette generation for ultra crisp colors
    palette_path = FRAMES_DIR / "palette.png"
    ffmpeg_cmd_palette = [
        "ffmpeg", "-y",
        "-framerate", "8",
        "-i", str(FRAMES_DIR / "frame_%03d.png"),
        "-vf", "fps=8,scale=960:-1:flags=lanczos,palettegen=stats_mode=diff",
        str(palette_path),
    ]
    subprocess.run(ffmpeg_cmd_palette, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    ffmpeg_cmd_gif = [
        "ffmpeg", "-y",
        "-framerate", "8",
        "-i", str(FRAMES_DIR / "frame_%03d.png"),
        "-i", str(palette_path),
        "-lavfi", "fps=8,scale=960:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3",
        str(gif_path),
    ]
    subprocess.run(ffmpeg_cmd_gif, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print(f"Generated {gif_path} ({os.path.getsize(gif_path)} bytes)")

    # Clean up temp frames
    shutil.rmtree(FRAMES_DIR, ignore_errors=True)
    print("Done!")


if __name__ == "__main__":
    asyncio.run(capture_all_assets())
