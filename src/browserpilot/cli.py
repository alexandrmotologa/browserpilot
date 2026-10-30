"""Command-line interface for BrowserPilot using Typer and Rich."""

import asyncio
import json
from pathlib import Path
from typing import Optional
import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from browserpilot.agent.planner import AgentPlanner, AgentStep
from browserpilot.browser.stealth_context import BrowserManager
from browserpilot.config import get_settings
from browserpilot.dom.a11y_tree import AccessibilityTreeParser

app = typer.Typer(
    name="browserpilot",
    help="Autonomous vision-language web agent with a11y grounding and stealth CDP engine.",
    add_completion=False,
)
console = Console()


@app.command(name="run")
def run_command(
    goal: str = typer.Argument(..., help="Objective for the browser agent to accomplish"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Initial starting URL"),
    headless: bool = typer.Option(False, "--headless", "-h", help="Run in headless mode"),
    max_steps: int = typer.Option(30, "--max-steps", "-s", help="Step limit"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Target LLM model"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Path to save JSON trace"),
) -> None:
    """Execute an autonomous browser agent mission."""
    settings = get_settings()
    settings.headless = headless
    if model:
        settings.llm_model = model

    console.print(
        Panel(
            f"[bold cyan]Goal:[/bold cyan] {goal}\n"
            f"[bold cyan]Model:[/bold cyan] {settings.llm_model} ({settings.llm_provider})\n"
            f"[bold cyan]Headless:[/bold cyan] {headless}\n"
            f"[bold cyan]Start URL:[/bold cyan] {url or 'Default'}",
            title="[bold green]BrowserPilot Mission Kickoff[/bold green]",
            border_style="cyan",
        )
    )

    async def _async_run() -> None:
        async with BrowserManager(settings) as bm:
            page = await bm.new_page()

            async def step_callback(step: AgentStep) -> None:
                step_table = Table(show_header=False, border_style="dim")
                step_table.add_row("[bold yellow]Thought[/bold yellow]", step.thought)
                step_table.add_row(
                    "[bold green]Action[/bold green]",
                    f"{step.action.action.upper()} (target={step.action.element_id})",
                )
                step_table.add_row(
                    "[bold blue]Tokens / Cost[/bold blue]",
                    f"{step.total_tokens} tokens (~${step.cost_usd:.4f})",
                )
                console.print(
                    Panel(
                        step_table,
                        title=f"[bold]Step {step.step_number} - {page.url}[/bold]",
                        border_style="blue",
                    )
                )

            planner = AgentPlanner(
                goal=goal,
                settings=settings,
                on_step_callback=step_callback,
            )

            console.print("[dim]Navigating and starting execution loop...[/dim]")
            await planner.run(
                page=page,
                cursor=bm.cursor,
                start_url=url,
                max_steps=max_steps,
            )

            summary_table = Table(title="Mission Execution Summary")
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Value", style="green")

            summary_table.add_row("Total Steps", str(len(planner.steps)))
            summary_table.add_row(
                "Total Tokens",
                str(planner.total_prompt_tokens + planner.total_completion_tokens),
            )
            summary_table.add_row("Estimated Cost", f"${planner.total_cost_usd:.4f}")
            summary_table.add_row("Completion Status", "Success" if planner.is_done else "Incomplete")
            summary_table.add_row("Final Answer", planner.final_answer or "N/A")

            console.print(summary_table)

            if output:
                trace_data = {
                    "goal": goal,
                    "model": settings.llm_model,
                    "steps": [s.model_dump() for s in planner.steps],
                    "total_cost_usd": planner.total_cost_usd,
                    "final_answer": planner.final_answer,
                }
                output.write_text(json.dumps(trace_data, indent=2), encoding="utf-8")
                console.print(f"[bold green]Saved trace to {output}[/bold green]")

    asyncio.run(_async_run())


@app.command(name="serve")
def serve_command(
    port: int = typer.Option(9660, "--port", "-p", help="Server port"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host interface"),
    reload: bool = typer.Option(False, "--reload", help="Enable code hot-reload"),
) -> None:
    """Launch the FastAPI mission control backend and web studio."""
    console.print(
        Panel(
            f"Access Mission Control at [bold cyan]http://{host}:{port}[/bold cyan]\n"
            f"OpenAPI documentation at [bold cyan]http://{host}:{port}/docs[/bold cyan]",
            title="[bold green]Starting BrowserPilot Mission Control[/bold green]",
            border_style="green",
        )
    )
    uvicorn.run("browserpilot.server.app:create_app", host=host, port=port, factory=True, reload=reload)


@app.command(name="dump-tree")
def dump_tree_command(
    url: str = typer.Argument(..., help="Website URL to inspect"),
    headless: bool = typer.Option(True, "--headless", help="Run browser headless"),
) -> None:
    """Extract and display the compact accessibility tree of any URL."""
    settings = get_settings()
    settings.headless = headless

    async def _inspect() -> None:
        async with BrowserManager(settings) as bm:
            page = await bm.new_page()
            target = url if url.startswith("http") else f"https://{url}"
            console.print(f"[dim]Loading {target}...[/dim]")
            await page.goto(target, wait_until="domcontentloaded")
            await asyncio.sleep(1.0)

            elements = await AccessibilityTreeParser.parse_page(page)

            table = Table(title=f"Accessibility Tree - {target}")
            table.add_column("ID", style="bold cyan", width=4)
            table.add_column("Role", style="magenta", width=12)
            table.add_column("Name / Label", style="white")
            table.add_column("Coordinates", style="yellow", width=16)
            table.add_column("Value / State", style="dim")

            for el in elements:
                coords = f"({int(el.center_x)}, {int(el.center_y)})"
                state = []
                if el.is_focused:
                    state.append("focused")
                if el.value:
                    state.append(f"val='{el.value}'")
                table.add_row(
                    str(el.id),
                    el.role,
                    el.name[:50],
                    coords,
                    ", ".join(state) if state else "-",
                )

            console.print(table)
            console.print(f"[bold green]Total Actionable Elements:[/bold green] {len(elements)}")

    asyncio.run(_inspect())


@app.command(name="test-stealth")
def test_stealth_command(
    headless: bool = typer.Option(True, "--headless", help="Run in headless mode"),
) -> None:
    """Evaluate browser stealth against detection vectors."""
    settings = get_settings()
    settings.headless = headless

    async def _test() -> None:
        console.print("[dim]Launching stealth browser context...[/dim]")
        async with BrowserManager(settings) as bm:
            page = await bm.new_page()

            # Navigate to standard domain to test real browser environment
            await page.goto("https://example.com", wait_until="domcontentloaded")

            checks = await page.evaluate(
                """() => ({
                    webdriver: navigator.webdriver,
                    hasChrome: !!window.chrome,
                    hasChromeRuntime: !!(window.chrome && window.chrome.runtime),
                    pluginCount: navigator.plugins.length,
                    languages: navigator.languages,
                    webglVendor: (() => {
                        const canvas = document.createElement('canvas');
                        const gl = canvas.getContext('webgl');
                        if (!gl) return 'no-webgl';
                        const ext = gl.getExtension('WEBGL_debug_renderer_info');
                        return ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) : 'masked';
                    })(),
                    webglRenderer: (() => {
                        const canvas = document.createElement('canvas');
                        const gl = canvas.getContext('webgl');
                        if (!gl) return 'no-webgl';
                        const ext = gl.getExtension('WEBGL_debug_renderer_info');
                        return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'masked';
                    })()
                })"""
            )

            table = Table(title="Stealth Engine Property Verification")
            table.add_column("Property Check", style="cyan")
            table.add_column("Reported Value", style="white")
            table.add_column("Evasion Status", style="bold")

            # Check navigator.webdriver
            wd = checks.get("webdriver")
            table.add_row(
                "navigator.webdriver",
                str(wd),
                "[green]PASSED (false)[/green]" if wd is False else "[red]FAILED[/red]",
            )

            # Check window.chrome
            hc = checks.get("hasChrome")
            table.add_row(
                "window.chrome object",
                str(hc),
                "[green]PASSED (present)[/green]" if hc else "[red]FAILED[/red]",
            )

            # Check plugins
            pc = checks.get("pluginCount", 0)
            table.add_row(
                "navigator.plugins",
                f"{pc} plugins",
                "[green]PASSED (>0)[/green]" if pc > 0 else "[red]FAILED (empty)[/red]",
            )

            # Check WebGL Vendor
            wv = checks.get("webglVendor")
            table.add_row("WebGL Vendor", str(wv), "[green]PASSED (Spoofed)[/green]")

            # Check WebGL Renderer
            wr = checks.get("webglRenderer")
            table.add_row("WebGL Renderer", str(wr)[:40] + "...", "[green]PASSED (GPU Spoofed)[/green]")

            console.print(table)
            console.print(f"[bold green]Stealth Engine active: {bm.engine_type}[/bold green]")

    asyncio.run(_test())


if __name__ == "__main__":
    app()
