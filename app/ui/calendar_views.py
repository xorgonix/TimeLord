"""Calendar and timeline visualization pages."""

from datetime import datetime, timedelta

from nicegui import ui

from app.core.queries import get_app_statistics, get_daily_events, get_monthly_summary


def format_duration(ms: int) -> str:
    """Format milliseconds to human-readable duration."""
    if not ms:
        return "0m"

    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


@ui.page("/daily")
def daily_timeline_page():
    """Daily timeline view showing app usage throughout the day."""

    # Default to today
    selected_date = ui.date().props("landscape")

    with ui.column().classes("w-full gap-4 p-4"):
        ui.label("📅 Daily Timeline").classes("text-2xl font-bold")

        # Date selector
        with ui.row().classes("w-full items-center gap-4"):
            date_input = ui.input("Date", placeholder="YYYY-MM-DD").classes("w-48")
            today_btn = ui.button(
                "Today",
                on_click=lambda: date_input.set_value(
                    datetime.now().strftime("%Y-%m-%d")
                ),
            )
            load_btn = ui.button("Load", on_click=lambda: refresh_timeline())

        # Timeline container
        timeline_container = ui.column().classes("w-full")

        def refresh_timeline():
            """Load and display timeline for selected date."""
            timeline_container.clear()

            date_str = date_input.value or datetime.now().strftime("%Y-%m-%d")

            try:
                events = get_daily_events(date_str)

                if not events:
                    with timeline_container:
                        ui.label(f"No data for {date_str}").classes("text-gray-500")
                    return

                # Display events as timeline
                with timeline_container:
                    ui.label(f"📊 {date_str} - {len(events)} events").classes(
                        "text-lg font-bold mb-2"
                    )

                    # Calculate total time
                    total_ms = sum(
                        (e["end_ts"] - e["start_ts"]) if e["end_ts"] else 0
                        for e in events
                        if not e["is_idle"]
                    )
                    ui.label(f"Total active time: {format_duration(total_ms)}").classes(
                        "text-sm text-gray-600 mb-4"
                    )

                    # Show events
                    for event in events:
                        start_time = datetime.fromtimestamp(
                            event["start_ts"] / 1000
                        ).strftime("%H:%M")
                        end_time = (
                            datetime.fromtimestamp(event["end_ts"] / 1000).strftime(
                                "%H:%M"
                            )
                            if event["end_ts"]
                            else "Now"
                        )

                        duration = format_duration(
                            (event["end_ts"] - event["start_ts"])
                            if event["end_ts"]
                            else 0
                        )

                        status_icon = "😴" if event["is_idle"] else "🖥️"
                        color_class = (
                            "bg-gray-100" if event["is_idle"] else "bg-blue-50"
                        )

                        with ui.card().classes(f"w-full {color_class} p-2"):
                            with ui.row().classes("w-full items-center"):
                                ui.label(status_icon).classes("text-lg")
                                ui.label(f"{event['app_name']}").classes(
                                    "font-bold flex-1"
                                )  # ← Added }
                                ui.label(f"{start_time} - {end_time}").classes(
                                    "text-sm text-gray-600"
                                )
                                ui.label(duration).classes(
                                    "text-sm font-mono bg-white px-2 rounded"
                                )

                            if (
                                event["window_title"]
                                and event["window_title"] != event["app_name"]
                            ):
                                ui.label(event["window_title"][:100]).classes(
                                    "text-xs text-gray-500 ml-8"
                                )

            except Exception as e:
                with timeline_container:
                    ui.label(f"Error loading data: {e}").classes("text-red")

        # Load today by default
        date_input.set_value(datetime.now().strftime("%Y-%m-%d"))
        refresh_timeline()


@ui.page("/monthly")
def monthly_calendar_page():
    """Monthly view with calendar and app totals."""

    with ui.column().classes("w-full gap-4 p-4"):
        ui.label("📆 Monthly Summary").classes("text-2xl font-bold")

        # Month selector
        with ui.row().classes("w-full items-center gap-4"):
            year_input = ui.number("Year", value=datetime.now().year).classes("w-24")
            month_input = ui.number(
                "Month", value=datetime.now().month, min=1, max=12
            ).classes("w-24")
            load_btn = ui.button("Load Month", on_click=lambda: refresh_monthly())

        # Calendar grid
        calendar_grid = ui.grid(columns=7).classes("w-full")

        # App statistics table
        stats_container = ui.column().classes("w-full")

        def refresh_monthly():
            """Load and display monthly summary."""
            calendar_grid.clear()
            stats_container.clear()

            try:
                year = int(year_input.value)
                month = int(month_input.value)

                summary = get_monthly_summary(year, month)

                # Display calendar header
                month_name = datetime(year, month, 1).strftime("%B %Y")
                ui.label(f"📅 {month_name}").classes(
                    "text-xl font-bold col-span-7 text-center"
                )

                # Day headers
                for day_name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                    ui.label(day_name).classes("font-bold text-center p-2 bg-gray-200")

                # Calculate days in month
                if month == 12:
                    next_month = datetime(year + 1, 1, 1)
                else:
                    next_month = datetime(year, month + 1, 1)

                days_in_month = (next_month - datetime(year, month, 1)).days

                # Get first day of month (0=Monday, 6=Sunday)
                first_day = datetime(year, month, 1).weekday()

                # Empty cells before first day
                for _ in range(first_day):
                    ui.label("").classes("p-2")

                # Day cells
                for day in range(1, days_in_month + 1):
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    day_data = summary["daily_totals"].get(date_str, {"total_ms": 0})

                    total_ms = day_data["total_ms"]
                    total_hours = total_ms / (1000 * 60 * 60)

                    # Color intensity based on usage
                    if total_hours > 8:
                        color = "bg-green-500"
                    elif total_hours > 4:
                        color = "bg-green-300"
                    elif total_hours > 0:
                        color = "bg-green-100"
                    else:
                        color = "bg-gray-100"

                    with ui.card().classes(f"p-2 {color} min-h-[80px]"):
                        ui.label(f"{day}").classes("font-bold text-sm")
                        if total_ms > 0:
                            ui.label(f"{format_duration(total_ms)}").classes("text-xs")

                # App statistics
                with stats_container:
                    ui.label("📊 App Usage Totals").classes("text-xl font-bold mt-6")

                    # Sort apps by total time
                    sorted_apps = sorted(
                        summary["app_totals"].items(), key=lambda x: x[1], reverse=True
                    )

                    # Total time
                    total_ms = sum(summary["app_totals"].values())
                    ui.label(
                        f"Total tracked time: {format_duration(total_ms)}"
                    ).classes("text-lg mb-4")

                    # App table
                    columns = [
                        {"name": "app", "label": "Application", "field": "app"},
                        {"name": "hours", "label": "Hours", "field": "hours"},
                        {"name": "percentage", "label": "%", "field": "percentage"},
                    ]

                    rows = []
                    for app_name, app_ms in sorted_apps:
                        percentage = (app_ms / total_ms * 100) if total_ms > 0 else 0
                        rows.append(
                            {
                                "app": app_name,
                                "hours": f"{format_duration(app_ms)}",
                                "percentage": f"{percentage:.1f}%",
                            }
                        )

                    ui.table(columns=columns, rows=rows, row_key="app").classes(
                        "w-full"
                    )

            except Exception as e:
                ui.label(f"Error loading data: {e}").classes("text-red")

        # Load current month by default
        refresh_monthly()


# In calendar_views.py
@ui.page("/calendar-full")
def full_calendar_page():
    """Interactive calendar using FullCalendar.js."""

    ui.add_head_html("""
    <script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.9/index.global.min.js'></script>
    <style>
        #calendar { max-width: 1100px; margin: 0 auto; }
    </style>
    """)

    ui.label("📅 Interactive Calendar").classes("text-2xl font-bold")

    # Calendar container
    calendar_div = ui.element("div").classes("w-full")
    calendar_div._props["id"] = "calendar"

    # Initialize FullCalendar
    ui.run_javascript("""
    document.addEventListener('DOMContentLoaded', function() {
        var calendarEl = document.getElementById('calendar');
        var calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            },
            events: async function(info, successCallback, failureCallback) {
                // Fetch events from backend
                const response = await fetch('/api/calendar-events?start=' + info.startStr + '&end=' + info.endStr);
                const events = await response.json();
                successCallback(events);
            },
            dateClick: function(info) {
                // Navigate to daily view
                window.location.href = '/daily?date=' + info.dateStr;
            }
        });
        calendar.render();
    });
    """)


@ui.page("/stats")
def statistics_page():
    """Application statistics and insights."""

    with ui.column().classes("w-full gap-4 p-4"):
        ui.label("📈 Application Statistics").classes("text-2xl font-bold")

        # Days selector
        days_input = ui.number("Days", value=7, min=1, max=90).classes("w-24")
        refresh_btn = ui.button("Refresh", on_click=lambda: refresh_stats())

        # Stats container
        stats_container = ui.column().classes("w-full")

        def refresh_stats():
            """Load and display statistics."""
            stats_container.clear()

            try:
                days = int(days_input.value)
                stats = get_app_statistics(days)

                with stats_container:
                    ui.label(f"Last {days} days").classes("text-lg mb-4")

                    if not stats:
                        ui.label("No data available").classes("text-gray-500")
                        return

                    # Summary cards
                    with ui.row().classes("w-full gap-4"):
                        with ui.card().classes("flex-1").props("flat bordered"):
                            ui.label("Total Apps").classes("text-2xl font-bold")
                            ui.label(str(len(stats))).classes("text-gray-600")

                        total_hours = sum(s["total_hours"] for s in stats)
                        with ui.card().classes("flex-1").props("flat bordered"):
                            ui.label("Total Hours").classes("text-2xl font-bold")
                            ui.label(f"{total_hours:.1f}h").classes("text-gray-600")

                    # Detailed table
                    columns = [
                        {"name": "app", "label": "Application", "field": "app"},
                        {"name": "hours", "label": "Total Time", "field": "hours"},
                        {"name": "events", "label": "Sessions", "field": "events"},
                        {"name": "avg", "label": "Avg Session", "field": "avg"},
                    ]

                    rows = []
                    for s in stats:
                        avg_session = (
                            s["total_hours"] / s["event_count"]
                            if s["event_count"] > 0
                            else 0
                        )
                        rows.append(
                            {
                                "app": s["app_name"],
                                "hours": f"{s['total_hours']:.2f}h",
                                "events": s["event_count"],
                                "avg": f"{avg_session * 60:.0f}m",  # Convert to minutes
                            }
                        )

                    ui.table(columns=columns, rows=rows, row_key="app").classes(
                        "w-full mt-4"
                    )

                    # Future: Add chart here
                    # ui.echart({...})

            except Exception as e:
                ui.label(f"Error loading data: {e}").classes("text-red")

        refresh_stats()
