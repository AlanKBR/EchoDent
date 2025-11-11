"""Blueprint para o menu de Configurações (Settings).

Estrutura de abas:
- /settings -> Hub com tabs (SaaS-style)
- /settings/clinica -> Dados da clínica (admin pode editar, outros read-only)
- /settings/tema -> Customização de cores e tema
- /settings/usuario -> Preferências do usuário logado
- /settings/admin -> Painel admin (gestão usuários, devlogs, backups, etc.)
"""

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.models import RoleEnum, Usuario
from app.services import (
    audit_service,  # Fase 4.4 (Timeline)
    clinica_service,
    log_service,
    storage_service,
    theme_service,
    user_preferences_service,
)
from app.utils.decorators import admin_required

settings_bp = Blueprint("settings_bp", __name__, url_prefix="/settings")


# ============================================================================
# HUB (Landing page com tabs)
# ============================================================================


@settings_bp.route("/", methods=["GET"])
@login_required
def hub():
    """Hub central de configurações com navegação por abas."""
    # Redireciona para a primeira aba relevante
    return redirect(url_for("settings_bp.clinica"))


# ============================================================================
# ABA: Clínica
# ============================================================================


@settings_bp.route("/clinica", methods=["GET"])
@login_required
def clinica():
    """Tela de configurações da clínica (admin edita, outros visualizam)."""
    info = clinica_service.get_or_create_clinica_info()
    # Calcular status de completude
    config_status = clinica_service.get_config_completeness()
    return render_template(
        "settings/clinica.html",
        info=info,
        is_admin=current_user.is_admin,
        config_status=config_status,
    )


@settings_bp.route("/clinica/update", methods=["POST"])
@login_required
@admin_required
def clinica_update():
    """Atualiza informações da clínica (apenas admin)."""
    try:
        print("\n===== clinica_update() CHAMADA =====")
        print(f"Form data keys: {list(request.form.keys())}")

        data = {
            "nome_clinica": request.form.get("nome_clinica"),
            "cnpj": request.form.get("cnpj"),
            "cro_clinica": request.form.get("cro_clinica"),
            "telefone": request.form.get("telefone"),
            "email": request.form.get("email"),
            "cep": request.form.get("cep"),
            "logradouro": request.form.get("logradouro"),
            "numero": request.form.get("numero"),
            "complemento": request.form.get("complemento"),
            "bairro": request.form.get("bairro"),
            "cidade": request.form.get("cidade"),
            "estado": request.form.get("estado"),
        }

        # Horário de funcionamento (JSON simplificado)
        # Ex: seg_inicio, seg_fim, ter_inicio, ter_fim, etc.
        horario = {}
        dias = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
        for dia in dias:
            inicio = request.form.get(f"{dia}_inicio")
            fim = request.form.get(f"{dia}_fim")
            if inicio and fim:
                horario[dia] = f"{inicio}-{fim}"
            else:
                horario[dia] = None

        data["horario_funcionamento"] = horario

        result = clinica_service.update_clinica_info(data)
    except Exception as e:
        print(f"\n💥 EXCEPTION NO BLUEPRINT: {type(e).__name__}: {str(e)}")
        import traceback

        traceback.print_exc()
        flash(f"Erro técnico: {str(e)}", "error")
        return redirect(url_for("settings_bp.clinica"))

    # Fase 4.2: Retornar Toast Rollback via HTMX OOB
    if result["success"]:
        # Preparar dados para o toast
        undo_data = {
            "record_id": result.get("record_id"),
            "previous_state": result.get("previous_state", {}),
            "message": "Configurações atualizadas!",
            "rollback_url": url_for("settings_bp.clinica_rollback"),
        }

        # Retornar template do toast para HTMX injetar
        return render_template(
            "settings/_undo_toast_response.html", undo_data=undo_data
        ), 200
    else:
        # Em caso de erro, retornar mensagem simples
        flash("Erro ao atualizar informações da clínica.", "error")
        return redirect(url_for("settings_bp.clinica"))


@settings_bp.route("/clinica/rollback", methods=["POST"])
@login_required
@admin_required
def clinica_rollback():
    """Desfaz a última atualização da clínica (Fase 4.2)."""
    result = clinica_service.rollback_clinica_info()

    # Fase 4.2: Retornar resposta vazia para HTMX (apenas limpa o toast)
    # O rollback recarrega automaticamente a página via HX-Refresh header
    if result["success"]:
        # Retornar vazio para limpar container do toast + trigger reload
        return "", 200, {"HX-Refresh": "true"}
    else:
        # Em caso de erro, retornar mensagem
        msg = f'<div class="alert alert-danger">{result["message"]}</div>'
        return msg, 400


@settings_bp.route("/clinica/upload_logo", methods=["POST"])
@login_required
@admin_required
def clinica_upload_logo():
    """Upload de logo (cabeçalho, rodapé, marca d'água, favicon)."""
    logo_type = request.form.get("logo_type")  # cabecalho, rodape, etc.
    file = request.files.get("logo_file")

    if not logo_type or logo_type not in [
        "cabecalho",
        "rodape",
        "marca_dagua",
        "favicon",
    ]:
        flash("Tipo de logo inválido.", "error")
        return redirect(url_for("settings_bp.clinica"))

    if not file or file.filename == "":
        flash("Nenhum arquivo selecionado.", "error")
        return redirect(url_for("settings_bp.clinica"))

    # Salvar arquivo usando storage_service
    try:
        # Determinar subpasta
        subfolder = f"clinica/{logo_type}"
        filename = secure_filename(file.filename)

        # Salvar arquivo
        file_path = storage_service.salvar_arquivo(
            file, subfolder=subfolder, filename=filename
        )

        # Atualizar path no banco
        clinica_service.update_logo_path(logo_type, file_path)

        flash(f"Logo ({logo_type}) enviado com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao enviar logo: {str(e)}", "error")

    return redirect(url_for("settings_bp.clinica"))


@settings_bp.route("/clinica/remove_logo/<logo_type>", methods=["DELETE"])
@login_required
@admin_required
def clinica_remove_logo(logo_type):
    """Remove logo (soft-delete: apenas limpa o path no banco)."""
    if logo_type not in ["cabecalho", "rodape", "marca_dagua", "favicon"]:
        flash("Tipo de logo inválido.", "error")
        return redirect(url_for("settings_bp.clinica"))

    try:
        # Limpar path no banco (soft-delete, arquivo permanece em disco)
        clinica_service.update_logo_path(logo_type, None)
        flash(f"Logo ({logo_type}) removido com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao remover logo: {str(e)}", "error")

    return redirect(url_for("settings_bp.clinica"))


# ============================================================================
# ABA: Tema
# ============================================================================


@settings_bp.route("/tema", methods=["GET"])
@login_required
def tema():
    """Tela de configurações de tema/estética (todos podem editar)."""
    theme_settings = theme_service.get_theme_settings()
    return render_template("settings/tema.html", theme=theme_settings)


@settings_bp.route("/tema/update", methods=["POST"])
@login_required
def tema_update():
    """Atualiza configurações de tema."""
    data = {
        "primary_color": request.form.get("primary_color"),
        "secondary_color": request.form.get("secondary_color"),
        "use_system_color": request.form.get("use_system_color") == "on",
    }

    success, message = theme_service.update_theme_settings(data)
    flash(message, "success" if success else "error")

    return redirect(url_for("settings_bp.tema"))


# ============================================================================
# ABA: Usuário (Preferências Pessoais)
# ============================================================================


@settings_bp.route("/usuario", methods=["GET"])
@login_required
def usuario():
    """Tela de preferências do usuário logado."""
    prefs = user_preferences_service.get_or_create_user_preferences(
        current_user.id
    )
    return render_template(
        "settings/usuario.html", prefs=prefs, user=current_user
    )


@settings_bp.route("/usuario/update", methods=["POST"])
@login_required
def usuario_update():
    """Atualiza preferências do usuário logado."""
    data = {
        "notificacoes_enabled": request.form.get("notificacoes_enabled")
        == "on",
    }

    success = user_preferences_service.update_user_preferences(
        current_user.id, data
    )
    if success:
        flash("Preferências atualizadas com sucesso!", "success")
    else:
        flash("Erro ao atualizar preferências.", "error")

    return redirect(url_for("settings_bp.usuario"))


@settings_bp.route("/usuario/update_color", methods=["POST"])
@login_required
def usuario_update_color():
    """Atualiza a cor do profissional na agenda (Usuario.color)."""
    color = request.form.get("color", "").strip()

    # Validação básica de cor hex
    if color and not theme_service.is_valid_hex_color(color):
        flash("Cor inválida (use formato #RRGGBB).", "error")
        return redirect(url_for("settings_bp.usuario"))

    try:
        user = db.session.get(Usuario, current_user.id)
        user.color = color if color else None
        db.session.commit()
        flash("Cor do profissional atualizada!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao atualizar cor: {str(e)}", "error")

    return redirect(url_for("settings_bp.usuario"))


# ============================================================================
# ABA: Admin (apenas para admins)
# ============================================================================


@settings_bp.route("/admin", methods=["GET"])
@login_required
@admin_required
def admin_panel():
    """Painel administrativo: gestão de usuários, devlogs, backups, etc."""
    # Listar usuários ativos
    usuarios = Usuario.query.filter_by(is_active=True).all()

    # Estatísticas de devlogs
    total_logs = log_service.get_total_logs_count()

    return render_template(
        "settings/admin.html",
        usuarios=usuarios,
        total_logs=total_logs,
        audit_service=audit_service,  # Para timeline (Fase 4.4)
    )


# --- Gestão de Usuários ---


@settings_bp.route("/admin/usuarios/criar", methods=["POST"])
@login_required
@admin_required
def admin_criar_usuario():
    """Cria um novo usuário (thin controller)."""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    role_str = request.form.get("role", "").strip()
    nome_completo = request.form.get("nome_completo", "").strip()

    try:
        if not username or not password or not role_str:
            raise ValueError("Preencha todos os campos obrigatórios.")

        role = RoleEnum(role_str)

        # Verifica se username já existe
        if Usuario.query.filter_by(username=username).first():
            raise ValueError(f"Username '{username}' já existe.")

        from werkzeug.security import generate_password_hash

        novo_usuario = Usuario(
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
            nome_completo=nome_completo,
        )
        db.session.add(novo_usuario)
        db.session.commit()

        flash(f"Usuário '{username}' criado com sucesso!", "success")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao criar usuário: {str(e)}", "error")

    return redirect(url_for("settings_bp.admin_panel"))


@settings_bp.route("/admin/usuarios/<int:user_id>/desativar", methods=["POST"])
@login_required
@admin_required
def admin_desativar_usuario(user_id: int):
    """Desativa um usuário (soft-delete)."""
    try:
        user = db.session.get(Usuario, user_id)
        if not user:
            raise ValueError("Usuário não encontrado.")

        if user.id == current_user.id:
            raise ValueError("Você não pode desativar a si mesmo.")

        user.is_active = False
        db.session.commit()
        flash(f"Usuário '{user.username}' desativado.", "success")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao desativar usuário: {str(e)}", "error")

    return redirect(url_for("settings_bp.admin_panel"))


# --- Dev Logs (migrado de admin_bp) ---


@settings_bp.route("/admin/devlogs", methods=["GET"])
@login_required
@admin_required
def devlogs():
    """Lista de logs de desenvolvedor (paginada)."""
    page = request.args.get("page", 1, type=int)
    per_page = 25
    pagination = log_service.get_logs_paginated(page=page, per_page=per_page)
    return render_template("settings/devlogs.html", pagination=pagination)


@settings_bp.route("/admin/devlogs/<int:log_id>", methods=["GET"])
@login_required
@admin_required
def view_log_detail(log_id: int):
    """Detalhe de um log específico."""
    log = log_service.get_log_by_id(log_id)
    if not log:
        abort(404)
    return render_template("settings/devlog_detail.html", log=log)


@settings_bp.route("/admin/devlogs/purge", methods=["POST"])
@login_required
@admin_required
def purge_devlogs():
    """Purga todos os logs de desenvolvedor."""
    log_service.purge_all_logs()
    return ("", 204, {"HX-Redirect": url_for("settings_bp.devlogs")})


# --- Configurações Globais (DEV_LOGS_ENABLED, ASSET_VERSION) ---


@settings_bp.route("/admin/global_settings", methods=["GET"])
@login_required
@admin_required
def global_settings():
    """Tela de configurações globais (migrado de admin_bp.configuracoes)."""
    from app.services import settings_service

    settings = settings_service.get_all_settings()
    return render_template("settings/global_settings.html", settings=settings)


@settings_bp.route("/admin/global_settings/update", methods=["POST"])
@login_required
@admin_required
def global_settings_update():
    """Atualiza configurações globais."""
    from app.services import settings_service

    settings_service.update_settings_bulk(request.form.to_dict())
    return Response(
        status=204,
        headers={"HX-Redirect": url_for("settings_bp.global_settings")},
    )


# ============================================================================
# Rotas de Integrações (API Keys)
# ============================================================================


@settings_bp.route("/integrations", methods=["GET"])
@login_required
@admin_required
def integrations():
    """
    Página de configuração de integrações de API.
    Apenas ADMIN pode visualizar e editar tokens.
    """
    from app.services import api_keys_service

    # Buscar todas as keys conhecidas
    api_keys_data = api_keys_service.list_api_keys()

    # Converter para dict {key_name: masked_value} para facilitar template
    api_keys = {}
    for item in api_keys_data:
        # Se configurado, exibir valor mascarado (para preencher placeholder)
        # Se não configurado, deixar vazio
        if item["configured"]:
            api_keys[item["key_name"]] = item["masked_value"]
        else:
            api_keys[item["key_name"]] = ""

    return render_template("settings/integrations.html", api_keys=api_keys)


@settings_bp.route("/integrations/save/<api_name>", methods=["POST"])
@login_required
@admin_required
def integrations_save(api_name):
    """
    Salva token de uma API específica.

    Args:
        api_name: Identificador da API ("brasilapi", "gateway_pagamento")
    """
    from app.services import api_keys_service

    if api_name == "brasilapi":
        token = request.form.get("token", "").strip()
        sucesso = api_keys_service.set_api_key(
            api_keys_service.API_KEY_BRASILAPI, token or None
        )

        if sucesso:
            flash("✅ Token BrasilAPI salvo com sucesso!", "success")
        else:
            flash("❌ Erro ao salvar token BrasilAPI.", "error")

    elif api_name == "gateway_pagamento":
        token = request.form.get("token", "").strip()
        secret = request.form.get("secret", "").strip()

        sucesso_token = api_keys_service.set_api_key(
            api_keys_service.API_KEY_GATEWAY_PAGAMENTO_TOKEN, token or None
        )
        sucesso_secret = api_keys_service.set_api_key(
            api_keys_service.API_KEY_GATEWAY_PAGAMENTO_SECRET, secret or None
        )

        if sucesso_token and sucesso_secret:
            flash("✅ Tokens do Gateway salvos com sucesso!", "success")
        else:
            flash("❌ Erro ao salvar tokens do Gateway.", "error")

    else:
        flash("⚠️ API desconhecida.", "warning")

    return redirect(url_for("settings_bp.integrations"))


@settings_bp.route("/integrations/test/<api_name>", methods=["POST"])
@login_required
@admin_required
def integrations_test(api_name):
    """
    Testa conexão com uma API externa (HTMX).

    Args:
        api_name: Identificador da API ("brasilapi", "gateway_pagamento")

    Returns:
        HTML fragment com resultado do teste
    """
    from app.services import api_keys_service

    result = api_keys_service.test_api_connection(api_name)

    return render_template(
        "settings/_integration_test_result.html", result=result
    )


# ============================================================================
# AUDIT LOGS (Fase 4.1)
# ============================================================================


@settings_bp.route("/admin/audit-logs", methods=["GET"])
@login_required
@admin_required
def audit_logs():
    """
    Listagem paginada de logs de auditoria com filtros.

    Query params:
        - page: Número da página (default: 1)
        - user_id: Filtro por usuário
        - model_name: Filtro por tabela
        - action: Filtro por ação (create, update, delete)
        - date_from: Data inicial (YYYY-MM-DD)
        - date_to: Data final (YYYY-MM-DD)
    """
    from datetime import datetime

    from app.services import audit_service

    # Parâmetros de filtro
    page = request.args.get("page", 1, type=int)
    user_id = request.args.get("user_id", type=int)
    model_name = request.args.get("model_name")
    action = request.args.get("action")

    # Datas
    date_from = None
    date_to = None
    if request.args.get("date_from"):
        try:
            date_from = datetime.strptime(
                request.args.get("date_from"), "%Y-%m-%d"
            )
        except ValueError:
            pass

    if request.args.get("date_to"):
        try:
            date_to = datetime.strptime(
                request.args.get("date_to"), "%Y-%m-%d"
            )
        except ValueError:
            pass

    # Buscar logs
    pagination = audit_service.list_audit_logs(
        page=page,
        per_page=30,
        user_id=user_id,
        model_name=model_name,
        action=action,
        date_from=date_from,
        date_to=date_to,
    )

    # Buscar usuários para filtro
    usuarios = (
        db.session.query(Usuario)
        .filter(Usuario.is_active == True)  # noqa: E712
        .all()
    )

    return render_template(
        "settings/audit_logs.html",
        pagination=pagination,
        usuarios=usuarios,
        audit_service=audit_service,
    )


@settings_bp.route("/admin/audit-logs/<int:log_id>", methods=["GET"])
@login_required
@admin_required
def audit_log_detail(log_id):
    """
    Detalhamento de um log de auditoria específico (modal HTMX).

    Args:
        log_id: ID do log

    Returns:
        HTML fragment com modal de detalhes
    """
    from app.services import audit_service

    log = audit_service.get_audit_log_by_id(log_id)

    if not log:
        return "<div class='alert alert-danger'>Log não encontrado.</div>", 404

    return render_template(
        "settings/_audit_log_detail.html",
        log=log,
        audit_service=audit_service,
    )
