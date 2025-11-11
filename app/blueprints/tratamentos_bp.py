"""
Blueprint de Tratamentos (Catálogo Clínico) - EchoDent v4
Fase 2: Gestão do Catálogo de Procedimentos

Rotas:
- / (index) - Lista de tratamentos (todos podem ver)
- /create - Criar tratamento (apenas ADMIN)
- /update/<id> - Atualizar tratamento (apenas ADMIN)
- /delete/<id> - Soft-delete de tratamento (apenas ADMIN)
- /ajustar-precos - Modal de ajuste em massa (apenas ADMIN)
- /preview-ajuste - Preview HTMX do ajuste (apenas ADMIN)
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.services import procedimentos_service
from app.utils.decorators import admin_required

tratamentos_bp = Blueprint(
    "tratamentos_bp",
    __name__,
    url_prefix="/tratamentos",
)


@tratamentos_bp.route("/", methods=["GET"])
@login_required
def index():
    """
    Página principal de tratamentos.
    Todos os usuários autenticados podem visualizar (read-only para não-admin).
    """
    # Filtros
    categoria = request.args.get("categoria")
    ativo_param = request.args.get("ativo", "true")
    ativo = None if ativo_param == "all" else (ativo_param == "true")

    # Buscar tratamentos
    tratamentos = procedimentos_service.list_tratamentos(categoria, ativo)

    # Lista de categorias para filtros
    categorias = procedimentos_service.CATEGORIAS_FIXAS

    return render_template(
        "tratamentos/index.html",
        tratamentos=tratamentos,
        categorias=categorias,
        is_admin=(
            current_user.is_admin
            if hasattr(current_user, "is_admin")
            else False
        ),
        filtro_categoria=categoria,
        filtro_ativo=ativo_param,
    )


@tratamentos_bp.route("/create", methods=["GET", "POST"])
@login_required
@admin_required
def create():
    """Criar novo tratamento (apenas ADMIN).

    GET: Renderiza formulário de criação (modal HTMX).
    POST: Processa criação do tratamento.
    """
    if request.method == "GET":
        # Renderizar formulário de criação
        categorias = procedimentos_service.CATEGORIAS_FIXAS
        return render_template(
            "tratamentos/_form_create.html",
            categorias=categorias,
        )

    # POST: Processar criação
    data = {
        "nome": request.form.get("nome"),
        "codigo": request.form.get("codigo"),
        "categoria": request.form.get("categoria"),
        "valor_padrao": request.form.get("valor_padrao"),
        "descricao": request.form.get("descricao"),
    }

    proc = procedimentos_service.create_tratamento(data, current_user.id)

    if proc:
        flash("✅ Tratamento criado com sucesso", "success")
    else:
        flash("❌ Erro ao criar tratamento. Verifique os dados.", "error")

    return redirect(url_for("tratamentos_bp.index"))


@tratamentos_bp.route("/update/<int:proc_id>", methods=["POST"])
@login_required
@admin_required
def update(proc_id):
    """Atualizar tratamento existente (apenas ADMIN)."""
    data = {
        "nome": request.form.get("nome"),
        "codigo": request.form.get("codigo"),
        "categoria": request.form.get("categoria"),
        "valor_padrao": request.form.get("valor_padrao"),
        "descricao": request.form.get("descricao"),
    }

    proc = procedimentos_service.update_tratamento(
        proc_id,
        data,
        current_user.id,
    )

    if proc:
        flash("✅ Tratamento atualizado com sucesso", "success")
    else:
        flash("❌ Erro ao atualizar tratamento.", "error")

    return redirect(url_for("tratamentos_bp.index"))


@tratamentos_bp.route("/delete/<int:proc_id>", methods=["DELETE"])
@login_required
@admin_required
def delete(proc_id):
    """Soft-delete de tratamento (apenas ADMIN)."""
    sucesso = procedimentos_service.soft_delete_tratamento(
        proc_id,
        current_user.id,
    )

    if sucesso:
        flash("✅ Tratamento desativado com sucesso", "success")
    else:
        flash("❌ Erro ao desativar tratamento.", "error")

    return redirect(url_for("tratamentos_bp.index"))


@tratamentos_bp.route("/ajustar-precos", methods=["GET", "POST"])
@login_required
@admin_required
def ajustar_precos():
    """
    Modal de ajuste de preços em massa (apenas ADMIN).
    GET: Renderiza modal
    POST: Aplica ajuste
    """
    if request.method == "GET":
        # Renderizar modal de preview
        categorias = procedimentos_service.CATEGORIAS_FIXAS
        return render_template(
            "tratamentos/ajustar_precos.html",
            categorias=categorias,
        )

    # POST: Aplicar ajuste
    percentual = float(request.form.get("percentual", 0))
    categoria = request.form.get("categoria") or None
    confirmado = request.form.get("confirmado") == "on"

    if not confirmado:
        flash(
            "⚠️ Você precisa confirmar o ajuste marcando o checkbox",
            "warning",
        )
        return redirect(url_for("tratamentos_bp.ajustar_precos"))

    resultado = procedimentos_service.ajustar_precos_em_massa(
        percentual, categoria, current_user.id
    )

    if resultado["sucesso"]:
        flash(
            (
                f"✅ {resultado['afetados']} tratamentos atualizados "
                f"({percentual:+.1f}%)"
            ),
            "success",
        )
    else:
        flash(
            f"❌ Erro: {resultado.get('erro', 'Erro desconhecido')}",
            "error",
        )

    return redirect(url_for("tratamentos_bp.index"))


@tratamentos_bp.route("/preview-ajuste", methods=["POST"])
@login_required
@admin_required
def preview_ajuste():
    """
    Preview HTMX do ajuste de preços (retorna HTML parcial).
    Apenas ADMIN.
    """
    try:
        percentual = float(request.form.get("percentual", 0))
        categoria = request.form.get("categoria") or None

        # Simular ajuste (sem commit) para gerar preview
        # ATENÇÃO: Aqui usamos a função real mas com rollback
        # Para evitar modificar o DB, vamos buscar e calcular manualmente

        from decimal import Decimal

        from app.models import CategoriaEnum, Procedimento, db

        # Filtro base: apenas ativos
        query = db.session.query(Procedimento).filter_by(is_active=True)

        if categoria:
            try:
                categoria_enum = CategoriaEnum(categoria)
                query = query.filter_by(categoria=categoria_enum)
            except ValueError:
                pass  # Ignorar categoria inválida

        tratamentos = query.limit(10).all()  # Apenas 10 primeiros para preview
        total = query.count()

        preview = []
        for proc in tratamentos:
            preco_antigo = proc.valor_padrao
            preco_novo = preco_antigo * (1 + Decimal(percentual) / 100)
            preco_novo = preco_novo.quantize(Decimal("0.01"))

            preview.append(
                {
                    "nome": proc.nome,
                    "categoria": proc.categoria.value,
                    "preco_antigo": float(preco_antigo),
                    "preco_novo": float(preco_novo),
                }
            )

        return render_template(
            "tratamentos/_preview_ajuste.html",
            preview=preview,
            total_afetados=total,
            percentual=percentual,
        )

    except Exception as e:
        return f"<div class='alert alert-danger'>Erro: {str(e)}</div>", 500
