"""
Agent Event Bus
===============
In-memory pub/sub event bus supporting SSE (Server-Sent Events) streaming
and in-memory buffer replay for real-time agent log activity.
"""

import asyncio
import json
import time
from collections import deque
from typing import Any, AsyncGenerator, Dict, List, Optional


class AgentEventBus:
    """Manages real-time log event streaming to frontend via SSE."""

    def __init__(self, max_history: int = 200):
        self._history: deque[Dict[str, Any]] = deque(maxlen=max_history)
        self._subscribers: set[asyncio.Queue] = set()

    def publish(
        self,
        event_type: str,
        message: str,
        level: str = "INFO",
        correlation_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Publish an event to all connected SSE clients and add to history."""
        event = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": level.upper(),
            "event": event_type,
            "message": message,
            "correlation_id": correlation_id or "system",
            "data": data or {},
        }
        self._history.append(event)

        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except Exception:
                pass
        return event

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the most recent buffered events."""
        items = list(self._history)
        return items[-limit:] if len(items) > limit else items

    async def subscribe(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Subscribe to the event bus stream."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        try:
            # Yield history first
            for past_event in self.get_recent_events(30):
                yield past_event

            while True:
                event = await q.get()
                yield event
        finally:
            self._subscribers.discard(q)


# Global event bus instance
event_bus = AgentEventBus()
