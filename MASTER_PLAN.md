# BrowserPilot: Master Implementation Plan

> Autonomous Vision-Language Web Agent and Stealth Browser Automation Engine with Anti-Bot Resilience

Next-generation open-source autonomous web browsing agent. Combines visual element grounding with the Chrome Accessibility (a11y) tree to reduce token consumption by 80%, bypasses bot detection (Cloudflare Turnstile, DataDome) via stealth CDP patches, handles dynamic Single Page Application (SPA) state changes, and supports seamless human-in-the-loop handovers.

---

## 1. Project Overview and Architecture

Browser agents navigating production websites face major practical challenges:
1. **Token Expenses and Latency**: Transmitting full-page screenshots to multimodal models on every step costs thousands of tokens per minute and introduces 5 to 10 seconds of round-trip latency.
2. **Bot Detection**: Default Playwright and Puppeteer sessions trigger Cloudflare, DataDome, and PerimeterX blocks due to exposed automation flags (`navigator.webdriver`, inconsistent CDP signatures).
3. **Fragile DOM Grounding**: Dynamic SPAs with shifting layouts, sticky navigation bars, and modal overlays cause coordinate mismatches.
4. **Interactive Verification Hurdles**: When websites present SMS verification, two-factor authentication, or interactive CAPTCHAs, automated workflows halt.

BrowserPilot addresses these issues directly:
- **Hybrid Accessibility (a11y) and Visual Grounding**: Extracts interactive DOM elements from Chrome DevTools Protocol (`Accessibility.getFullAXTree`), tagging actionable elements with indexed bounding IDs (`[14] Button: "Checkout"`). This cuts token overhead by 80% while preserving spatial precision.
- **Stealth CDP Engine**: Applies low-level CDP patches and optional `patchright` integration to mask automated flags, normalize WebGL/Audio fingerprints, and simulate human cursor trajectories using cubic Bézier curves with micro-jitter.
- **Self-Healing Execution Cycle**: Executes an autonomous Observe, Reason, Act, Verify loop that detects failed actions, stale nodes, or modal overlays and recovers automatically.
- **Human-in-the-Loop Handover**: Automatically flags CAPTCHA and 2FA challenges, pauses agent execution, streams an interactive browser viewport to the operator, accepts remote mouse and keyboard events, and resumes once verified.
- **Mission Control Web Studio**: Built with React 19, featuring live viewport streaming, action decision history, real-time token expenditure tracking, and interactive takeover controls.

```
+-----------------------------------------------------------------------------------+
|                                   BROWSERPILOT                                    |
+-----------------------------------------+-----------------------------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                                                   |
+-------v-------------------------+                 +-----------------------v-------+
|     Stealth Chromium Engine     |                 |  Hybrid a11y & Visual Ground  |
|  * Patched CDP / Anti-Detection |                 |  * Chrome Accessibility Tree  |
|  * Cloudflare Turnstile Bypass  |                 |  * Indexed Element Bounds [14]|
|  * Human Cursor Bezier Curves   |                 |  * 80% Token Cost Reduction   |
+-------+-------------------------+                 +-----------------------+-------+
        |                                                                   |
        +---------------------------------+---------------------------------+
                                          |
                        +-----------------v-----------------+
                        |   Autonomous Execution Planner    |
                        |  * Observe -> Plan -> Act -> Verify|
                        |  * Dynamic Modal & Popup Recovery |
                        |  * Multi-Provider (OpenAI, Claude)|
                        +-----------------+-----------------+
                                          |
                        +-----------------v-----------------+
                        |    Human-in-the-Loop Handover     |
                        |  * Detects CAPTCHA & 2FA Screens  |
                        |  * Two-Way Remote Canvas Stream   |
                        |  * Seamless Auto-Resume           |
                        +-----------------+-----------------+
                                          |
                        +-----------------v-----------------+
                        |   Mission Control Web Studio      |
                        |  * Live Viewport Stream           |
                        |  * Action Decision Timeline       |
                        |  * Token Cost Meter (Port 9660)   |
                        +-----------------------------------+
```

---

## 2. Directory Structure

```
browserpilot/
├── docs/
│   ├── ARCHITECTURE.md           # System design and component interactions
│   ├── API_REFERENCE.md          # REST and WebSocket interface specifications
│   ├── STEALTH_ENGINE.md         # CDP masking and bot evasion strategies
│   └── A11Y_TREE.md              # Accessibility tree parsing and indexing details
├── src/
│   └── browserpilot/
│       ├── __init__.py           # Package exports and version metadata
│       ├── config.py             # Pydantic application settings
│       ├── browser/
│       │   ├── __init__.py
│       │   ├── stealth_context.py# Playwright/Patchright browser launcher with stealth flags
│       │   ├── cursor_motion.py  # Human-like Bezier curve mouse trajectory emulator
│       │   └── fingerprint.py    # WebGL, audio, and navigator property normalizer
│       ├── dom/
│       │   ├── __init__.py
│       │   ├── a11y_tree.py      # Accessibility tree parser extracting interactive nodes
│       │   ├── element_highlighter.py # Ephemeral numbered bounding badge overlay
│       │   └── spatial_matcher.py# Viewport coordinate correlation and visibility checks
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── models.py         # Multi-provider LLM interface (OpenAI, Claude, Gemini, Ollama)
│       │   ├── planner.py        # Autonomous agent execution loop
│       │   ├── actions.py        # Action executors: click, type, scroll, select, press
│       │   └── verifier.py       # Post-action verification and recovery heuristics
│       ├── human/
│       │   ├── __init__.py
│       │   ├── captcha_detector.py # Heuristic detector for Turnstile, reCAPTCHA, hCaptcha, 2FA
│       │   └── stream_relay.py   # Two-way viewport streaming and remote input relay
│       ├── server/
│       │   ├── __init__.py
│       │   ├── app.py            # FastAPI backend application
│       │   ├── routes.py         # REST endpoints for session and mission control
│       │   └── ws_telemetry.py   # WebSocket broadcaster for live telemetry and remote input
│       └── cli.py                # Command-line interface with rich console outputs
├── web/                          # React 19 Mission Control Web Studio
│   ├── src/
│   │   ├── components/
│   │   │   ├── LiveBrowserView.tsx    # Viewport canvas with remote input handling
│   │   │   ├── ActionHistory.tsx      # Step-by-step decision log with LLM reasoning
│   │   │   ├── HumanTakeoverModal.tsx # Interactive takeover overlay for CAPTCHA/2FA
│   │   │   ├── TokenUsageCard.tsx     # Real-time token expenditure tracker
│   │   │   └── MissionControls.tsx    # Goal input, pause, resume, step controls
│   │   ├── hooks/
│   │   │   └── useAgentSession.ts     # WebSocket telemetry and action dispatcher
│   │   ├── types.ts                   # Shared TypeScript definitions
│   │   ├── App.tsx                    # Main mission control layout
│   │   ├── index.css                  # Modern styling
│   │   └── main.tsx                   # React 19 entry point
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── tests/
│   ├── test_a11y_tree.py         # A11y tree parser and token compaction tests
│   ├── test_cursor_motion.py     # Mouse motion smoothness and velocity checks
│   ├── test_stealth.py           # Evasion evaluation and navigator properties
│   ├── test_planner.py           # Agent decision schema and parsing tests
│   └── test_api.py               # FastAPI endpoints and telemetry streaming
├── pyproject.toml
└── README.md
```

---

## 3. Implementation Plan and Work Packages

### Phase 1: Project Setup and Foundational Infrastructure
- [x] Repository initialization on GitHub with metadata and topics.
- [x] Portfolio registry synchronization in MTLG ecosystem.
- [ ] Create `pyproject.toml` and `.gitignore`.
- [ ] Implement `src/browserpilot/config.py` with environment variable loading.
- [ ] Set up package structure with standard exports.

### Phase 2: Stealth Chromium Engine and Cursor Motion
- [ ] Implement `src/browserpilot/browser/fingerprint.py`:
  - Evasion scripts injected before document load.
  - Navigator properties: `webdriver: false`, `plugins`, `languages`, `platform`.
  - WebGL vendor and renderer masking.
  - AudioContext noise injection and canvas noise normalization.
- [ ] Implement `src/browserpilot/browser/cursor_motion.py`:
  - Cubic Bézier curve generation between start and target points.
  - Variable velocity profiles with acceleration and deceleration.
  - Micro-jitter and overshoot corrections.
  - Natural pre-click dwell pauses.
- [ ] Implement `src/browserpilot/browser/stealth_context.py`:
  - Unified browser manager supporting `patchright` with fallback to `playwright`.
  - Anti-automation arguments (`--disable-blink-features=AutomationControlled`).
  - Viewport configuration, user agent rotation, and persistent context support.

### Phase 3: Accessibility Tree Parsing and Spatial Grounding
- [ ] Implement `src/browserpilot/dom/spatial_matcher.py`:
  - Calculate bounding boxes and viewport intersections.
  - Filter obscured or off-screen elements.
- [ ] Implement `src/browserpilot/dom/a11y_tree.py`:
  - Query Chrome DevTools Protocol `Accessibility.getFullAXTree`.
  - Filter actionable nodes (button, link, input, select, checkbox, radio).
  - Assign stable numeric IDs (`[1]`, `[2]`, `[3]`).
  - Generate token-compact text representations for LLM prompts.
- [ ] Implement `src/browserpilot/dom/element_highlighter.py`:
  - Ephemeral badge overlay script injected into page DOM.
  - Render colored badges matching element IDs for visual inspection and streaming.

### Phase 4: Autonomous Agent Planner and Execution Loop
- [ ] Implement `src/browserpilot/agent/models.py`:
  - LLM client adapter supporting OpenAI, Anthropic Claude, Gemini, and Ollama.
  - Structured output parsing with fallback repair for malformed JSON.
- [ ] Implement `src/browserpilot/agent/actions.py`:
  - Executors for `click`, `type`, `scroll`, `select`, `press_key`, `wait`, `goto`.
  - Humanized typing with variable key intervals.
- [ ] Implement `src/browserpilot/agent/verifier.py`:
  - Post-action verification evaluating DOM mutations, network idle, and URL shifts.
  - Detection of stale elements, blocking modals, or failed submissions.
- [ ] Implement `src/browserpilot/agent/planner.py`:
  - Observe, Reason, Act, Verify loop.
  - Prompt construction combining goal, current URL, and compact a11y tree.
  - Step counter, error retry strategy, and execution trace logging.

### Phase 5: Human-in-the-Loop Handover and Detection
- [ ] Implement `src/browserpilot/human/captcha_detector.py`:
  - Heuristics for Cloudflare Turnstile, Google reCAPTCHA, hCaptcha, and AWS WAF.
  - Keyword pattern matching for OTP, SMS, and authenticator challenges.
- [ ] Implement `src/browserpilot/human/stream_relay.py`:
  - Viewport frame capture pipeline with dynamic JPEG compression.
  - Two-way input bridge translating frontend click/type coordinates to browser events.
  - Pause and resume synchronization primitives.

### Phase 6: Server and WebSocket Telemetry
- [ ] Implement `src/browserpilot/server/routes.py`:
  - Session lifecycle management (start, stop, pause, resume).
  - Mission status and step inspection endpoints.
- [ ] Implement `src/browserpilot/server/ws_telemetry.py`:
  - WebSocket hub broadcasting live frames, active element trees, and LLM thoughts.
  - Incoming client event receiver for remote interactive control.
- [ ] Implement `src/browserpilot/server/app.py`:
  - FastAPI application mounting API routes, WebSockets, and static frontend assets.

### Phase 7: Mission Control Web Studio (React 19)
- [ ] Initialize modern React 19 + TypeScript + Vite project in `web/`.
- [ ] Implement `LiveBrowserView.tsx` with remote canvas interaction.
- [ ] Implement `ActionHistory.tsx` displaying step timelines, reasoning, and actions.
- [ ] Implement `HumanTakeoverModal.tsx` for alert notices and manual intervention.
- [ ] Implement `TokenUsageCard.tsx` showing tokens and estimated costs.
- [ ] Implement `MissionControls.tsx` for starting goals, pausing, stepping, and aborting.
- [ ] Build and bundle production frontend into static distribution.

### Phase 8: Command-Line Interface and Validation Suite
- [ ] Implement `src/browserpilot/cli.py` with Typer and Rich console:
  - `browserpilot run "<goal>"`
  - `browserpilot serve --port 9660`
  - `browserpilot test-stealth`
  - `browserpilot dump-tree <url>`
- [ ] Comprehensive automated test suite in `tests/`.
- [ ] End-to-end verification running realistic web navigation tasks.
