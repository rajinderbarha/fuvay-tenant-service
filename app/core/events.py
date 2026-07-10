"""
ServiceOS — Event Bus (Redis Pub/Sub)
Transactional outbox pattern: events are first written to the outbox table
in the same DB transaction as the business operation, then a background
worker publishes them to Redis. This guarantees delivery even on crash.

In Phase 1: publish/subscribe stubs are wired. Outbox worker added in Phase 3.
"""
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable
import uuid

import redis.asyncio as aioredis
import structlog

from app.config import get_settings

logger = structlog.get_logger("event_bus")


@dataclass
class DomainEvent:
    """Every domain event has this shape on the bus."""
    event_id: str
    event_type: str           # e.g. "job.status_changed"
    engine_id: str            # e.g. "field_ops"
    tenant_id: str
    actor_id: str | None
    entity_type: str          # e.g. "job"
    entity_id: str            # e.g. "JB-40921"
    payload: dict[str, Any]
    occurred_at: str          # ISO 8601

    @classmethod
    def create(
        cls,
        event_type: str,
        engine_id: str,
        tenant_id: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any],
        actor_id: str | None = None,
    ) -> "DomainEvent":
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            engine_id=engine_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            occurred_at=datetime.now(timezone.utc).isoformat(),
        )


class EventBus:
    """
    Thin wrapper around Redis pub/sub.
    Engines publish events; interested engines subscribe and react.

    Publishing flow (with outbox):
      1. Engine writes event to outbox_events table (same TX as business op)
      2. Outbox worker reads from table, publishes to Redis, marks as published
      3. Subscribers receive and process

    In Phase 1: direct publish (without outbox persistence). Outbox in Phase 3.
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        self._channel = get_settings().REDIS_EVENT_CHANNEL
        self._handlers: dict[str, list[Callable]] = {}

    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to the bus."""
        message = json.dumps(asdict(event))
        await self._redis.publish(self._channel, message)
        logger.info(
            "event.published",
            event_type=event.event_type,
            engine_id=event.engine_id,
            entity_id=event.entity_id,
            tenant_id=event.tenant_id,
        )

    async def publish_raw(
        self,
        event_type: str,
        engine_id: str,
        tenant_id: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any],
        actor_id: str | None = None,
    ) -> None:
        """Convenience method — creates and publishes in one call."""
        event = DomainEvent.create(
            event_type=event_type,
            engine_id=engine_id,
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            actor_id=actor_id,
        )
        await self.publish(event)

    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], Awaitable[None]]) -> None:
        """Register a handler for an event type. Called at app startup."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug("event.handler_registered", event_type=event_type)

    async def dispatch(self, raw_message: str) -> None:
        """Called by the subscriber loop. Routes to registered handlers."""
        try:
            data = json.loads(raw_message)
            event = DomainEvent(**data)
            handlers = self._handlers.get(event.event_type, [])
            wildcard = self._handlers.get("*", [])
            for handler in handlers + wildcard:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(
                        "event.handler_error",
                        event_type=event.event_type,
                        handler=handler.__name__,
                        error=str(e),
                    )
        except Exception as e:
            logger.error("event.dispatch_error", error=str(e), raw=raw_message[:200])


# Global event bus instance (initialized in app lifespan)
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    if _event_bus is None:
        raise RuntimeError("Event bus not initialized. Check app lifespan.")
    return _event_bus


def set_event_bus(bus: EventBus) -> None:
    global _event_bus
    _event_bus = bus
