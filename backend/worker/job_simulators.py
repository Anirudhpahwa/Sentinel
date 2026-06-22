"""Phase 1 has no real business logic -- jobs are simulated. The goal is for
execution history to look and feel like a real platform's output (varied,
occasionally failing) rather than a uniform "ok" placeholder.
"""

import random
import time
from collections.abc import Callable
from typing import Any

from backend.shared.enums import JobType

FAILURE_RATE = 0.1


def simulate_job(job_type: str, payload: dict[str, Any], log: Callable[[str], None]) -> tuple[dict[str, Any], bool]:
    simulator = _SIMULATORS.get(job_type)
    if simulator is None:
        log(f"Unknown job type: {job_type}")
        return {"error": f"Unknown job type: {job_type}"}, False

    time.sleep(random.uniform(1.0, 2.5))
    log("Processing records")
    time.sleep(random.uniform(1.0, 2.5))

    if random.random() < FAILURE_RATE:
        error = simulator["failure"]()
        log(f"Error: {error}")
        return {"error": error}, False

    return simulator["success"](payload), True


def _generate_report_success(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "rows_processed": random.randint(1000, 10000),
        "report_type": payload.get("report_type", "daily"),
        "region": payload.get("region", "global"),
    }


def _process_data_success(payload: dict[str, Any]) -> dict[str, Any]:
    batch_size = payload.get("batch_size", 5000)
    return {
        "records_processed": random.randint(batch_size, batch_size * 2),
        "dataset": payload.get("dataset", "unspecified"),
    }


def _send_notification_success(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "emails_sent": random.randint(50, 500),
        "channel": payload.get("channel", "email"),
    }


_SIMULATORS: dict[str, dict[str, Callable]] = {
    JobType.GENERATE_REPORT: {
        "success": _generate_report_success,
        "failure": lambda: "Report data source timeout",
    },
    JobType.PROCESS_DATA: {
        "success": _process_data_success,
        "failure": lambda: "Batch validation error: malformed records detected",
    },
    JobType.SEND_NOTIFICATION: {
        "success": _send_notification_success,
        "failure": lambda: "Notification provider returned 503",
    },
}
