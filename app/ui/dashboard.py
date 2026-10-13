"""
Dashboard UI components for the TimeLord application.
Uses NiceGUI advanced patterns: ui.aggrid, ui.card, @ui.refreshable
"""

import asyncio
import logging
from datetime import datetime, timedelta

from nicegui import ui

from app.core.database import get_active_event, get_events_by_date, get_today_summary

logger = logging.getLogger(__name__)


def format_timestamp(ts_ms: int) -> str:
    """Convert millisecond timestamp to readable format."""
    if ts_ms is None:
        return "--"
    try:
        dt = datetime.fromtimestamp(ts_ms / 1000)
        return dt.strftime("%H:%M:%S")
    except (ValueError, OSError):
        return "--"


def format_duration(ms: int) -> str:
    """Convert milliseconds to human-readable duration."""
    if ms is None or ms < 0:
        return "--"
    try:
        total_seconds = ms // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except:
        return "--"


# Global cache for current stats (avoids passing functions to UI)
_current_stats = {"total_time": "--", "event_count": 0, "current_app": "--"}


@ui.refreshable
def stats_cards():
    """
    Display summary statistics in card format.
    Uses @ui.refreshable for reactive updates.

    ✅ FIX: No parameters - fetch data inside the function
    """
    # Use cached stats to avoid async complexity in render function
    with ui.row().classes("w-full gap-4"):
        with ui.card().classes("flex-1 min-w-[200px]"):
            ui.label(_current_stats["total_time"]).classes(
                "text-2xl font-bold text-primary"
            )
            ui.label("Total Time Today").classes("text-body2 text-grey-7")

        with ui.card().classes("flex-1 min-w-[200px]"):
            ui.label(str(_current_stats["event_count"])).classes(
                "text-2xl font-bold text-primary"
            )
            ui.label("Tracked Events").classes("text-body2 text-grey-7")

        with ui.card().classes("flex-1 min-w-[200px]"):
            ui.label(_current_stats["current_app"][:30]).classes("text-lg font-medium")
            ui.label("Active Application").classes("text-body2 text-grey-7")


@ui.refreshable
def timeline_grid():
    """
    Display timeline data using AG Grid.
    High-performance grid for showing tracked events.

    ✅ FIX: No parameters - fetch data inside the function
    """
    # Column definitions for AG Grid
    column_defs = [
        {"field": "start_time", "headerName": "Start", "width": 90, "sortable": True},
        {"field": "end_time", "headerName": "End", "width": 90, "sortable": True},
        {"field": "duration", "headerName": "Duration", "width": 100, "sortable": True},
        {
            "field": "app_name",
            "headerName": "Application",
            "width": 150,
            "sortable": True,
            "filter": True,
        },
        {
            "field": "window_title",
            "headerName": "Window Title",
            "width": 300,
            "sortable": False,
        },
        {
            "field": "is_idle",
            "headerName": "Status",
            "width": 80,
            "sortable": True,
            "cellRenderer": lambda params: "😴 Idle" if params.value else "✓ Active",
        },
    ]

    # Fetch and format events
    try:
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        today_end = today_start + timedelta(days=1)

        start_ts = int(today_start.timestamp() * 1000)
        end_ts = int(today_end.timestamp() * 1000)

        # ✅ FIX: Use sync wrapper or ensure DB function is compatible
        events = get_events_by_date(start_ts, end_ts)

        row_data = []
        for event in events:
            # ✅ FIX: Safe attribute access (handle dict or object)
            if isinstance(event, dict):
                start_ts_e = event.get("start_ts")
                end_ts_e = event.get("end_ts")
                app_name = event.get("app_name", "Unknown")
                window_title = event.get("window_title", "")
                is_idle = event.get("is_idle", False)
            else:
                # Handle object case (WindowEvent dataclass)
                start_ts_e = getattr(event, "start_ts", None)
                end_ts_e = getattr(event, "end_ts", None)
                app_name = getattr(
                    event, "process_name", getattr(event, "app_name", "Unknown")
                )
                window_title = getattr(event, "window_title", "")
                is_idle = getattr(event, "is_idle", False)

            duration = (end_ts_e - start_ts_e) if end_ts_e and start_ts_e else 0

            row_data.append(
                {
                    "start_time": format_timestamp(start_ts_e),
                    "end_time": format_timestamp(end_ts_e) if end_ts_e else "--",
                    "duration": format_duration(duration),
                    "app_name": str(app_name)[:40],  # Truncate for display
                    "window_title": str(window_title)[:60],
                    "is_idle": bool(is_idle),
                }
            )

    except Exception as e:
        logger.error(f"Error loading timeline: {e}")
        row_data = []

    with ui.card().classes("w-full"):
        ui.label("Today's Timeline").classes("text-h6 mb-2")

        if row_data:
            # ✅ FIX: Ensure all values are JSON-serializable primitives
            ui.aggrid(
                {
                    "columnDefs": column_defs,
                    "rowData": row_data,  # List of dicts with str/int/bool values only
                    "defaultColDef": {"resizable": True},
                    "pagination": True,
                    "paginationPageSize": 20,
                }
            ).classes("w-full h-[400px]")
        else:
            with ui.column().classes("w-full h-[200px] items-center justify-center"):
                ui.icon("history", size="4em").classes("text-grey-5")
                ui.label("No events recorded yet").classes("text-body1 text-grey-7")
                ui.label("Start using your computer to begin tracking").classes(
                    "text-body2 text-grey-5"
                )


async def update_stats_cache():
    """
    Fetch fresh stats and update the global cache.
    Call this before refreshing stats_cards.
    """
    global _current_stats

    try:
        # ✅ FIX: Handle both sync and async DB functions
        summary = get_today_summary()
        active = get_active_event()

        # Handle if functions return coroutines
        if hasattr(summary, "__await__"):
            summary = await summary
        if hasattr(active, "__await__"):
            active = await active

        total_ms = summary.get("total_time_ms", 0) if isinstance(summary, dict) else 0
        hours = total_ms // 3600000
        minutes = (total_ms % 3600000) // 60000

        current_app = "--"
        if isinstance(active, dict) and active.get("app_name"):
            current_app = active["app_name"]
        elif active and hasattr(active, "process_name"):
            current_app = active.process_name

        _current_stats = {
            "total_time": f"{hours}h {minutes}m",
            "event_count": summary.get("event_count", 0)
            if isinstance(summary, dict)
            else 0,
            "current_app": str(current_app)[:30],
        }

    except Exception as e:
        logger.error(f"Error updating stats: {e}")
        # Keep existing values on error


async def load_dashboard_data():
    """
    Load all dashboard data and refresh UI components.
    ✅ FIX: Proper async handling for NiceGUI
    """
    await update_stats_cache()
    stats_cards.refresh()
    timeline_grid.refresh()


def create_dashboard():
    """
    Create the main dashboard page.
    Uses declarative UI with context managers.

    ✅ FIX: All timers use function call syntax, not decorator
    """

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4"):
        # Header
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("ActiveWindow Time Tracker").classes("text-h4")
            with ui.row():
                status_chip = ui.chip("● Tracking", color="green").props("outline")

                # ✅ FIX: Refresh button with proper async handling
                def on_refresh():
                    ui.notify("Refreshing...")
                    # NiceGUI handles async in button callbacks automatically
                    asyncio.create_task(load_dashboard_data())

                refresh_btn = ui.button(icon="refresh", on_click=on_refresh).props(
                    "round dense flat"
                )
                refresh_btn.tooltip("Refresh data")

        # Stats cards - will auto-update via timer
        stats_cards()

        # Timeline section
        timeline_grid()

        # ✅ FIX: Auto-refresh timer - function call syntax, NOT decorator
        async def auto_refresh():
            await load_dashboard_data()

        # Timer calls function every 10 seconds
        ui.timer(10.0, lambda: asyncio.create_task(auto_refresh()))

        # ✅ FIX: Initial load - once=True parameter, function call syntax
        ui.timer(0.5, lambda: asyncio.create_task(load_dashboard_data()), once=True)
