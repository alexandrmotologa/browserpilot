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
