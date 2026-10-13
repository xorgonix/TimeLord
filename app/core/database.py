"""
SQLite database layer for event persistence.
All database operations use run.io_bound to avoid blocking the UI.
"""
import sqlite3
import asyncio
from pathlib import Path
from typing import Optional, List

from app.core.models import WindowEvent


DB_PATH = Path(__file__).parent.parent.parent / "timelord.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """
    Initialize the database schema.
    Creates tables if they don't exist.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_ts INTEGER NOT NULL,
            end_ts INTEGER,
            app_name TEXT NOT NULL,
            window_title TEXT,
            process_id INTEGER,
            is_idle BOOLEAN DEFAULT 0,
            project_tag TEXT
        )
    """)
    
    # Create settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Insert default settings
    cursor.execute("""
        INSERT OR IGNORE INTO settings (key, value) VALUES 
        ('idle_threshold', '60'),
        ('theme', 'light'),
        ('version', '1.0.0')
    """)
    
    conn.commit()
    conn.close()


async def save_event(event: WindowEvent) -> int:
    """
    Save a window event to the database.
    Uses run.io_bound to avoid blocking the UI.
    
    Args:
        event: The WindowEvent to save.
        
    Returns:
        The ID of the inserted row.
    """
    def _insert():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (start_ts, end_ts, app_name, window_title, process_id, is_idle)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            int(event.start_time * 1000),  # Convert to milliseconds
            int(event.end_time * 1000) if event.end_time else None,
            event.process_name,
            event.window_title,
            event.process_id,
            1 if event.is_idle else 0
        ))
        row_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return row_id
    
    return await asyncio.to_thread(_insert)


async def update_event_end_time(event_id: int, end_time: float):
    """
    Update the end time of an existing event.
    
    Args:
        event_id: The ID of the event to update.
        end_time: The new end time (Unix timestamp).
    """
    def _update():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE events SET end_ts = ? WHERE id = ?
        """, (int(end_time * 1000), event_id))
        conn.commit()
        conn.close()
    
    await asyncio.to_thread(_update)


async def get_events_by_date(date_start: float, date_end: float) -> List[dict]:
    """
    Get all events within a date range.
    
    Args:
        date_start: Start Unix timestamp (ms).
        date_end: End Unix timestamp (ms).
        
    Returns:
        List of event dictionaries.
    """
    def _query():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, start_ts, end_ts, app_name, window_title, process_id, is_idle, project_tag
            FROM events
            WHERE start_ts >= ? AND start_ts <= ?
            ORDER BY start_ts ASC
        """, (int(date_start), int(date_end)))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    return await asyncio.to_thread(_query)


async def get_active_event() -> Optional[dict]:
    """
    Get the currently active event (no end_time).
    
    Returns:
        Event dictionary or None if no active event.
    """
    def _query():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, start_ts, end_ts, app_name, window_title, process_id, is_idle, project_tag
            FROM events
            WHERE end_ts IS NULL
            ORDER BY start_ts DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    return await asyncio.to_thread(_query)


async def close_active_event(end_time: float) -> Optional[int]:
    """
    Close any active events by setting their end_time.
    
    Args:
        end_time: The end time to set.
        
    Returns:
        The ID of the closed event, or None if no active event.
    """
    def _update():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE events SET end_ts = ? WHERE end_ts IS NULL
        """, (int(end_time * 1000),))
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        return row_id
    
    return await asyncio.to_thread(_update)


async def get_setting(key: str) -> Optional[str]:
    """
    Get a setting value by key.
    
    Args:
        key: The setting key.
        
    Returns:
        The setting value or None if not found.
    """
    def _query():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row['value'] if row else None
    
    return await asyncio.to_thread(_query)


async def set_setting(key: str, value: str):
    """
    Set a setting value.
    
    Args:
        key: The setting key.
        value: The setting value.
    """
    def _update():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
        """, (key, value))
        conn.commit()
        conn.close()
    
    await asyncio.to_thread(_update)


async def get_today_summary() -> dict:
    """
    Get a summary of today's activity.
    
    Returns:
        Dictionary with total time, top apps, etc.
    """
    def _query():
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get start of today (midnight)
        import time
        today_start = int(time.time() * 1000) - (int(time.time() * 1000) % 86400000)
        
        # Total active time today (excluding idle)
        cursor.execute("""
            SELECT 
                SUM(end_ts - start_ts) as total_time,
                COUNT(*) as event_count
            FROM events
            WHERE start_ts >= ? AND is_idle = 0
        """, (today_start,))
        row = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_time_ms': row['total_time'] or 0,
            'event_count': row['event_count'] or 0
        }
    
    return await asyncio.to_thread(_query)
