from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    Response,
)
from flask_login import login_required, current_user
from decimal import Decimal
from datetime import datetime
from app.services import financeiro_service
from app.services import settings_service
from app.services import log_service
from app.utils.decorators import admin_required

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/admin")


@admin_bp.route("/caixa/fechar", methods=["GET"])
@login_required
@admin_required
def fechar_caixa_form():
    return render_template("admin/_fechamento_caixa_form.html")


@admin_bp.route("/caixa/fechar", methods=["POST"])
@login_required
@admin_required
def fechar_caixa_submit():
    data_caixa = request.form.get("data_caixa")
    saldo_apurado = request.form.get("saldo_apurado")
    try:
        if not data_caixa or not saldo_apurado:
            raise ValueError("Preencha todos os campos.")
        # Converter data e saldo
        data_caixa = datetime.strptime(data_caixa, "%Y-%m-%d").date()
        saldo_apurado = Decimal(saldo_apurado)
        financeiro_service.fechar_caixa_dia(
            data_caixa=data_caixa,
            saldo_apurado=saldo_apurado,
            usuario_id=current_user.id
        )
        flash("Caixa fechado com sucesso!", "success")
        return redirect(url_for("admin_bp.fechar_caixa_form"))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("admin_bp.fechar_caixa_form"))


@admin_bp.route("/configuracoes", methods=["GET"])
@login_required
@admin_required
def configuracoes():
    # Inicializar configurações padrão se não existirem
    settings_service.initialize_default_settings()
    settings = settings_service.get_all_settings()
    return render_template("admin/configuracoes.html", settings=settings)


@admin_bp.route("/configuracoes/update", methods=["POST"])
@login_required
@admin_required
def configuracoes_update():
    # Atualização atômica em lote (whitelist e sanitização no service)
    settings_service.update_settings_bulk(request.form.to_dict())
    flash("Configurações salvas com sucesso!", "success")
    # Resposta HTMX: redireciona para recarregar a página
    return Response(
        status=204,
        headers={"HX-Redirect": url_for("admin_bp.configuracoes")},
    )


@admin_bp.route("/theme.css", methods=["GET"])
def theme_css():
    """Gera CSS dinâmico com as cores de tema personalizadas."""
    primary_color = settings_service.get_setting("THEME_PRIMARY_COLOR", "#10b981")
    
    # Helper para gerar variações de cor (light e dark)
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def adjust_brightness(rgb, factor):
        return tuple(max(0, min(255, int(c * factor))) for c in rgb)
    
    def rgb_to_hex(rgb):
        return '#{:02x}{:02x}{:02x}'.format(*rgb)
    
    try:
        rgb = hex_to_rgb(primary_color)
        light_rgb = adjust_brightness(rgb, 1.2)
        dark_rgb = adjust_brightness(rgb, 0.8)
        
        primary_light = rgb_to_hex(light_rgb)
        primary_dark = rgb_to_hex(dark_rgb)
    except:
        # Fallback para cores padrão
        primary_color = "#10b981"
        primary_light = "#34d399"
        primary_dark = "#059669"
    
    css_content = f"""
/* CSS dinâmico gerado a partir das configurações */
:root {{
    --color-primary-light: {primary_light};
    --color-primary-main:  {primary_color};
    --color-primary-dark:  {primary_dark};
}}
"""
    
    return Response(css_content, mimetype='text/css')


@admin_bp.route("/devlogs", methods=["GET"])
@login_required
@admin_required
def devlogs():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    pagination = log_service.get_logs_paginated(page=page, per_page=per_page)
    return render_template("admin/devlogs.html", pagination=pagination)


# Rota de detalhe de log
@admin_bp.route("/devlogs/<int:log_id>", methods=["GET"])
@login_required
@admin_required
def view_log_detail(log_id):
    log = log_service.get_log_by_id(log_id)
    if not log:
        abort(404)
    return render_template("admin/devlog_detail.html", log=log)


@admin_bp.route("/devlogs/purge", methods=["POST"])
@login_required
@admin_required
def purge_devlogs():
    log_service.purge_all_logs()
    # Resposta HTMX: redireciona para recarregar a página de logs
    return ('', 204, {"HX-Redirect": "/admin/devlogs"})
