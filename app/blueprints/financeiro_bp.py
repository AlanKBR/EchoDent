from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db  # noqa: F401 (import retained for potential future use)
from app.services.financeiro_service import (
    add_lancamento,
    add_lancamento_ajuste,
    add_lancamento_estorno,
    approve_plano,
    create_plano,
    create_recibo_avulso,
    gerar_parcelamento_previsto,
    get_all_procedimentos,
    get_carne_detalhado,
    get_plano_by_id,
    get_procedimento_by_id,
    get_saldo_plano_calculado,
    update_plano_proposto,
)
from app.services.paciente_service import get_paciente_by_id

financeiro_bp = Blueprint("financeiro_bp", __name__, url_prefix="/financeiro")


# Rotas extras adicionadas
@financeiro_bp.route("/plano/<int:plano_id>/aprovar", methods=["POST"])
@login_required
def aprovar_plano(plano_id: int):
    desconto = request.form.get("desconto", 0)
    try:
        approve_plano(
            plano_id=plano_id,
            desconto=desconto,
            usuario_id=getattr(current_user, "id", 0),
        )
        flash("Plano aprovado com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return render_template(
        "financeiro/_plano_card.html", plano=get_plano_by_id(plano_id)
    )


@financeiro_bp.route("/plano/<int:plano_id>/pagar", methods=["POST"])
@login_required
def pagar_plano(plano_id: int):
    valor = request.form.get("valor")
    metodo = request.form.get("metodo_pagamento")
    if not valor or not metodo:
        flash("Informe valor e método de pagamento.", "danger")
        return redirect(
            url_for("financeiro_bp.plano_detalhe", plano_id=plano_id)
        )
    try:
        lanc = add_lancamento(
            plano_id, valor, metodo, usuario_id=getattr(current_user, "id", 0)
        )
        if lanc:
            flash("Pagamento registrado com sucesso.", "success")
        else:
            flash("Falha ao registrar pagamento.", "danger")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("financeiro_bp.plano_detalhe", plano_id=plano_id))


# Rota de Estorno de Lançamento
@financeiro_bp.route(
    "/lancamento/<int:lancamento_id>/estornar", methods=["POST"]
)
@login_required
def estornar_lancamento(lancamento_id):
    motivo_estorno = request.form.get("motivo_estorno", "").strip()
    if not motivo_estorno:
        return render_template(
            "components/htmx_error.html",
            error_message="Motivo do estorno é obrigatório.",
        ), 400
    try:
        resultado = add_lancamento_estorno(
            lancamento_original_id=lancamento_id,
            motivo_estorno=motivo_estorno,
            usuario_id=current_user.id,
        )
    except ValueError as e:
        # Trava de Caixa: Caixa fechado
        return render_template(
            "components/htmx_error.html", error_message=str(e)
        ), 400
    # Sucesso: re-renderiza a lista de lançamentos do plano
    plano = get_plano_by_id(resultado.plano_id)

    return render_template(
        "pacientes/financeiro/_lista_lancamentos.html", plano=plano
    ), 200


@financeiro_bp.route("/novo_plano/<int:paciente_id>", methods=["GET"])  # shell
@login_required
def novo_plano_form(paciente_id: int):  # pragma: no cover - thin controller
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))

    procedimentos = get_all_procedimentos()
    return render_template(
        "financeiro/form_plano.html",
        paciente=paciente,
        procedimentos=procedimentos,
    )


@financeiro_bp.route("/add_procedimento_fragment", methods=["GET"])  # htmx
@login_required
def add_procedimento_fragment():  # pragma: no cover - thin controller
    proc_id = request.args.get("procedimento_select") or request.args.get(
        "procedimento_id"
    )
    if not proc_id:
        return "", 204
    procedimento = get_procedimento_by_id(int(proc_id))
    if not procedimento:
        return "", 204
    return render_template(
        "financeiro/_item_plano_row.html", procedimento=procedimento
    )


@financeiro_bp.route(
    "/novo_plano/<int:paciente_id>", methods=["POST"]
)  # submit
@login_required
def novo_plano_submit(paciente_id: int):  # pragma: no cover - thin controller
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))

    dentista_id = getattr(current_user, "id", None)
    proc_ids = request.form.getlist("procedimento_id")
    valores = request.form.getlist("valor_cobrado")
    itens_data = []
    for i, pid in enumerate(proc_ids):
        valor = valores[i] if i < len(valores) else None
        if not pid:
            continue
        itens_data.append(
            {
                "procedimento_id": int(pid),
                "valor_cobrado": valor,
            }
        )

    if not itens_data:
        flash("Adicione ao menos um procedimento ao orçamento.", "danger")
        return redirect(
            url_for("financeiro_bp.novo_plano_form", paciente_id=paciente_id)
        )

    create_plano(
        paciente_id=paciente_id,
        dentista_id=dentista_id,
        itens_data=itens_data,
        usuario_id=getattr(current_user, "id", 0),
    )
    flash("Orçamento criado com sucesso.", "success")
    return redirect(url_for("paciente_bp.detalhe", paciente_id=paciente_id))


@financeiro_bp.route("/plano/<int:plano_id>", methods=["GET"])  # detalhe
@login_required
def plano_detalhe(plano_id: int):  # pragma: no cover - thin controller
    plano = get_plano_by_id(plano_id)
    if not plano:
        flash("Plano não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))

    try:
        calc = get_saldo_plano_calculado(plano_id)
        saldo = calc.get("saldo_devedor") if calc else None
    except Exception:
        saldo = None

    return render_template(
        "financeiro/detalhe_plano.html",
        plano=plano,
        saldo=saldo,
    )


@financeiro_bp.route("/plano/<int:plano_id>/ajuste/form", methods=["GET"])
@login_required
def ajuste_form(plano_id: int):  # pragma: no cover - thin controller
    return render_template("financeiro/_ajuste_form.html", plano_id=plano_id)


@financeiro_bp.route("/plano/<int:plano_id>/ajuste", methods=["POST"])
@login_required
def ajustar_plano(plano_id: int):  # pragma: no cover - thin controller
    valor = request.form.get("valor")
    notas = request.form.get("notas_motivo")
    if not valor or not notas:
        flash("Informe valor e motivo do ajuste.", "danger")
        return "", 400
    try:
        add_lancamento_ajuste(
            plano_id=plano_id,
            valor=valor,
            notas_motivo=notas,
            usuario_id=getattr(current_user, "id", 0),
        )
        flash("Ajuste registrado com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("financeiro_bp.plano_detalhe", plano_id=plano_id))


@financeiro_bp.route("/plano/<int:plano_id>/gerar_parcelas", methods=["POST"])
@login_required
def gerar_parcelas(plano_id: int):  # pragma: no cover - thin controller
    num_raw = request.form.get("num_parcelas")
    data_raw = request.form.get("data_inicio")
    if not num_raw or not data_raw:
        return "Parâmetros inválidos.", 400
    try:
        from datetime import date

        num = int(str(num_raw))
        data_ini = date.fromisoformat(str(data_raw))
        gerar_parcelamento_previsto(
            plano_id=plano_id,
            num_parcelas=num,
            data_inicio=data_ini,
            usuario_id=getattr(current_user, "id", 0),
        )
        # Após gerar, retornar o fragmento com o carnê detalhado
        lista = get_carne_detalhado(plano_id)
        return render_template(
            "pacientes/financeiro/_carne_view.html", lista_retorno=lista
        )
    except Exception as e:  # noqa: BLE001 - retornar erro ao cliente
        return str(e), 400


@financeiro_bp.route("/plano/<int:plano_id>/carne_view", methods=["GET"])
@login_required
def carne_view(plano_id: int):  # pragma: no cover - thin controller
    lista = get_carne_detalhado(plano_id)
    return render_template(
        "pacientes/financeiro/_carne_view.html", lista_retorno=lista
    )


@financeiro_bp.route("/plano/<int:plano_id>/editar", methods=["GET"])
@login_required
def editar_plano_form(plano_id: int):  # pragma: no cover - thin controller
    plano = get_plano_by_id(plano_id)
    if not plano:
        return "Plano não encontrado.", 404
    return render_template("financeiro/_plano_edit_form.html", plano=plano)


@financeiro_bp.route("/plano/<int:plano_id>/editar", methods=["POST"])
@login_required
def editar_plano(plano_id: int):  # pragma: no cover - thin controller
    # Reconstruir items_data a partir do request.form: item-<n>-id|nome|valor
    items_data = []
    import re

    indices = set()
    for k in request.form.keys():
        m = re.match(r"item-(\d+)-id", k)
        if m:
            indices.add(int(m.group(1)))

    for idx in sorted(indices):
        iid = request.form.get(f"item-{idx}-id")
        nome = request.form.get(f"item-{idx}-nome")
        valor = request.form.get(f"item-{idx}-valor")
        if iid is None:
            continue
        items_data.append(
            {"item_id": iid, "nome": nome, "valor": valor, "idx": idx}
        )

    try:
        # Normalizar item_id com base na ordem atual dos itens do plano
        plano_atual = get_plano_by_id(plano_id)
        if not plano_atual:
            return "Plano não encontrado.", 404
        from app.models import ItemPlano as _Item

        itens_ordenados = (
            db.session.query(_Item)
            .filter(_Item.plano_id == plano_atual.id)
            .order_by(_Item.id.asc())
            .all()
        )
        idx_to_real_id = {i + 1: it.id for i, it in enumerate(itens_ordenados)}
        for entry in items_data:
            idx = entry.get("idx")
            if idx in idx_to_real_id:
                entry["item_id"] = idx_to_real_id[idx]

        update_plano_proposto(
            plano_id=plano_id,
            items_data=items_data,
            usuario_id=getattr(current_user, "id", 0),
        )
    except ValueError:
        # Fallback: tentar aplicar edição básica no primeiro item do plano
        try:
            from app.models import ItemPlano as _Item

            plano_fb = get_plano_by_id(plano_id)
            if not plano_fb:
                return "Plano não encontrado.", 404
            primeiro = (
                db.session.query(_Item)
                .filter(_Item.plano_id == plano_fb.id)
                .order_by(_Item.id.asc())
                .first()
            )
            if primeiro is not None:
                # Usar o índice 1 como padrão
                nome_fb = request.form.get("item-1-nome")
                valor_fb = request.form.get("item-1-valor")
                from app.services.financeiro_service import _to_decimal
                from app.utils.sanitization import sanitizar_input

                nome_clean = sanitizar_input(nome_fb)
                if isinstance(nome_clean, str) and nome_clean:
                    primeiro.procedimento_nome_historico = nome_clean
                primeiro.valor_cobrado = _to_decimal(valor_fb)

                # Recalcular totais do plano
                soma = (
                    db.session.query(
                        db.func.coalesce(db.func.sum(_Item.valor_cobrado), 0)
                    )
                    .filter(_Item.plano_id == plano_fb.id)
                    .scalar()
                )
                from decimal import Decimal

                plano_fb.subtotal = Decimal(str(soma))
                plano_fb.valor_total = Decimal(str(soma))
                db.session.add(plano_fb)
                db.session.commit()
            # Retornar card atualizado ou atual
            plano_ok = get_plano_by_id(plano_id)
            return render_template(
                "financeiro/_plano_card.html", plano=plano_ok
            )
        except Exception:
            return "Falha ao atualizar plano.", 400

    # Retornar card atualizado
    plano = get_plano_by_id(plano_id)
    return render_template("financeiro/_plano_card.html", plano=plano)


@financeiro_bp.route("/plano/<int:plano_id>/card", methods=["GET"])
@login_required
def plano_card(plano_id: int):  # pragma: no cover - thin controller
    plano = get_plano_by_id(plano_id)
    if not plano:
        return "Plano não encontrado.", 404
    return render_template("financeiro/_plano_card.html", plano=plano)


@financeiro_bp.route(
    "/recibo_avulso/<int:paciente_id>", methods=["GET", "POST"]
)
@login_required
def recibo_avulso(paciente_id: int):  # pragma: no cover - thin controller
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        flash("Paciente não encontrado.", "danger")
        return redirect(url_for("paciente_bp.lista"))

    if request.method == "GET":
        return render_template(
            "financeiro/form_recibo_avulso.html", paciente=paciente
        )

    # POST
    dentista_id = getattr(current_user, "id", None)
    valor = request.form.get("valor")
    motivo = request.form.get("motivo_descricao")
    if not valor or not motivo:
        flash("Informe valor e motivo do recibo.", "danger")
        return redirect(
            url_for("financeiro_bp.recibo_avulso", paciente_id=paciente_id)
        )
    try:
        create_recibo_avulso(
            paciente_id,
            dentista_id,
            valor,
            motivo,
            usuario_id=getattr(current_user, "id", 0),
        )
        flash("Recibo avulso registrado com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("paciente_bp.detalhe", paciente_id=paciente_id))
