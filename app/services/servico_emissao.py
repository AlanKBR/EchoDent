from __future__ import annotations

import jinja2
from typing import Any, Mapping

from .. import db
from ..models import LogEmissao, Paciente, Usuario, TemplateDocumento
from ..utils.sanitization import sanitizar_input

# Ambiente Jinja independente/tolerante para renderização a partir de strings
# de template vindas do banco de dados (sem depender do loader de arquivos).
motor_jinja_tolerante = jinja2.Environment(
    # Undefined silently renders as empty string in standard Undefined
    undefined=jinja2.Undefined,
    loader=jinja2.BaseLoader(),
)


def renderizar_documento_html(log_emissao_id: int) -> str:
    """Renderiza HTML do documento (window.print) a partir de um LogEmissao.

    - Busca o LogEmissao e o TemplateDocumento associado
        - Constrói o contexto mesclando dados do domínio com dados_chave
            (dados_chave tem prioridade)
    - Renderiza usando um Environment Jinja tolerante (SilentUndefined)
    """
    try:
        log = db.session.get(LogEmissao, log_emissao_id)
        if not log:
            raise ValueError("LogEmissao não encontrado")

        template_string = (log.template.template_jinja or "").strip()
        if not template_string:
            raise ValueError("Template do documento está vazio")

        # Contexto padrão do domínio
        contexto: dict[str, Any] = {
            "paciente": log.paciente,
            "usuario": log.usuario,
            "log": log,
        }
        # Mescla dados_chave com prioridade
        try:
            dados_chave: Mapping[str, Any] = (log.dados_chave or {})
            contexto.update(dados_chave)
        except Exception:
            # Se dados_chave não for mapeável, ignora silenciosamente
            pass

        template = motor_jinja_tolerante.from_string(template_string)
        html_renderizado = template.render(contexto)
        return html_renderizado

    except ValueError:
        # Propaga erros de domínio controlados
        raise
    except jinja2.TemplateSyntaxError as e:
        raise ValueError(f"Erro de sintaxe no template: {e}")
    except Exception as e:
        raise ValueError(f"Falha ao renderizar documento: {e}")


def criar_log_emissao(
    paciente_id: int,
    usuario_id: int,
    template_id: int,
    dados_chave: dict | None,
) -> int:
    """Cria um LogEmissao de forma atômica e retorna seu ID (int).

    Regras aplicadas:
    - Atomicidade (try/commit/rollback) conforme Regra 7 do AGENTS.MD.
    - Sanitização de campos livres via utils.sanitizar_input em dados_chave.
    - Validação de FKs (paciente/usuário/template devem existir).
    - Sem DDL em runtime: caso a tabela não exista, a exceção é propagada.
    """
    try:
        # Valida FKs
        paciente = db.session.get(Paciente, paciente_id)
        if not paciente:
            raise ValueError("Paciente não encontrado")

        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
            raise ValueError("Usuário não encontrado")

        template = db.session.get(TemplateDocumento, template_id)
        if not template:
            raise ValueError("TemplateDocumento não encontrado")

        # Sanitiza dados_chave (campos livres)
        dados_sanitizados: dict[str, Any] = {}
        if dados_chave:
            for k, v in dict(dados_chave).items():
                dados_sanitizados[k] = sanitizar_input(v)

        novo_log = LogEmissao(
            template_id=template.id,
            paciente_id=paciente.id,
            usuario_id=usuario.id,
            dados_chave=dados_sanitizados,
        )
        db.session.add(novo_log)
        # Garante que ID foi gerado antes do commit e evita SELECT pós-commit
        db.session.flush()
        new_id = int(getattr(novo_log, "id"))
        db.session.commit()
        return new_id
    except Exception:
        db.session.rollback()
        raise
