import asyncio
import json

class Messenger:
    """Utility class to broadcast real-time updates from the pipeline to the backend.
    Uses asyncio.Queue and supports safe updates from synchronous threads."""
    def __init__(self):
        self.queue = asyncio.Queue()
        self.loop = None

    def set_loop(self, loop):
        """Sets the event loop used by the backend."""
        self.loop = loop

    def send(self, event_type: str, data: any):
        """Puts an event into the queue. Safe to call from sync threads."""
        event = {
            "type": event_type,
            "data": data
        }
        if self.loop and self.loop.is_running():
            # Use thread-safe way to put into async queue
            try:
                self.loop.call_soon_threadsafe(self.queue.put_nowait, event)
            except Exception:
                pass
        else:
            # Fallback for debugging (skip image data in console log)
            if event_type != "screenshot":
                print(f"[Messenger Fallback: {event_type}] {data}")

    async def get_updates(self):
        """Async generator that yields updates from the queue."""
        while True:
            update = await self.queue.get()
            yield json.dumps(update)
            self.queue.task_done()

# Global instance
pipeline_messenger = Messenger()
