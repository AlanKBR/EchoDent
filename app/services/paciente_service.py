from __future__ import annotations

import os
from datetime import datetime, date
from typing import Mapping, Optional, List, Dict, Any, cast

from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from app.models import Paciente, Anamnese, MediaPaciente


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    v = value.strip()
    # Try ISO first (YYYY-MM-DD) then common BR format
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None


def get_paciente_by_id(paciente_id: int) -> Optional[Paciente]:
    return db.session.get(Paciente, int(paciente_id))


def get_all_pacientes() -> List[Paciente]:
    return (
        db.session.query(Paciente)
        .order_by(Paciente.nome_completo.asc())
        .all()
    )


def create_paciente(form_data: Mapping[str, str]) -> Paciente:
    p = Paciente()
    p.nome_completo = (form_data.get("nome_completo") or "").strip()
    if not p.nome_completo:
        raise ValueError("Nome do paciente é obrigatório.")

    p.data_nascimento = _parse_date(form_data.get("data_nascimento"))
    p.cpf = (form_data.get("cpf") or None) or None
    p.telefone = (form_data.get("telefone") or None) or None
    p.email = (form_data.get("email") or None) or None
    p.cep = (form_data.get("cep") or None) or None
    p.logradouro = (form_data.get("logradouro") or None) or None
    p.numero = (form_data.get("numero") or None) or None
    p.complemento = (form_data.get("complemento") or None) or None
    p.bairro = (form_data.get("bairro") or None) or None
    p.cidade = (form_data.get("cidade") or None) or None
    p.estado = (form_data.get("estado") or None) or None

    db.session.add(p)
    db.session.flush()  # ensure p.id

    # optionally create empty Anamnese
    criar_anamnese = form_data.get("criar_anamnese")
    if criar_anamnese:
        a = Anamnese()
        a.paciente_id = p.id
        db.session.add(a)

    db.session.commit()
    return p


def update_paciente(
    paciente_id: int, form_data: Mapping[str, str]
) -> Paciente:
    p = get_paciente_by_id(paciente_id)
    if p is None:
        raise ValueError("Paciente não encontrado.")

    nome = (form_data.get("nome_completo") or "").strip()
    if nome:
        p.nome_completo = nome

    dn = _parse_date(form_data.get("data_nascimento"))
    if form_data.get("data_nascimento") is not None:
        p.data_nascimento = dn

    # Update other simple fields (set to None if provided empty)
    for field in (
        "cpf",
        "telefone",
        "email",
        "cep",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cidade",
        "estado",
    ):
        if field in form_data:
            value = form_data.get(field) or None
            setattr(p, field, value)

    db.session.add(p)
    db.session.commit()
    return p


def update_anamnese(
    paciente_id: int, form_data: Mapping[str, Any]
) -> Anamnese:
    """Create or update a patient's Anamnese and compute red flags.

        Red flags when:
        - Any of: alergias, medicamentos_uso_continuo,
            historico_doencas are non-empty
    - Any boolean-like field in form_data has value 'sim' (case-insensitive)
    """
    paciente = get_paciente_by_id(paciente_id)
    if paciente is None:
        raise ValueError("Paciente não encontrado.")

    a = paciente.anamnese
    if a is None:
        a = Anamnese()
        a.paciente_id = paciente.id
        db.session.add(a)

    # Map possible form aliases to model fields
    alias_map: Dict[str, str] = {
        "alergia_detalhes": "alergias",
        "alergias": "alergias",
        "medicamentos": "medicamentos_uso_continuo",
        "medicamentos_uso_continuo": "medicamentos_uso_continuo",
        "historico_doencas": "historico_doencas",
    }

    def _normalize_safe_text(val: Optional[str]) -> Optional[str]:
        """Return None for values that semantically mean 'empty/safe'.

        Treat common synonyms as empty: 'nenhuma', 'nenhum', 'nao', 'não',
        'n/a', 'none', 'no', '-', 'sem', 'sem alergias'.
        """
        if val is None:
            return None
        s = val.strip()
        if not s:
            return None
        low = s.lower()
        safe_tokens = {
            "nenhuma",
            "nenhum",
            "nao",
            "não",
            "n/a",
            "none",
            "no",
            "-",
            "sem",
            "sem alergias",
        }
        return None if low in safe_tokens else s

    # Update known fields (with normalization of safe values)
    for form_key, model_key in alias_map.items():
        if form_key in form_data:
            raw = form_data.get(form_key)
            val = _normalize_safe_text(cast(Optional[str], raw))
            setattr(a, model_key, val)

    # Compute red flags
    flag = False
    for key in ("alergias", "medicamentos_uso_continuo", "historico_doencas"):
        if getattr(a, key, None):
            flag = True
            break
    if not flag:
        # Look for yes/no fields where 'sim' indicates a red flag
        for k, v in form_data.items():
            if isinstance(v, str) and v.strip().lower() == "sim":
                flag = True
                break

    setattr(a, "has_red_flags", bool(flag))
    db.session.commit()
    return cast(Anamnese, a)


def save_media_file(
    paciente_id: int, file_storage, descricao: Optional[str]
) -> MediaPaciente:
    """Save file under instance/media_storage/<paciente_id>/.

    Also record the relative path in the database.
    """
    paciente = get_paciente_by_id(paciente_id)
    if paciente is None:
        raise ValueError("Paciente não encontrado.")

    if not file_storage or not getattr(file_storage, "filename", None):
        raise ValueError("Arquivo inválido.")

    filename = secure_filename(file_storage.filename)
    if not filename:
        raise ValueError("Nome de arquivo inválido.")

    base_dir = os.path.join(current_app.instance_path, "media_storage")
    media_dir = os.path.join(base_dir, str(paciente_id))
    os.makedirs(media_dir, exist_ok=True)

    save_path = os.path.join(media_dir, filename)
    relative_path = os.path.join(str(paciente_id), filename)

    file_storage.save(save_path)

    media = MediaPaciente()
    media.paciente_id = paciente_id
    media.file_path = relative_path
    media.descricao = (descricao or None)
    db.session.add(media)
    db.session.commit()
    return media
