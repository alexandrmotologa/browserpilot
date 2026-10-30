# Architecture and Design

BrowserPilot is structured around four subsystems: the browser runtime, the DOM observer, the reasoning planner, and the telemetry server.

```
                      +-----------------------------+
                      |       User Goal / CLI       |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |   Autonomous Agent Planner  | <----+
                      +--------------+--------------+      |
                                     |                     |
                  +------------------+------------------+  |
                  |                                     |  |
                  v                                     v  |
     +-------------------------+           +---------------+---------------+
     |  Browser Stealth Core   |           | DOM Accessibility Parser      |
     | - Patchright / CDP      |           | - Chrome a11y tree extraction |
     | - Fingerprint overrides |           | - Interactive node pruning    |
     | - Human cursor motion   |           | - Numeric badge indexing      |
     +------------+------------+           +---------------+---------------+
                  |                                     ^
                  v                                     |
     +-------------------------+                        |
     | Action Dispatcher       |                        |
     | - Click, Type, Scroll   |------------------------+
     | - Post-action verifier  | (Verify DOM state changes)
     +------------+------------+
                  |
     +------------v------------+           +-------------------------------+
     | Captcha & 2FA Detector  |---------->| Human-in-the-Loop Relay       |
     +-------------------------+ (Alert)   | - WebSocket viewport stream   |
                                           | - Two-way input forwarding    |
                                           | - Operator resume control     |
                                           +---------------+---------------+
                                                           |
                                           +---------------v---------------+
                                           | React 19 Mission Control      |
                                           +-------------------------------+
```

## Subsystems

### 1. Browser Runtime (`browserpilot.browser`)

The browser runtime manages Chromium instances. It supports two launch drivers:
- **Patchright**: A patched version of Playwright that removes internal automation flags at the binary and protocol levels, eliminating CDP runtime detection vectors.
- **Standard Playwright with Custom Stealth**: When Patchright binaries are not present, BrowserPilot falls back to standard Chromium, injecting script evaluations before document load (`Page.addInitScript`) to patch `navigator.webdriver`, fake hardware concurrency, override canvas and WebGL properties, and normalize permissions.

The cursor emulator calculates cubic Bézier trajectories. Instead of instantly setting pointer coordinates, it interpolates movement across intermediate steps with random micro-tremors and natural dwell delays before clicks.

### 2. DOM Accessibility Parser (`browserpilot.dom`)

Traditional vision agents capture high-resolution screenshots on every step and transmit them to multimodal models. On complex pages, this consumes between 1,500 and 3,000 tokens per action.

BrowserPilot extracts the page accessibility tree through the Chrome DevTools Protocol (`Accessibility.getFullAXTree`). The parser:
1. Traverses the accessibility hierarchy.
2. Filters for actionable roles: `button`, `link`, `textbox`, `combobox`, `checkbox`, `radio`, `menuitem`, `tab`.
3. Resolves each element to its visual bounding rectangle on screen.
4. Drops off-screen and invisible elements.
5. Injects ephemeral numeric badges (`[1]`, `[2]`, `[3]`) directly into the DOM or onto the visual canvas.
6. Emits a structured text summary that replaces large screenshots for the model prompt.

### 3. Reasoning Planner (`browserpilot.agent`)

The planner coordinates autonomous execution through an Observe, Reason, Act, Verify cycle:
1. **Observe**: Captures current page URL, page title, and the filtered accessibility tree.
2. **Reason**: Queries the configured language model (OpenAI, Anthropic Claude, Gemini, or local models). The model returns a structured JSON payload defining the next action and the rationale.
3. **Act**: Dispatches the action through the action executor. Keys are entered with randomized per-keystroke delays.
4. **Verify**: Inspects the page after the action to confirm that network requests have settled, DOM mutations occurred, or navigation completed. If an action fails, the verifier attempts fallback selectors or scrolls the viewport.

### 4. Human-in-the-Loop and Telemetry (`browserpilot.human`, `browserpilot.server`)

When bot challenges or authentication screens appear (such as Cloudflare Turnstile, reCAPTCHA, or two-factor code prompts), the heuristic detector flags the hurdle and halts the planner.

The telemetry server streams JPEG frames over WebSockets to the React 19 mission control dashboard. Operators can interact directly with the remote canvas using mouse clicks and keyboard input to solve the challenge. Once complete, the operator clicks Resume, returning control to the planner.
