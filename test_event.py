# test_event.py - Run separately to inspect WindowEvent
import asyncio
from app.core.tracker import WindowTracker

async def main():
    tracker = WindowTracker(idle_threshold=60.0)
    
    print("🔍 Inspecting WindowEvent structure...")
    async for event in tracker.track():
        print(f"\nType: {type(event)}")
        print(f"Repr: {repr(event)}")
        print(f"Attributes: {[a for a in dir(event) if not a.startswith('_')]}")
        
        if hasattr(event, '__dict__'):
            print(f"__dict__: {event.__dict__}")
        if hasattr(event, '__dataclass_fields__'):
            print(f"Dataclass fields: {event.__dataclass_fields__.keys()}")
        
        tracker.stop()
        break  # Just check first event

if __name__ == '__main__':
    asyncio.run(main())