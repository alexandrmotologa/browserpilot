"""REST and WebSocket endpoints for session control, live inspection, and telemetry."""

import asyncio
import logging
from typing import Any
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from browserpilot.agent.planner import AgentPlanner, AgentStep
from browserpilot.browser.stealth_context import BrowserManager
from browserpilot.config import get_settings
from browserpilot.dom.a11y_tree import AccessibilityTreeParser
from browserpilot.human.stream_relay import StreamRelay
from browserpilot.server.ws_telemetry import telemetry_hub

logger = logging.getLogger("browserpilot.server.routes")
router = APIRouter()


class ServerState:
    """Singleton holding active browser and agent session instances."""

    browser_manager: BrowserManager | None = None
    planner: AgentPlanner | None = None
    relay: StreamRelay | None = None
    runner_task: asyncio.Task[Any] | None = None


state = ServerState()


class StartSessionRequest(BaseModel):
    """Payload for initiating a new browser agent mission."""

    goal: str = Field(description="Objective to accomplish")
    start_url: str | None = Field(default=None, description="Initial website URL")
    model: str | None = Field(default=None, description="LLM model override")
    max_steps: int | None = Field(default=30, description="Step limit")
    headless: bool | None = Field(default=None, description="Headless mode flag")


class SessionStatusResponse(BaseModel):
    """Current state of the agent mission."""

    session_id: str | None = None
    status: str
    goal: str = ""
    total_steps: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    takeover_required: bool = False
    final_answer: str | None = None


@router.get("/api/health")
async def health_check() -> dict[str, Any]:
    """Return backend health status and active engine metadata."""
    settings = get_settings()
    return {
        "status": "healthy",
        "version": "0.1.0",
        "browser_active": state.browser_manager is not None,
        "engine_type": state.browser_manager.engine_type if state.browser_manager else "none",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }


@router.post("/api/sessions/start", response_model=SessionStatusResponse)
async def start_session(req: StartSessionRequest) -> SessionStatusResponse:
    """Launch a new autonomous agent mission."""
    settings = get_settings()

    # Clean up previous session if running
    if state.runner_task and not state.runner_task.done():
        if state.planner:
            await state.planner.stop()
        state.runner_task.cancel()

    if state.browser_manager is None:
        state.browser_manager = BrowserManager(settings)
        await state.browser_manager.launch()
        await state.browser_manager.new_page()

    page = state.browser_manager.active_page
    cursor = state.browser_manager.cursor

    # Initialize streaming relay
    state.relay = StreamRelay(page_provider=lambda: state.browser_manager.active_page if state.browser_manager else None)

    async def broadcast_frame(b64_frame: str) -> None:
        await telemetry_hub.broadcast({
            "type": "viewport_frame",
            "frame": b64_frame,
        })

    state.relay.subscribe(broadcast_frame)
    await state.relay.start_stream(fps=6.0)

    # Step callback broadcaster
    async def on_step(step: AgentStep) -> None:
        await telemetry_hub.broadcast({
            "type": "step_update",
            "step": step.model_dump(),
        })

    async def on_takeover(challenge_type: str) -> None:
        await telemetry_hub.broadcast({
            "type": "human_takeover_required",
            "challenge_type": challenge_type,
        })

    state.planner = AgentPlanner(
        goal=req.goal,
        settings=settings,
        on_step_callback=on_step,
        on_takeover_callback=on_takeover,
    )

    async def _execute_mission() -> None:
        try:
            await state.planner.run(
                page=page,
                cursor=cursor,
                start_url=req.start_url,
                max_steps=req.max_steps,
            )
            await telemetry_hub.broadcast({
                "type": "session_completed",
                "final_answer": state.planner.final_answer,
                "total_steps": len(state.planner.steps),
                "total_cost_usd": state.planner.total_cost_usd,
            })
        except Exception as ex:
            logger.error(f"Mission execution error: {ex}", exc_info=True)
            await telemetry_hub.broadcast({
                "type": "session_error",
                "error": str(ex),
            })

    state.runner_task = asyncio.create_task(_execute_mission())

    return SessionStatusResponse(
        session_id=state.planner.session_id,
        status="running",
        goal=req.goal,
        total_steps=0,
        total_tokens=0,
        total_cost_usd=0.0,
        takeover_required=False,
    )


@router.post("/api/sessions/pause")
async def pause_session() -> dict[str, str]:
    """Pause the running agent loop."""
    if not state.planner:
        raise HTTPException(status_code=400, detail="No active session found")
    await state.planner.pause()
    await telemetry_hub.broadcast({"type": "session_paused"})
    return {"status": "paused"}


@router.post("/api/sessions/resume")
async def resume_session() -> dict[str, str]:
    """Resume a paused agent session after user intervention."""
    if not state.planner:
        raise HTTPException(status_code=400, detail="No active session found")
    await state.planner.resume()
    await telemetry_hub.broadcast({"type": "session_resumed"})
    return {"status": "resumed"}


@router.post("/api/sessions/stop")
async def stop_session() -> dict[str, str]:
    """Abort the active mission."""
    if state.planner:
        await state.planner.stop()
    if state.runner_task and not state.runner_task.done():
        state.runner_task.cancel()
    await telemetry_hub.broadcast({"type": "session_stopped"})
    return {"status": "stopped"}


@router.get("/api/sessions/status", response_model=SessionStatusResponse)
async def get_status() -> SessionStatusResponse:
    """Query current session status and token statistics."""
    if not state.planner:
        return SessionStatusResponse(status="idle")

    status = "running"
    if state.planner.is_done:
        status = "completed"
    elif state.planner.is_paused:
        status = "paused"
    elif state.planner.is_stopped:
        status = "stopped"

    return SessionStatusResponse(
        session_id=state.planner.session_id,
        status=status,
        goal=state.planner.goal,
        total_steps=len(state.planner.steps),
        total_tokens=state.planner.total_prompt_tokens + state.planner.total_completion_tokens,
        total_cost_usd=state.planner.total_cost_usd,
        takeover_required=state.planner.takeover_required,
        final_answer=state.planner.final_answer,
    )


@router.get("/api/sessions/history")
async def get_history() -> list[dict[str, Any]]:
    """Retrieve full step history of the current mission."""
    if not state.planner:
        return []
    return [s.model_dump() for s in state.planner.steps]


@router.get("/api/dom/tree")
async def get_dom_tree() -> list[dict[str, Any]]:
    """Return parsed accessibility tree elements of the active browser page."""
    if not state.browser_manager or not state.browser_manager.active_page:
        raise HTTPException(status_code=400, detail="Browser is not active")

    elements = await AccessibilityTreeParser.parse_page(state.browser_manager.active_page)
    return [el.model_dump() for el in elements]


@router.websocket("/ws/telemetry")
async def ws_telemetry_endpoint(websocket: WebSocket) -> None:
    """Bi-directional WebSocket for streaming frames and receiving operator input."""
    await telemetry_hub.connect(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if not state.relay:
                continue

            if msg_type == "mouse_click":
                await state.relay.handle_remote_click(
                    x=float(data.get("x", 0)),
                    y=float(data.get("y", 0)),
                    button=data.get("button", "left"),
                )
            elif msg_type == "mouse_move":
                await state.relay.handle_remote_move(
                    x=float(data.get("x", 0)),
                    y=float(data.get("y", 0)),
                )
            elif msg_type == "mouse_scroll":
                await state.relay.handle_remote_scroll(
                    delta_x=float(data.get("delta_x", 0)),
                    delta_y=float(data.get("delta_y", 0)),
                )
            elif msg_type == "keyboard_type":
                await state.relay.handle_remote_type(str(data.get("text", "")))
            elif msg_type == "keyboard_press":
                await state.relay.handle_remote_press(str(data.get("key", "Enter")))
            elif msg_type == "resume_agent" and state.planner:
                await state.planner.resume()
                await telemetry_hub.broadcast({"type": "session_resumed"})
            elif msg_type == "pause_agent" and state.planner:
                await state.planner.pause()
                await telemetry_hub.broadcast({"type": "session_paused"})
            elif msg_type == "stop_agent" and state.planner:
                await state.planner.stop()
                await telemetry_hub.broadcast({"type": "session_stopped"})

    except WebSocketDisconnect:
        await telemetry_hub.disconnect(websocket)
    except Exception as ex:
        logger.debug(f"WebSocket connection exception: {ex}")
        await telemetry_hub.disconnect(websocket)
