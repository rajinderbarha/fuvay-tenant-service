"""Bounded, read-only concurrency probe for authenticated admin APIs.

This is a developer confidence tool, not a substitute for a production-sized
dataset or distributed load test.  It deliberately permits GET endpoints only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import statistics
import time
from collections import Counter
from dataclasses import dataclass

import httpx


DEFAULT_ENDPOINTS = (
    "/health",
    "/v1/admin/home-services/customers/summary",
    "/v1/admin/home-services/customers?page=1&page_size=20",
    "/v1/admin/home-services/operations/summary",
    "/v1/admin/home-services/operations?page=1&page_size=25",
    "/v1/admin/complaints/summary",
    "/v1/admin/complaints/list?page=1&page_size=25",
    "/v1/admin/notification-outbox/channel-status",
)


@dataclass(frozen=True)
class Sample:
    endpoint: str
    status: int
    elapsed_ms: float
    error: str | None = None


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * fraction) - 1)
    return ordered[index]


async def login(client: httpx.AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": password},
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("data", {}).get("access_token")
    if not token:
        raise RuntimeError("Login response did not include an access token")
    return token


async def request_once(
    client: httpx.AsyncClient,
    endpoint: str,
    semaphore: asyncio.Semaphore,
) -> Sample:
    async with semaphore:
        started = time.perf_counter()
        try:
            response = await client.get(endpoint)
            elapsed = (time.perf_counter() - started) * 1000
            return Sample(endpoint, response.status_code, elapsed)
        except Exception as exc:  # the report must retain transport failures
            elapsed = (time.perf_counter() - started) * 1000
            return Sample(endpoint, 0, elapsed, type(exc).__name__)


async def run(args: argparse.Namespace) -> int:
    endpoints = tuple(args.endpoint or DEFAULT_ENDPOINTS)
    if any(not endpoint.startswith("/") for endpoint in endpoints):
        raise ValueError("Every endpoint must be an absolute path")

    limits = httpx.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    timeout = httpx.Timeout(args.timeout)
    async with httpx.AsyncClient(
        base_url=args.base_url.rstrip("/"),
        limits=limits,
        timeout=timeout,
    ) as client:
        token = await login(client, args.email, args.password)
        client.headers["Authorization"] = f"Bearer {token}"

        # Exclude import, authentication, and connection warm-up from results.
        for endpoint in endpoints:
            response = await client.get(endpoint)
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Warm-up failed for {endpoint}: HTTP {response.status_code}"
                )

        semaphore = asyncio.Semaphore(args.concurrency)
        work = [
            request_once(client, endpoints[index % len(endpoints)], semaphore)
            for index in range(args.requests)
        ]
        started = time.perf_counter()
        samples = await asyncio.gather(*work)
        wall_seconds = time.perf_counter() - started

    rows = []
    for endpoint in endpoints:
        group = [sample for sample in samples if sample.endpoint == endpoint]
        timings = [sample.elapsed_ms for sample in group]
        statuses = Counter(str(sample.status) for sample in group)
        errors = Counter(sample.error for sample in group if sample.error)
        rows.append(
            {
                "endpoint": endpoint,
                "requests": len(group),
                "statuses": dict(sorted(statuses.items())),
                "errors": dict(sorted(errors.items())),
                "p50_ms": round(statistics.median(timings), 2),
                "p95_ms": round(percentile(timings, 0.95), 2),
                "p99_ms": round(percentile(timings, 0.99), 2),
                "max_ms": round(max(timings, default=0.0), 2),
            }
        )

    failed = sum(sample.status < 200 or sample.status >= 300 for sample in samples)
    report = {
        "base_url": args.base_url,
        "concurrency": args.concurrency,
        "requests": args.requests,
        "wall_seconds": round(wall_seconds, 3),
        "requests_per_second": round(args.requests / wall_seconds, 2),
        "failed": failed,
        "results": rows,
    }
    print(json.dumps(report, indent=2))
    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--email", default=os.getenv("SERVICEOS_LOAD_EMAIL", "admin@serviceos.in"))
    parser.add_argument("--password", default=os.getenv("SERVICEOS_LOAD_PASSWORD", "Password123!"))
    parser.add_argument("--requests", type=int, default=160)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--endpoint",
        action="append",
        help="GET path to probe; repeat to override the default endpoint set",
    )
    args = parser.parse_args()
    if args.requests < 1 or args.requests > 10_000:
        parser.error("--requests must be between 1 and 10000")
    if args.concurrency < 1 or args.concurrency > 200:
        parser.error("--concurrency must be between 1 and 200")
    return args


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
