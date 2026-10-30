"""REST and WebSocket endpoints for session control, multi-tab inspection, co-pilot approval, and telemetry."""

import asyncio
import logging
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from browserpilot.agent.actions import ActionCommand
from browserpilot.agent.planner import AgentPlanner, AgentStep
from browserpilot.browser.stealth_context import BrowserManager
from browserpilot.config import get_settings
from browserpilot.dom.a11y_tree import AccessibilityTreeParser
from browserpilot.human.stream_relay import StreamRelay
from browserpilot.server.session_recorder import PROFILES_DIR, SessionArchiveManager
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
    co_pilot_mode: bool = Field(default=False, description="Enable Co-Pilot step-by-step approval mode")
    profile: str | None = Field(default=None, description="Saved profile name to load cookies/session state")


class ApproveStepRequest(BaseModel):
    """Payload for approving or modifying a proposed action in Co-Pilot mode."""

    modified_action: ActionCommand | None = None


class SessionStatusResponse(BaseModel):
    """Current state of the agent mission."""

    session_id: str | None = None
    status: str
    goal: str = ""
    total_steps: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    takeover_required: bool = False
    co_pilot_mode: bool = False
    awaiting_approval: bool = False
    final_answer: str | None = None
    has_extracted_data: bool = False


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
        "active_tabs": len(state.browser_manager.pages) if state.browser_manager else 0,
    }


@router.post("/api/sessions/start", response_model=SessionStatusResponse)
async def start_session(req: StartSessionRequest) -> SessionStatusResponse:
    """Launch a new autonomous or co-pilot browser agent mission."""
    settings = get_settings()

    # Clean up previous session if running
    if state.runner_task and not state.runner_task.done():
        if state.planner:
            await state.planner.stop()
        state.runner_task.cancel()

    # Determine profile path if requested
    profile_path = None
    if req.profile:
        candidate = PROFILES_DIR / f"{req.profile}.json"
        if candidate.exists():
            profile_path = candidate

    if state.browser_manager is None:
        state.browser_manager = BrowserManager(settings)
        await state.browser_manager.launch(storage_state_path=profile_path)
        await state.browser_manager.new_page()

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
        tabs = await state.browser_manager.get_tabs() if state.browser_manager else []
        await telemetry_hub.broadcast({
            "type": "step_update",
            "step": step.model_dump(),
            "tabs": tabs,
        })

    async def on_takeover(challenge_type: str) -> None:
        await telemetry_hub.broadcast({
            "type": "human_takeover_required",
            "challenge_type": challenge_type,
        })

    async def on_approval_required(step: AgentStep) -> None:
        await telemetry_hub.broadcast({
            "type": "step_awaiting_approval",
            "step": step.model_dump(),
        })

    state.planner = AgentPlanner(
        goal=req.goal,
        settings=settings,
        co_pilot_mode=req.co_pilot_mode,
        on_step_callback=on_step,
        on_takeover_callback=on_takeover,
        on_approval_callback=on_approval_required,
    )

    async def _execute_mission() -> None:
        try:
            target_page = state.browser_manager.active_page
            await state.planner.run(
                page=target_page,
                cursor=cursor,
                start_url=req.start_url,
                max_steps=req.max_steps,
                browser_manager=state.browser_manager,
            )

            # Automatically archive completed session
            SessionArchiveManager.save_session(
                session_id=state.planner.session_id,
                goal=state.planner.goal,
                steps=[s.model_dump() for s in state.planner.steps],
                total_tokens=state.planner.total_prompt_tokens + state.planner.total_completion_tokens,
                total_cost_usd=state.planner.total_cost_usd,
                final_answer=state.planner.final_answer,
                extracted_data=state.planner.extracted_data,
            )

            await telemetry_hub.broadcast({
                "type": "session_completed",
                "final_answer": state.planner.final_answer,
                "total_steps": len(state.planner.steps),
                "total_cost_usd": state.planner.total_cost_usd,
                "has_extracted_data": state.planner.extracted_data is not None,
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
        co_pilot_mode=req.co_pilot_mode,
        awaiting_approval=False,
    )


@router.post("/api/sessions/approve")
async def approve_step(req: ApproveStepRequest | None = None) -> dict[str, str]:
    """Approve or modify a proposed action in Co-Pilot mode."""
    if not state.planner or not state.planner.awaiting_approval:
        raise HTTPException(status_code=400, detail="No step currently awaiting approval")

    state.planner.approve_step(req.modified_action if req else None)
    await telemetry_hub.broadcast({"type": "step_approved"})
    return {"status": "approved"}


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
    """Query current session status, co-pilot state, and token statistics."""
    if not state.planner:
        return SessionStatusResponse(status="idle")

    status = "running"
    if state.planner.is_done:
        status = "completed"
    elif state.planner.awaiting_approval:
        status = "awaiting_approval"
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
        co_pilot_mode=state.planner.co_pilot_mode,
        awaiting_approval=state.planner.awaiting_approval,
        final_answer=state.planner.final_answer,
        has_extracted_data=state.planner.extracted_data is not None,
    )


@router.get("/api/sessions/history")
async def get_history() -> list[dict[str, Any]]:
    """Retrieve full step history of the current mission."""
    if not state.planner:
        return []
    return [s.model_dump() for s in state.planner.steps]


@router.get("/api/sessions/extracted-data")
async def get_extracted_data(format: str = Query(default="json", pattern="^(json|csv)$")) -> Any:
    """Download structured dataset extracted by the agent."""
    if not state.planner or not state.planner.extracted_data:
        raise HTTPException(status_code=404, detail="No structured dataset available in current session")

    data = state.planner.extracted_data
    if format == "csv" and isinstance(data, list):
        csv_str = SessionArchiveManager.export_csv(data)
        return Response(content=csv_str, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=extracted_data.csv"})

    return data


@router.get("/api/sessions/archive")
async def list_archives() -> list[dict[str, Any]]:
    """List all previously recorded agent missions for replay."""
    return SessionArchiveManager.list_archived_sessions()


@router.get("/api/sessions/archive/{session_id}")
async def get_archive(session_id: str) -> dict[str, Any]:
    """Retrieve full replay trace of a past mission."""
    trace = SessionArchiveManager.get_archived_session(session_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Archive for session {session_id} not found")
    return trace


# Multi-Tab Endpoints
@router.get("/api/tabs")
async def get_tabs() -> list[dict[str, Any]]:
    """Return all currently open browser tabs."""
    if not state.browser_manager:
        return []
    return await state.browser_manager.get_tabs()


@router.post("/api/tabs/switch")
async def switch_tab(index: int = Query(...)) -> dict[str, Any]:
    """Switch active tab to the specified index."""
    if not state.browser_manager:
        raise HTTPException(status_code=400, detail="Browser is not active")
    page = await state.browser_manager.switch_tab(index)
    tabs = await state.browser_manager.get_tabs()
    await telemetry_hub.broadcast({"type": "tabs_updated", "tabs": tabs})
    return {"status": "switched", "index": index, "url": page.url}


@router.post("/api/tabs/new")
async def new_tab(url: str | None = Query(default=None)) -> dict[str, Any]:
    """Create and focus a new browser tab."""
    if not state.browser_manager:
        raise HTTPException(status_code=400, detail="Browser is not active")
    page = await state.browser_manager.new_tab(url)
    tabs = await state.browser_manager.get_tabs()
    await telemetry_hub.broadcast({"type": "tabs_updated", "tabs": tabs})
    return {"status": "opened", "url": page.url}


@router.post("/api/tabs/close")
async def close_tab(index: int | None = Query(default=None)) -> dict[str, Any]:
    """Close active or targeted tab."""
    if not state.browser_manager:
        raise HTTPException(status_code=400, detail="Browser is not active")
    await state.browser_manager.close_tab(index)
    tabs = await state.browser_manager.get_tabs()
    await telemetry_hub.broadcast({"type": "tabs_updated", "tabs": tabs})
    return {"status": "closed"}


# Profile & Cookie Persistence Endpoints
@router.post("/api/profiles/save")
async def save_profile(name: str = Query(...)) -> dict[str, str]:
    """Save active browser cookies and localStorage state to profile file."""
    if not state.browser_manager:
        raise HTTPException(status_code=400, detail="Browser is not active")
    target = PROFILES_DIR / f"{name}.json"
    await state.browser_manager.save_storage_state(target)
    return {"status": "saved", "profile": name, "path": str(target)}


@router.get("/api/profiles")
async def list_profiles() -> list[str]:
    """List all available browser profiles with saved cookies."""
    if not PROFILES_DIR.exists():
        return []
    return [f.stem for f in PROFILES_DIR.glob("*.json")]


@router.get("/api/dom/tree")
async def get_dom_tree() -> list[dict[str, Any]]:
    """Return parsed accessibility tree elements of the active browser page."""
    if not state.browser_manager or not state.browser_manager.active_page:
        raise HTTPException(status_code=400, detail="Browser is not active")

    elements = await AccessibilityTreeParser.parse_page(state.browser_manager.active_page)
    return [el.model_dump() for el in elements]


@router.websocket("/ws/telemetry")
async def ws_telemetry_endpoint(websocket: WebSocket) -> None:
    """Bi-directional WebSocket for streaming frames, receiving input, and handling approval."""
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
            elif msg_type == "approve_step" and state.planner:
                state.planner.approve_step()
                await telemetry_hub.broadcast({"type": "step_approved"})
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
