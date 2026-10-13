"""
ActiveWindow Time Tracker - Main Entry Point
Fixed: Now properly displays dashboard with all controls
"""
from nicegui import ui, background_tasks, app
from app.core.tracker import WindowTracker
from app.core.database import init_database
from app.ui.dashboard import create_dashboard
# Temporarily disable calendar views until syntax is fully fixed
# from app.ui.calendar_views import daily_timeline_page, monthly_calendar_page, statistics_page

# Global tracker
tracker = WindowTracker(idle_threshold=60.0)

# UI state: ONLY JSON-serializable primitives (NO functions!)
ui_state = {
    "tracking": False,
    "event_count": 0,
    "last_process": "None",
    "last_title": "None",
}

def main():
    @app.on_startup
    async def startup():
        print("🚀 APP STARTUP")
        init_database()
        print("✅ Database initialized")

        async def tracking_loop():
            print("🔍 TRACKING LOOP STARTED")
            ui_state["tracking"] = True

            try:
                async for event in tracker.track():
                    process_name = getattr(event, "process_name", "Unknown") or "Unknown"
                    window_title = getattr(event, "window_title", "") or ""

                    ui_state["event_count"] += 1
                    ui_state["last_process"] = str(process_name)[:40]
                    ui_state["last_title"] = str(window_title)[:50]

                    print(f"💾 Event #{ui_state['event_count']}: {process_name}")

            except Exception as e:
                print(f"❌ Tracking error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                ui_state["tracking"] = False

        background_tasks.create(tracking_loop())

    @app.on_shutdown
    def shutdown():
        print("🛑 APP SHUTDOWN")
        tracker.stop()

    @ui.page("/")
    def index():
        # ✅ MAIN HEADER
        ui.label("⏱ ActiveWindow Time Tracker").classes("text-2xl font-bold")

        # ✅ DEBUG PANEL (keep for testing)
        with ui.card().classes("w-full bg-green-100 mt-4"):
            ui.label("🛠 DEBUG STATUS").classes("text-bold")

            status_label = ui.label("Tracking: ❓")
            count_label = ui.label("Events: 0")
            process_label = ui.label("Process: None")

            def manual_refresh():
                count_label.set_text(f"Events: {ui_state['event_count']}")
                process_label.set_text(f"Process: {ui_state['last_process']}")
                ui.notify("Data refreshed!")

            ui.button("🔄 Refresh", on_click=manual_refresh).classes("mt-2")

            def auto_update():
                status_label.set_text(
                    f"Tracking: {'✅ ACTIVE' if ui_state['tracking'] else '❌ STOPPED'}"
                )
                status_label.classes("text-green" if ui_state["tracking"] else "text-red")
                count_label.set_text(f"Events: {ui_state['event_count']}")
                process_label.set_text(f"Process: {ui_state['last_process']}")

            ui.timer(2.0, auto_update)  # ✅ Function call, NOT decorator

        # ✅ CALL THE DASHBOARD - This was MISSING!
        ui.label("📊 Dashboard").classes("text-xl font-bold mt-6")
        create_dashboard()  # ← This line displays stats cards + timeline grid

        # ✅ OPTIONAL: Add navigation to calendar views (when fixed)
        with ui.row().classes("w-full gap-4 mt-4"):
            ui.button("📅 Daily View", on_click=lambda: ui.navigate.to("/daily")).props("outline")
            ui.button("📆 Monthly View", on_click=lambda: ui.navigate.to("/monthly")).props("outline")
            ui.button("📈 Statistics", on_click=lambda: ui.navigate.to("/stats")).props("outline")

    # Run with window visible
    ui.run(
        title="ActiveWindow Time Tracker",
        native=True,
        window_size=(1200, 800),  # Slightly larger for dashboard
        storage_secret="timelord-secret-key",
        show=True,
    )

if __name__ in {"__main__", "__mp_main__"}:
    main()
