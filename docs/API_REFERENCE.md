# API and WebSocket Reference

BrowserPilot exposes an HTTP REST API and a real-time WebSocket endpoint on port 9660 by default.

## REST Endpoints

### Health and Status

#### `GET /api/health`
Returns runtime status, loaded model engine, and browser context availability.

**Response `200 OK`:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "browser_active": true,
  "stealth_engine": "patchright"
}
```

### Session Control

#### `POST /api/sessions/start`
Starts a new browser agent mission.

**Request Body:**
```json
{
  "goal": "Search for mechanical keyboards and open the first result",
  "start_url": "https://www.google.com",
  "model": "gpt-4o",
  "headless": false,
  "max_steps": 25,
  "stealth": true
}
```

**Response `200 OK`:**
```json
{
  "session_id": "sess_89f02a",
  "status": "running",
  "started_at": "2026-10-30T11:15:00Z"
}
```

#### `POST /api/sessions/pause`
Pauses the active execution loop.

**Response `200 OK`:**
```json
{
  "session_id": "sess_89f02a",
  "status": "paused"
}
```

#### `POST /api/sessions/resume`
Resumes an agent session that was paused by the user or triggered by a human-in-the-loop requirement.

**Response `200 OK`:**
```json
{
  "session_id": "sess_89f02a",
  "status": "running"
}
```

#### `POST /api/sessions/stop`
Terminates the session and closes the browser context.

#### `POST /api/sessions/approve`
Approves or modifies a pending action in Co-Pilot mode.

**Request Body (Optional):**
```json
{
  "modified_action": {
    "action": "click",
    "element_id": 14
  }
}
```

#### `GET /api/sessions/extracted-data`
Downloads structured dataset extracted by the agent. Accepts `?format=json` or `?format=csv`.

#### `GET /api/sessions/archive`
Returns summaries of all previously recorded agent missions.

#### `GET /api/sessions/archive/{session_id}`
Returns full execution trace for replay and analysis.

### Multi-Tab Management

#### `GET /api/tabs`
Returns list of all open browser tabs and active tab indicator.

#### `POST /api/tabs/switch?index=1`
Switches active tab to specified index.

#### `POST /api/tabs/new?url=https://example.com`
Opens and focuses a new tab.

#### `POST /api/tabs/close?index=1`
Closes specified or active tab.

### Profile and Cookie Persistence

#### `POST /api/profiles/save?name=amazon-auth`
Saves current session cookies and localStorage to disk.

#### `GET /api/profiles`
Lists available saved profile names.

#### `GET /api/sessions/history`
Returns the complete action log, reasoning trace, and token statistics for the current or specified session.

---

## WebSocket Telemetry and Remote Input

### Endpoint: `/ws/telemetry`

Provides two-way communication between the React 19 web dashboard and the Python agent runtime.

### Server to Client Events

#### `viewport_frame`
Transmits JPEG frames of the current browser viewport.
```json
{
  "type": "viewport_frame",
  "data": "data:image/jpeg;base64,...",
  "timestamp": 1793361300.12
}
```

#### `step_update`
Broadcast whenever the planner finishes an Observe-Reason-Act-Verify cycle.
```json
{
  "type": "step_update",
  "step": 3,
  "observation": "Google Search homepage loaded with search input",
  "thought": "I need to type 'mechanical keyboards' into the search input box [2].",
  "action": {
    "type": "type",
    "element_id": 2,
    "text": "mechanical keyboards",
    "press_enter": true
  },
  "verified": true,
  "token_usage": {
    "prompt_tokens": 420,
    "completion_tokens": 65,
    "total_tokens": 485,
    "step_cost_usd": 0.0014
  }
}
```

#### `human_takeover_required`
Emitted when anti-bot challenges or authentication forms are detected.
```json
{
  "type": "human_takeover_required",
  "reason": "Cloudflare Turnstile challenge detected",
  "challenge_type": "turnstile"
}
```

### Client to Server Events

During human takeover, remote events are forwarded to the browser instance:

#### `mouse_event`
```json
{
  "type": "mouse_event",
  "event": "click",
  "x": 480,
  "y": 320
}
```

#### `keyboard_event`
```json
{
  "type": "keyboard_event",
  "event": "type",
  "text": "123456"
}
```

#### `resume_agent`
Signals that the human operator solved the challenge.
```json
{
  "type": "resume_agent"
}
```
