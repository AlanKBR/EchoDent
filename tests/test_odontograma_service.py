from __future__ import annotations

import pytest
from app import db
from app.models import Paciente, OdontogramaDenteEstado
from app.services.odontograma_service import (
    update_estado_dente,
    get_estado_odontograma_completo,
    snapshot_odontograma_inicial,
)


def _create_paciente(nome: str = "Paciente Odonto") -> Paciente:
    p = Paciente()
    p.nome_completo = nome
    db.session.add(p)
    db.session.commit()
    return p


def test_update_estado_dente_upsert(db_session):
    p = _create_paciente()

    # Insert
    estado1 = {"status": "presente", "flags": {"carie": False}, "endo": None}
    row1 = update_estado_dente(p.id, "11", estado1, usuario_id=1)
    assert isinstance(row1, OdontogramaDenteEstado)
    assert row1.tooth_id == "11"
    assert row1.estado_json["status"] == "presente"

    # Update
    estado2 = {"status": "restaurado", "flags": {"carie": False}, "endo": None}
    row2 = update_estado_dente(p.id, "11", estado2, usuario_id=1)
    assert isinstance(row2, OdontogramaDenteEstado)
    assert row2.id == row1.id  # same record updated
    assert row2.estado_json["status"] == "restaurado"


ess_map = {
    "11": {"status": "presente", "flags": {}, "endo": None},
    "12": {"status": "ausente", "flags": {}, "endo": None},
    "21": {"status": "presente", "flags": {"fratura": True}, "endo": None},
}


def test_get_estado_odontograma_completo_map(db_session):
    p = _create_paciente()

    for tooth, state in ess_map.items():
        update_estado_dente(p.id, tooth, state, usuario_id=1)

    result = get_estado_odontograma_completo(p.id)
    assert isinstance(result, dict)
    # Should contain exactly our inserted keys
    assert set(result.keys()) == set(ess_map.keys())
    # State entries should match
    assert result["11"]["status"] == "presente"
    assert result["12"]["status"] == "ausente"
    assert result["21"]["flags"].get("fratura") is True


def test_snapshot_odontograma_inicial_happy_and_overwrite_rules(db_session):
    p = _create_paciente()

    # Create live state
    update_estado_dente(
        p.id,
        "11",
        {"status": "presente", "flags": {}, "endo": None},
        usuario_id=1,
    )
    update_estado_dente(
        p.id,
        "12",
        {"status": "ausente", "flags": {}, "endo": None},
        usuario_id=1,
    )

    # Snapshot happy path
    assert snapshot_odontograma_inicial(p.id, usuario_id=1) is True
    # Reload paciente to verify persistence
    p_ref = db.session.get(Paciente, p.id)
    assert isinstance(p_ref, Paciente)
    snap = getattr(p_ref, "odontograma_inicial_json", None)
    assert isinstance(snap, dict)
    assert set(snap.keys()) == {"11", "12"}
    # Timestamp should be set (timezone-aware)
    ts1 = getattr(p_ref, "odontograma_inicial_data", None)
    assert ts1 is not None

    # Attempt to snapshot again without force -> should raise
    with pytest.raises(ValueError):
        snapshot_odontograma_inicial(p.id, usuario_id=1, force_overwrite=False)

    # Now change live state and force overwrite
    update_estado_dente(
        p.id,
        "12",
        {"status": "presente", "flags": {"implante": True}},
        usuario_id=1,
    )
    assert snapshot_odontograma_inicial(
        p.id, usuario_id=1, force_overwrite=True
    )
    p_ref2 = db.session.get(Paciente, p.id)
    snap2 = getattr(p_ref2, "odontograma_inicial_json", None)
    assert isinstance(snap2, dict)
    # Now '12' should reflect the overwritten state
    assert snap2["12"]["status"] == "presente"
    # Timestamp should be updated on force overwrite
    ts2 = getattr(p_ref2, "odontograma_inicial_data", None)
    assert ts2 is not None
    assert ts2 >= ts1
    assert ts2 != ts1


def test_update_odontograma_bulk_happy_and_rollback(app, db_session):
    from app.services.odontograma_service import update_odontograma_bulk
    p = _create_paciente()

    # Seed one existing
    update_estado_dente(
        p.id,
        "18",
        {"status": "presente", "flags": {}, "endo": None},
        usuario_id=1,
    )

    # Happy path: 2 updates (including existing) + 1 creation
    payload = {
        "18": {"status": "restaurado", "flags": {"amalgama": True}},
        "17": {"status": "presente", "flags": {}},
        "16": {"status": "ausente", "flags": {}},
    }
    assert update_odontograma_bulk(p.id, payload, usuario_id=1) is True

    # Verify all three persisted atomically
    full = get_estado_odontograma_completo(p.id)
    assert set(full.keys()).issuperset({"16", "17", "18"})
    assert full["18"]["status"] == "restaurado"

    # Rollback case: invalid None for estado_json (violates nullable=False)
    bad_payload = {
        "18": None,  # invalid
        "15": {"status": "presente"},
    }
    with pytest.raises(ValueError):
        update_odontograma_bulk(p.id, bad_payload, usuario_id=1)

    # Ensure no partial writes after rollback ("15" should NOT exist)
    full_after = get_estado_odontograma_completo(p.id)
    assert "15" not in full_after
