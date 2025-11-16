"""Agent Runtime Utilities

Provides helpers to update mission state and append delegation log entries.
This is a lightweight utility; integration points can call these functions
before/after subagent delegations.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List

RUNTIME_DIR = Path("instance/agent_runtime")
STATE_FILE = RUNTIME_DIR / "mission_state.json"
LOG_FILE = RUNTIME_DIR / "delegations.log"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        STATE_FILE.write_text(json.dumps({
            "active": False,
            "currentPhase": None,
            "delegations": [],
            "confidenceHistory": [],
            "gaps": [],
            "startedAt": None,
            "updatedAt": None
        }, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> Dict[str, Any]:
    ensure_runtime_dir()
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {
            "active": False,
            "currentPhase": None,
            "delegations": [],
            "confidenceHistory": [],
            "gaps": [],
            "startedAt": None,
            "updatedAt": None
        }


def save_state(state: Dict[str, Any]) -> None:
    state["updatedAt"] = _now_iso()
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def start_mission(phase: str = "ingestao") -> Dict[str, Any]:
    state = load_state()
    state.update({
        "active": True,
        "currentPhase": phase,
        "delegations": [],
        "confidenceHistory": [],
        "gaps": [],
        "startedAt": _now_iso()
    })
    save_state(state)
    return state


def update_phase(phase: str) -> Dict[str, Any]:
    state = load_state()
    state["currentPhase"] = phase
    save_state(state)
    return state


def record_delegation(
    agent: str,
    query: str,
    confidence: float | None,
    gaps: List[str] | None,
) -> Dict[str, Any]:
    state = load_state()
    delegation = {
        "timestamp": _now_iso(),
        "agent": agent,
        "query": query,
        "confidence": confidence,
        "gaps": gaps or []
    }
    state["delegations"].append(delegation)
    if confidence is not None:
        state["confidenceHistory"].append(confidence)
    if gaps:
        state["gaps"].extend(gaps)
    save_state(state)
    _append_log_line(delegation)
    return state


def _append_log_line(entry: Dict[str, Any]) -> None:
    ensure_runtime_dir()
    line = json.dumps(entry, ensure_ascii=False)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    _rotate_if_needed()


def _rotate_if_needed(max_bytes: int = 5_000_000) -> None:
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > max_bytes:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        rotated = LOG_FILE.with_name(f"delegations-{timestamp}.log")
        os.replace(LOG_FILE, rotated)


def complete_mission(final_confidence: float | None) -> Dict[str, Any]:
    state = load_state()
    state["active"] = False
    if final_confidence is not None:
        state["confidenceHistory"].append(final_confidence)
    save_state(state)
    return state


if __name__ == "__main__":  # simple CLI for manual ops
    import argparse

    parser = argparse.ArgumentParser(description="Agent runtime management")
    parser.add_argument(
        "action",
        choices=["start", "phase", "delegate", "complete", "show"],
        help="Action to perform",
    )
    parser.add_argument(
        "value",
        nargs="?",
        help="Phase name, delegate spec or final confidence",
    )
    args = parser.parse_args()

    if args.action == "start":
        print(json.dumps(start_mission(), ensure_ascii=False, indent=2))
    elif args.action == "phase":
        if not args.value:
            parser.error("phase action requires phase name")
        print(
            json.dumps(update_phase(args.value), ensure_ascii=False, indent=2)
        )
    elif args.action == "delegate":
        if not args.value:
            parser.error(
                "delegate action requires 'agent:query:confidence' format"
            )
        try:
            agent, query, conf = args.value.split(":", 2)
            confidence = float(conf) if conf else None
        except ValueError:
            parser.error("Expected format agent:query:confidence")
        print(
            json.dumps(
                record_delegation(agent, query, confidence, []),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.action == "complete":
        c = float(args.value) if args.value else None
        print(json.dumps(complete_mission(c), ensure_ascii=False, indent=2))
    elif args.action == "show":
        print(json.dumps(load_state(), ensure_ascii=False, indent=2))
