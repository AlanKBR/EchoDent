from __future__ import annotations

from flask import (
    Blueprint,
    render_template,
    abort,
    request,
    Response,
    url_for,
)
from flask_login import login_required, current_user

from app.models import Paciente, TemplateDocumento, TipoDocumento
from app.services import servico_emissao
from app.utils.decorators import dentista_required


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


@documentos_bp.route("/gerador/<tipo_doc>", methods=["GET"])
@login_required
@dentista_required
def gerador(tipo_doc: str):  # pragma: no cover - thin controller
    # Normaliza o enum/valor recebido
    try:
        tipo_enum = TipoDocumento(tipo_doc)
    except Exception:
        return abort(404)

    paciente_id = request.args.get("paciente_id", type=int)
    paciente = None
    if paciente_id:
        paciente = Paciente.query.get(paciente_id)

    templates = (
        TemplateDocumento.query.filter_by(
            tipo_doc=tipo_enum, is_active=True
        ).all()
    )
    return render_template(
        "documentos/_form_gerador.html",
        tipo_doc=tipo_enum.value,
        paciente=paciente,
        templates=templates,
        pacientes=(
            Paciente.query.order_by(Paciente.nome_completo)
            .limit(50)
            .all()
        ),
    )


@documentos_bp.route("/gerador/<tipo_doc>", methods=["POST"])
@login_required
@dentista_required
def criar_log(tipo_doc: str):  # pragma: no cover - thin controller
    try:
        _ = TipoDocumento(tipo_doc)
    except Exception:
        return abort(404)

    # Campos básicos
    paciente_id = request.form.get("paciente_id", type=int)
    template_id = request.form.get("template_id", type=int)

    # Monta dados_chave: tenta JSON livre primeiro
    dados_chave: dict = {}
    dados_json_raw = (request.form.get("dados_json") or "").strip()
    if dados_json_raw:
        # Best-effort: tenta interpretar como pares simples key=value por linha
        # ou JSON; mantemos simples para este passo.
        import json

        try:
            dados_chave = json.loads(dados_json_raw)
        except Exception:
            # Fallback: parse simples linha a linha 'chave: valor'
            for line in dados_json_raw.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    dados_chave[k.strip()] = v.strip()
    else:
        # Campos específicos simples por tipo (conveniência)
        # ATESTADO: dias_repouso
        if "dias_repouso" in request.form:
            dados_chave["dias_repouso"] = request.form.get("dias_repouso")
        # RECEITA: nome_remedio e posologia_remedio
        if "nome_remedio" in request.form:
            dados_chave["nome_remedio"] = request.form.get("nome_remedio")
        if "posologia_remedio" in request.form:
            dados_chave["posologia_remedio"] = request.form.get(
                "posologia_remedio"
            )

    try:
        novo_log_id = servico_emissao.criar_log_emissao(
            paciente_id=paciente_id,
            usuario_id=current_user.id,
            template_id=template_id,
            dados_chave=dados_chave,
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
