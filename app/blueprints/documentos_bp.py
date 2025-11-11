from __future__ import annotations

from flask import Blueprint, Response, abort, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import (
    Paciente,
    RoleEnum,
    TemplateDocumento,
    TipoDocumento,
    Usuario,
)
from app.services import servico_emissao

documentos_bp = Blueprint("documentos_bp", __name__)


@documentos_bp.route("/imprimir/log/<int:log_id>", methods=["GET"])
@login_required
def imprimir_log(log_id: int):  # pragma: no cover - thin controller
    try:
        html_documento = servico_emissao.renderizar_documento_html(log_id)
    except ValueError:
        return abort(404)
    return render_template(
        "documentos/print_page.html",
        html_documento=html_documento,
    )


@documentos_bp.route("/documentos", methods=["GET"])
@login_required
def hub_documentos():  # pragma: no cover - thin controller
    paciente_id = request.args.get("paciente_id", type=int)
    tipo_doc_raw = (request.args.get("tipo_doc") or "").strip()

    paciente = Paciente.query.get(paciente_id) if paciente_id else None
    tipos_documento = list(TipoDocumento)

    # Cenário B: contextual (paciente_id & tipo_doc)
    if paciente and tipo_doc_raw:
        try:
            tipo_enum = TipoDocumento(tipo_doc_raw)
        except Exception:
            return abort(404)
        templates = TemplateDocumento.query.filter_by(
            tipo_doc=tipo_enum, is_active=True
        ).all()
        campos_dinamicos: list[str] = []
        if templates:
            campos_dinamicos = servico_emissao.parse_campos_dinamicos(
                templates[0].template_body or ""
            )
        dentistas = (
            Usuario.query.filter_by(role=RoleEnum.DENTISTA)
            .order_by(Usuario.nome_completo)
            .all()
        )
        return render_template(
            "documentos/documentos_hub.html",
            tipos_documento=tipos_documento,
            paciente=paciente,
            inner_partial="documentos/_form_gerador.html",
            tipo_doc=tipo_enum.value,
            templates=templates,
            campos_dinamicos=campos_dinamicos,
            dentistas=dentistas,
            pacientes=(
                Paciente.query.order_by(Paciente.nome_completo).limit(50).all()
            ),
        )

    # Cenário A: global (hub de cards)
    return render_template(
        "documentos/documentos_hub.html",
        tipos_documento=tipos_documento,
        paciente=None,
        inner_partial="documentos/_hub_cards.html",
    )


@documentos_bp.route("/documentos/form/<tipo_doc>", methods=["GET"])
@login_required
def form_documento(tipo_doc: str):  # pragma: no cover - thin controller
    try:
        tipo_enum = TipoDocumento(tipo_doc)
    except Exception:
        return abort(404)

    paciente_id = request.args.get("paciente_id", type=int)
    paciente = Paciente.query.get(paciente_id) if paciente_id else None

    templates = TemplateDocumento.query.filter_by(
        tipo_doc=tipo_enum, is_active=True
    ).all()

    campos_dinamicos: list[str] = []
    if templates:
        campos_dinamicos = servico_emissao.parse_campos_dinamicos(
            templates[0].template_body or ""
        )

    dentistas = (
        Usuario.query.filter_by(role=RoleEnum.DENTISTA)
        .order_by(Usuario.nome_completo)
        .all()
    )

    return render_template(
        "documentos/_form_gerador.html",
        tipo_doc=tipo_enum.value,
        paciente=paciente,
        templates=templates,
        campos_dinamicos=campos_dinamicos,
        dentistas=dentistas,
        pacientes=(
            Paciente.query.order_by(Paciente.nome_completo).limit(50).all()
        ),
    )


@documentos_bp.route("/gerador/<tipo_doc>", methods=["POST"])
@login_required
def criar_log(tipo_doc: str):  # pragma: no cover - thin controller
    try:
        _ = TipoDocumento(tipo_doc)
    except Exception:
        return abort(404)

    # Campos básicos
    paciente_id = request.form.get("paciente_id", type=int)
    template_id = request.form.get("template_id", type=int)
    dentista_responsavel_id = request.form.get(
        "dentista_responsavel_id", type=int
    )

    # Monta dados_chave: tenta JSON livre primeiro, senão coleta campos livres
    dados_chave: dict = {}
    dados_json_raw = (request.form.get("dados_json") or "").strip()
    if dados_json_raw:
        import json

        try:
            dados_chave = json.loads(dados_json_raw)
        except Exception:
            for line in dados_json_raw.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    dados_chave[k.strip()] = v.strip()
    else:
        # Coleta todos os campos do form que não são de controle
        ignorar = {
            "paciente_id",
            "template_id",
            "dentista_responsavel_id",
            "dados_json",
            "q",
        }
        for k, v in request.form.items():
            if k not in ignorar and v is not None and v != "":
                dados_chave[k] = v

    try:
        novo_log_id = servico_emissao.criar_log_emissao(
            paciente_id=paciente_id,
            usuario_id=current_user.id,
            template_id=template_id,
            dados_chave=dados_chave,
            dentista_responsavel_id=dentista_responsavel_id,
        )

        # PRG via HX-Redirect
        url_impressao = url_for(
            "documentos_bp.imprimir_log", log_id=novo_log_id
        )
        resp = Response("")
        resp.headers["HX-Redirect"] = url_impressao
        return resp
    except Exception as e:
        # Debug-friendly response to surface the root cause in E2E runs
        # In production, the global handler would render 500; here we expose
        # the message to unblock the end-to-end verification step.
        return (
            f"Falha ao criar log: {e}",
            400,
            {
                "Content-Type": "text/plain; charset=utf-8",
                "HX-Reswap": "outerHTML",
                "HX-Retarget": "#modal-documento",
            },
        )
