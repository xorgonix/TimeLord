"""Database queries for time aggregation and reporting."""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict

def get_db_connection():
    """Get database connection."""
    return sqlite3.connect('timelord.db')

def get_daily_events(date: str) -> List[Dict[str, Any]]:
    """
    Get all events for a specific day.
    date: YYYY-MM-DD format
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Convert date to timestamp range
    start_dt = datetime.strptime(date, '%Y-%m-%d')
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int((start_dt + timedelta(days=1)).timestamp() * 1000)
    
    cursor.execute('''
        SELECT id, app_name, window_title, start_ts, end_ts, is_idle, project_tag
        FROM events
        WHERE start_ts >= ? AND start_ts < ?
        ORDER BY start_ts ASC
    ''', (start_ts, end_ts))
    
    events = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return events

def get_monthly_summary(year: int, month: int) -> Dict[str, Any]:
    """
    Get monthly summary with daily totals and app breakdown.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate month boundaries
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    start_ts = int(start_date.timestamp() * 1000)
    end_ts = int(end_date.timestamp() * 1000)
    
    # Get all events for the month
    cursor.execute('''
        SELECT app_name, start_ts, end_ts, is_idle
        FROM events
        WHERE start_ts >= ? AND start_ts < ?
        ORDER BY start_ts ASC
    ''', (start_ts, end_ts))
    
    events = cursor.fetchall()
    conn.close()
    
    # Aggregate by day
    daily_totals = defaultdict(lambda: {'total_ms': 0, 'apps': defaultdict(int)})
    
    # Aggregate by app
    app_totals = defaultdict(int)
    
    for app_name, start_ts, end_ts, is_idle in events:
        if is_idle:
            continue
        
        # Calculate duration
        if end_ts:
            duration_ms = end_ts - start_ts
        else:
            duration_ms = 0
        
        # Convert timestamp to date string (YYYY-MM-DD)
        event_date = datetime.fromtimestamp(start_ts / 1000).strftime('%Y-%m-%d')
        
        # Aggregate
        daily_totals[event_date]['total_ms'] += duration_ms
        daily_totals[event_date]['apps'][app_name] += duration_ms
        app_totals[app_name] += duration_ms
    
    return {
        'year': year,
        'month': month,
        'daily_totals': dict(daily_totals),
        'app_totals': dict(app_totals),
        'total_events': len(events)
    }

def get_app_statistics(days: int = 7) -> List[Dict[str, Any]]:
    """
    Get app usage statistics for the last N days.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate date range
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days)
    
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    
    cursor.execute('''
        SELECT 
            app_name,
            COUNT(*) as event_count,
            SUM(CASE WHEN end_ts IS NOT NULL THEN end_ts - start_ts ELSE 0 END) as total_ms,
            MIN(start_ts) as first_seen,
            MAX(end_ts) as last_seen
        FROM events
        WHERE start_ts >= ? AND start_ts < ? AND is_idle = 0
        GROUP BY app_name
        ORDER BY total_ms DESC
    ''', (start_ts, end_ts))
    
    stats = []
    for row in cursor.fetchall():
        app_name, event_count, total_ms, first_seen, last_seen = row
        stats.append({
            'app_name': app_name,
            'event_count': event_count,
            'total_ms': total_ms or 0,
            'total_hours': (total_ms or 0) / (1000 * 60 * 60),
            'first_seen': first_seen,
            'last_seen': last_seen
        })
    
    conn.close()
    return stats