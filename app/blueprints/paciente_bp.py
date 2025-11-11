from __future__ import annotations

import os

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from app.models import Paciente as PacienteModel
from app.models import TimelineEvento  # noqa: F401 (kept for clarity)
from app.services import user_preferences_service
from app.services.paciente_service import (
    create_paciente,
    get_all_pacientes,
    get_anamnese_status,
    get_paciente_by_id,
    save_media_file,
    update_anamnese,
    update_ficha_anamnese_atomic,
    update_paciente,
)

paciente_bp = Blueprint("paciente_bp", __name__, url_prefix="/pacientes")


@paciente_bp.route("/", methods=["GET"])
@login_required
def lista():  # pragma: no cover - thin controller
    pacientes = get_all_pacientes()
    colunas_visiveis = user_preferences_service.get_paciente_lista_colunas(
        current_user.id
    )
    return render_template(
        "pacientes/lista.html",
        pacientes=pacientes,
        colunas_visiveis=colunas_visiveis,
    )


@paciente_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():  # pragma: no cover - thin controller
    if request.method == "POST":
        try:
            create_paciente(request.form, current_user.id)
            flash("Paciente criado com sucesso.", "success")
            return redirect(url_for("paciente_bp.lista"))
        except ValueError as e:
            flash(str(e), "danger")
    return render_template("pacientes/form.html", paciente=None)


@paciente_bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar(id: int):  # pragma: no cover - thin controller
    paciente = get_paciente_by_id(id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))

    if request.method == "POST":
        try:
            update_paciente(id, request.form, current_user.id)
            flash("Paciente atualizado com sucesso.", "success")
            return redirect(url_for("paciente_bp.lista"))
        except ValueError as e:
            flash(str(e), "danger")

    return render_template("pacientes/form.html", paciente=paciente)


@paciente_bp.route("/<int:paciente_id>", methods=["GET"])
@login_required
def detalhe(paciente_id: int):  # pragma: no cover - thin controller
    """DEPRECATED: Redireciona para nova arquitetura (Tela 1: Ficha)"""
    return redirect(url_for("paciente_bp.ficha", paciente_id=paciente_id))


@paciente_bp.route("/<int:paciente_id>/ficha", methods=["GET"])
@login_required
def ficha(paciente_id: int):
    """Tela 1: Ficha + Anamnese (frontend Passo 2)."""
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))
    status = get_anamnese_status(paciente)
    return render_template(
        "pacientes/ficha/ficha_paciente.html",
        paciente=paciente,
        status=status,
    )


@paciente_bp.route("/<int:paciente_id>/odontograma", methods=["GET"])
@login_required
def odontograma(paciente_id: int):
    """Tela 2: Odontograma Master (3D) - Stub (Passo 2.5)."""
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))
    return render_template(
        "pacientes/odontograma/odontograma_master.html",
        paciente=paciente,
    )


@paciente_bp.route("/<int:paciente_id>/planejamento", methods=["GET"])
@login_required
def planejamento(paciente_id: int):
    """Tela 3: Planejamento Financeiro (Orçamentos) - Stub (Passo 2.5)."""
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))
    return render_template(
        "pacientes/planejamento/planejamento_financeiro.html",
        paciente=paciente,
    )


@paciente_bp.route("/<int:paciente_id>/financeiro", methods=["GET"])
@login_required
def financeiro(paciente_id: int):
    """Tela 4: Financeiro (Extrato) - Stub (Passo 2.5)."""
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))
    return render_template(
        "pacientes/financeiro/financeiro_extrato.html",
        paciente=paciente,
    )


@paciente_bp.route("/<int:paciente_id>/historico", methods=["GET"])
@login_required
def historico(paciente_id: int):
    """Tela 5: Histórico (Timeline) - Stub (Passo 2.5)."""
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))
    return render_template(
        "pacientes/historico/historico.html",
        paciente=paciente,
    )


@paciente_bp.route("/<int:paciente_id>/atualizar", methods=["POST"])
@login_required
def atualizar_ficha(paciente_id: int):
    """Salva ficha + anamnese de forma atômica (Regra §7.5)."""
    try:
        update_ficha_anamnese_atomic(
            paciente_id=paciente_id,
            form_data=request.form,
            usuario_id=current_user.id,
        )
    except ValueError as e:
        return str(e), 400
    from flask import make_response

    resp = make_response("", 204)
    resp.headers["HX-Redirect"] = url_for(
        "paciente_bp.ficha", paciente_id=paciente_id
    )
    return resp


@paciente_bp.route(
    "/<int:paciente_id>/tab/anamnese", methods=["GET"]
)  # Tela 1 - DEPRECATED (manter temporariamente para compatibilidade)
@login_required
def tab_anamnese(paciente_id: int):  # pragma: no cover - thin controller
    """DEPRECATED: Redireciona para nova rota /ficha"""
    return redirect(url_for("paciente_bp.ficha", paciente_id=paciente_id))


# ROTAS ANTIGAS REMOVIDAS (Passo 2.5)
# As rotas tab_planejamento, tab_financeiro e tab_historico foram substituídas
# pelas novas rotas dedicadas: /planejamento, /financeiro, /historico


@paciente_bp.route("/<int:paciente_id>/anamnese", methods=["GET", "POST"])
@login_required
def anamnese(paciente_id: int):  # pragma: no cover - thin controller
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))

    if request.method == "POST":
        update_anamnese(paciente_id, request.form, current_user.id)
        flash("Anamnese salva.", "success")
        return redirect(
            url_for("paciente_bp.detalhe", paciente_id=paciente_id)
        )

    return render_template(
        "pacientes/form_anamnese.html",
        paciente=paciente,
        anamnese=paciente.anamnese,
    )


@paciente_bp.route("/anamnese_fragment", methods=["GET"])
@login_required
def anamnese_fragment():  # pragma: no cover - thin controller
    field = (request.args.get("field") or "none").lower()
    if field == "alergias":
        return render_template("pacientes/anamnese/_anamnese_alergias.html")
    if field == "medicamentos":
        return render_template(
            "pacientes/anamnese/_anamnese_medicamentos.html"
        )
    return "", 204


@paciente_bp.route("/<int:paciente_id>/upload_media", methods=["POST"])
@login_required
def upload_media(paciente_id: int):  # pragma: no cover - thin controller
    if "file" not in request.files:
        flash("Nenhum arquivo enviado.", "info")
        return redirect(
            url_for("paciente_bp.detalhe", paciente_id=paciente_id)
        )
    file = request.files["file"]
    descricao = request.form.get("descricao") or None
    try:
        save_media_file(paciente_id, file, descricao, current_user.id)
        flash("Mídia salva com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("paciente_bp.detalhe", paciente_id=paciente_id))


@paciente_bp.route("/media/<int:media_id>", methods=["GET"])
@login_required
def get_media_file(media_id: int):  # pragma: no cover - thin controller
    from app.models import MediaPaciente  # local import to avoid cycles

    media = MediaPaciente.query.get_or_404(media_id)
    media_dir = os.path.join(current_app.instance_path, "media_storage")
    # file_path is relative (e.g., "<paciente_id>/<filename>")
    return send_from_directory(media_dir, media.file_path, as_attachment=False)


@paciente_bp.route("/buscar", methods=["GET"])
@login_required
def buscar_pacientes():  # pragma: no cover - thin controller
    """Autocomplete simples de pacientes por nome (ilike), limitado a 10."""
    q = (request.args.get("q") or "").strip()
    resultados = []
    if q:
        try:
            like = f"%{q}%"
            resultados = (
                PacienteModel.query.filter(
                    PacienteModel.nome_completo.ilike(like)
                )
                .order_by(PacienteModel.nome_completo)
                .limit(10)
                .all()
            )
        except Exception:
            resultados = []
    return render_template(
        "documentos/_lista_pacientes_autocomplete.html",
        pacientes=resultados,
    )


@paciente_bp.route("/modal_configurar_colunas", methods=["GET"])
@login_required
def modal_configurar_colunas():  # pragma: no cover - thin controller
    """Retorna o modal HTML com formulário de configuração de colunas."""
    colunas_visiveis = user_preferences_service.get_paciente_lista_colunas(
        current_user.id
    )
    return render_template(
        "pacientes/modal_configurar_colunas.html",
        colunas_visiveis=colunas_visiveis,
    )


@paciente_bp.route("/busca_global", methods=["GET"])
@login_required
def busca_global():  # pragma: no cover - thin controller
    """Busca global de pacientes: recentes ou filtrados por nome."""
    q = (request.args.get("q") or "").strip()
    query = PacienteModel.query

    # Modo Busca: filtrar por nome (ilike)
    if q:
        like_pattern = f"%{q}%"
        query = query.filter(PacienteModel.nome_completo.ilike(like_pattern))

    # Ordenação por denormalização (desc nullslast) e limite
    from sqlalchemy import desc, nullslast

    resultados = (
        query.order_by(
            nullslast(desc(PacienteModel.ultima_interacao_at)),
            PacienteModel.nome_completo,
        )
        .limit(7)
        .all()
    )

    return render_template(
        "pacientes/_busca_global_dropdown.html",
        resultados=resultados,
        query=q,
    )


@paciente_bp.route("/configurar_colunas", methods=["POST"])
@login_required
def configurar_colunas():  # pragma: no cover - thin controller
    """Salva preferências de colunas e retorna fragmento atualizado."""
    # Reconstruir dicionário a partir dos checkboxes marcados
    colunas_novas = {
        "telefone": "telefone" in request.form,
        "email": "email" in request.form,
        "idade": "idade" in request.form,
        "sexo": "sexo" in request.form,
        "data_ultimo_registro": "data_ultimo_registro" in request.form,
        "status_anamnese": "status_anamnese" in request.form,
        "cpf": "cpf" in request.form,
        "cidade": "cidade" in request.form,
    }
    success = user_preferences_service.update_paciente_lista_colunas(
        current_user.id, colunas_novas
    )
    if not success:
        flash("Erro ao salvar preferências.", "danger")
        # Retornar fragmento vazio com erro para fechar modal sem reload
        return "", 400

    # Buscar pacientes e colunas atualizadas para re-renderizar tabela
    pacientes = get_all_pacientes()
    colunas_visiveis = user_preferences_service.get_paciente_lista_colunas(
        current_user.id
    )
    # Header HX-Trigger para fechar modal (via evento customizado)
    from flask import make_response

    resp = make_response(
        render_template(
            "pacientes/_tabela_fragment.html",
            pacientes=pacientes,
            colunas_visiveis=colunas_visiveis,
        )
    )
    resp.headers["HX-Trigger"] = "closeModal"
    return resp


# ROTAS DE IMPRESSÃO DESCONTINUADAS (WeasyPrint removido no Passo 1)
# Mantidas comentadas intencionalmente até a migração para window.print.
# Ver diretrizes na Seção 9 do AGENTS.MD e novo serviço de emissão.
# @paciente_bp.route(
#     "/<int:paciente_id>/imprimir/receita", methods=["GET", "POST"]
# )
# @login_required
# def imprimir_receita(paciente_id: int):  # pragma: no cover - thin controller
#     return "", 410  # Gone


# @paciente_bp.route(
#     "/<int:paciente_id>/imprimir/atestado", methods=["GET", "POST"]
# )
# @login_required
# def imprimir_atestado(paciente_id: int):  # pragma: no cover
#     return "", 410  # Gone
