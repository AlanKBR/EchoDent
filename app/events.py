from __future__ import annotations

import json
from datetime import datetime, date
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any, Dict

from flask_login import current_user
from sqlalchemy import event
from sqlalchemy.inspection import inspect as sa_inspect

from app import db
from app.models import LogAuditoria


def _jsonify_value(value: Any) -> Any:
    """Convert values to JSON-serializable representations."""
    if isinstance(value, (str, int, float)) or value is None:
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, PyEnum):
        return value.value
    # Fallback to string
    return str(value)


def _row_state_dict(obj: Any) -> Dict[str, Any]:
    mapper = sa_inspect(obj).mapper
    data: Dict[str, Any] = {}
    for col in mapper.columns:
        try:
            data[col.key] = _jsonify_value(getattr(obj, col.key))
        except Exception:
            data[col.key] = None
    return data


def _row_diff(obj: Any) -> Dict[str, Dict[str, Any]]:
    """Return a dict of changed columns: {col: {"old": ..., "new": ...}}"""
    insp = sa_inspect(obj)
    mapper = insp.mapper
    diff: Dict[str, Dict[str, Any]] = {}
    for col in mapper.columns:
        attr = getattr(insp.attrs, col.key)
        hist = attr.history
        if hist.has_changes():
            old_val = (
                hist.deleted[0] if hist.deleted else getattr(obj, col.key)
            )
            new_val = hist.added[0] if hist.added else getattr(obj, col.key)
            diff[col.key] = {
                "old": _jsonify_value(old_val),
                "new": _jsonify_value(new_val),
            }
    return diff


@event.listens_for(db.session, "before_flush")
def track_changes(session, flush_context, instances):  # type: ignore[no-redef]
    """Collect and persist audit logs for updates/deletes before flush.

    For creates, we collect state in session.info to record after flush, so
    that auto-increment primary keys are available (model_id NOT NULL).
    """
    # Avoid recursion when logs themselves trigger flush
    if session.info.get("_audit_in_progress"):
        return

    # Resolve current user id, if available
    try:
        user_id = (
            int(getattr(current_user, "id", 0))
            if getattr(current_user, "is_authenticated", False)
            else None
        )
    except Exception:
        user_id = None
    session.info["_audit_user_id"] = user_id

    novos_logs = []

    # Handle creations later (after flush) to capture the generated PKs.
    creates = []
    for obj in list(session.new):
        if isinstance(obj, LogAuditoria):
            continue
        # store the state now; ID may be None before flush
        state = _row_state_dict(obj)
        creates.append((obj, state))
    if creates:
        session.info.setdefault("_audit_creates", []).extend(creates)

    # Updates
    for obj in list(session.dirty):
        if isinstance(obj, LogAuditoria):
            continue
        diff = _row_diff(obj)
        if not diff:
            continue
        model_name = obj.__class__.__name__
        model_id = getattr(obj, "id", None)
        if model_id is None:
            continue  # no id, skip
        log = LogAuditoria()
        log.user_id = user_id
        log.action = "update"
        log.model_name = model_name
        log.model_id = int(model_id)
        log.changes_json = json.dumps(diff)
        novos_logs.append(log)

    # Deletes
    for obj in list(session.deleted):
        if isinstance(obj, LogAuditoria):
            continue
        model_name = obj.__class__.__name__
        model_id = getattr(obj, "id", None)
        if model_id is None:
            continue
        payload = {"id": int(model_id)}
        log = LogAuditoria()
        log.user_id = user_id
        log.action = "delete"
        log.model_name = model_name
        log.model_id = int(model_id)
        log.changes_json = json.dumps(payload)
        novos_logs.append(log)

    if novos_logs:
        session.info["_audit_in_progress"] = True
        try:
            session.add_all(novos_logs)
        finally:
            session.info["_audit_in_progress"] = False


@event.listens_for(db.session, "after_flush_postexec")
def track_creates_after_flush(
    session, flush_context
):  # type: ignore[no-redef]
    """Persist create logs after PKs are assigned by the database."""
    creates = session.info.pop("_audit_creates", [])
    if not creates:
        return
    user_id = session.info.get("_audit_user_id")
    logs = []
    for obj, state in creates:
        if isinstance(obj, LogAuditoria):
            continue
        model_name = obj.__class__.__name__
        model_id = getattr(obj, "id", None)
        if model_id is None:
            # if still None, skip to avoid NOT NULL violation
            continue
        # store the final state captured before flush
        log = LogAuditoria()
        log.user_id = user_id
        log.action = "create"
        log.model_name = model_name
        log.model_id = int(model_id)
        log.changes_json = json.dumps(state)
        logs.append(log)
    if logs:
        # guard to prevent recursion
        if session.info.get("_audit_in_progress"):
            return
        session.info["_audit_in_progress"] = True
        try:
            session.add_all(logs)
        finally:
            session.info["_audit_in_progress"] = False
