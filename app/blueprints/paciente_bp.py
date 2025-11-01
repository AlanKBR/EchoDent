from __future__ import annotations

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import login_required, current_user

from app.services.paciente_service import (
    get_all_pacientes,
    create_paciente,
    get_paciente_by_id,
    update_paciente,
    update_anamnese,
    save_media_file,
)
from app.services.financeiro_service import get_planos_by_paciente
from app.services import paciente_service
from flask import send_from_directory, current_app
import os
from app.models import TimelineEvento  # noqa: F401 (kept for clarity)
from app.models import Paciente as PacienteModel
from app.utils.decorators import dentista_required


paciente_bp = Blueprint("paciente_bp", __name__, url_prefix="/pacientes")


@paciente_bp.route("/", methods=["GET"])
@login_required
def lista():  # pragma: no cover - thin controller
    pacientes = get_all_pacientes()
    return render_template("pacientes/lista.html", pacientes=pacientes)


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
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))
    # Shell apenas: conteúdo das abas carregado via HTMX
    return render_template(
        "pacientes/detalhe.html",
        paciente=paciente,
        current_user=current_user,
    )


@paciente_bp.route(
    "/<int:paciente_id>/tab/anamnese", methods=["GET"]
)  # Tela 1
@login_required
def tab_anamnese(paciente_id: int):  # pragma: no cover - thin controller
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        return "", 404
    anamnese_alert_tipo = paciente_service.check_anamnese_alert_status(
        paciente
    )
    return render_template(
        "pacientes/_tab_anamnese.html",
        paciente=paciente,
        current_user=current_user,
        anamnese_alert_tipo=anamnese_alert_tipo,
    )


@paciente_bp.route(
    "/<int:paciente_id>/tab/planejamento", methods=["GET"]
)  # Tela 3
@login_required
def tab_planejamento(paciente_id: int):  # pragma: no cover - thin controller
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        return "", 404
    planos = get_planos_by_paciente(paciente_id)
    return render_template(
        "pacientes/_tab_planejamento.html",
        paciente=paciente,
        planos=planos,
    )


@paciente_bp.route(
    "/<int:paciente_id>/tab/financeiro", methods=["GET"]
)  # Tela 4
@login_required
def tab_financeiro(paciente_id: int):  # pragma: no cover - thin controller
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        return "", 404
    planos = get_planos_by_paciente(paciente_id)
    # Injetar info de caixa_aberto para cada plano (por data dos lançamentos)
    from app.services.financeiro_service import is_caixa_dia_aberto
    from collections import defaultdict
    caixa_status_por_data = defaultdict(lambda: True)
    for plano in planos:
        # Para cada lançamento, verificar status do caixa do dia
        caixa_aberto_lanc = []
        for lanc in getattr(plano, 'lancamentos', []):
            data_lanc = getattr(lanc, 'data_lancamento', None)
            if data_lanc:
                data_dia = data_lanc.date()
                if data_dia not in caixa_status_por_data:
                    caixa_status_por_data[data_dia] = (
                        is_caixa_dia_aberto(data_dia)
                    )
                caixa_aberto_lanc.append(caixa_status_por_data[data_dia])
            else:
                caixa_aberto_lanc.append(True)
        # Se algum lançamento do plano está com caixa aberto, permite estorno
        setattr(plano, 'caixa_aberto_lancamentos', caixa_aberto_lanc)
    return render_template(
        "pacientes/_tab_financeiro.html",
        paciente=paciente,
        planos=planos,
    )


@paciente_bp.route(
    "/<int:paciente_id>/tab/historico", methods=["GET"]
)  # Tela 5
@login_required
def tab_historico(paciente_id: int):  # pragma: no cover - thin controller
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        return "", 404
    try:
        historico = paciente.timeline_eventos.limit(100).all()
    except Exception:
        historico = []
    return render_template(
        "pacientes/_tab_historico.html",
        paciente=paciente,
        historico=historico,
    )


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
        return render_template("pacientes/_anamnese_alergias.html")
    if field == "medicamentos":
        return render_template("pacientes/_anamnese_medicamentos.html")
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
    return redirect(
        url_for("paciente_bp.detalhe", paciente_id=paciente_id)
    )


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
@dentista_required
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
