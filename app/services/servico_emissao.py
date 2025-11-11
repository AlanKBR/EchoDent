from __future__ import annotations

import re
from collections.abc import Mapping
from string import Template
from typing import Any

from .. import db
from ..models import LogEmissao, Paciente, RoleEnum, TemplateDocumento, Usuario
from ..utils.sanitization import sanitizar_input

# ------------------------------
# Parser de variáveis dinâmicas
# ------------------------------

GLOBAIS_SUPORTADAS: set[str] = {
    # Paciente
    "paciente_nome",
    "paciente_cpf",
    "paciente_email",
    "paciente_telefone",
    # Dentista responsável
    "dentista_nome",
    "dentista_cro",
    # Emissão
    "data_emissao",
}


def parse_campos_dinamicos(template_string: str) -> list[str]:
    """Extrai variáveis $var do template, excluindo as globais conhecidas.

    Retorna lista ordenada e única dos nomes (sem o prefixo '$').
    """
    if not template_string:
        return []
    # Captura $variavel (evita $$ de escape do Template)
    vars_encontradas = set(
        m.group("var")
        for m in re.finditer(
            r"\$(?P<var>[a-zA-Z_][a-zA-Z0-9_]*)",
            template_string,
        )
    )
    # Remove as globais suportadas
    dinamicas = [v for v in vars_encontradas if v not in GLOBAIS_SUPORTADAS]
    dinamicas.sort()
    return dinamicas


# ------------------------------
# Renderização usando string.Template
# ------------------------------


def _construir_contexto_globais(log: LogEmissao) -> dict[str, Any]:
    paciente = getattr(log, "paciente", None)
    dentista = getattr(log, "dentista_responsavel", None)
    data_emissao = getattr(log, "data_emissao", None)
    ctx: dict[str, Any] = {}
    try:
        if paciente:
            ctx["paciente_nome"] = paciente.nome_completo or ""
            ctx["paciente_cpf"] = paciente.cpf or ""
            ctx["paciente_email"] = paciente.email or ""
            ctx["paciente_telefone"] = paciente.telefone or ""
    except Exception:
        pass
    try:
        if dentista:
            ctx["dentista_nome"] = dentista.nome_completo or ""
            ctx["dentista_cro"] = dentista.cro_registro or ""
    except Exception:
        pass
    try:
        if data_emissao is not None:
            # ISO curto; formatação rica pode ser via filtro Jinja na
            # print_page
            ctx["data_emissao"] = str(data_emissao)
    except Exception:
        pass
    return ctx


# Conjunto de blocos condicionais suportados -> função(ctx) -> string
def _blo_co_cid(ctx: Mapping[str, Any]) -> str:
    cid = (ctx.get("cid_code") or ctx.get("cid") or "").strip()
    if cid:
        return f"<p><strong>CID:</strong> {cid}</p>"
    return ""


_BLOCOS_CONDICIONAIS: dict[str, callable] = {
    "__BLOCO_CID__": _blo_co_cid,
}


def _aplicar_blocos_condicionais(
    template_str: str, ctx: Mapping[str, Any]
) -> str:
    """Aplica substituições simples de blocos condicionais.

    Cada marcador __BLOCO_X__ é substituído pelo resultado da função
    correspondente; se não existir função, permanece como está (para lint).
    """
    for marcador, func in _BLOCOS_CONDICIONAIS.items():
        try:
            if marcador in template_str:
                template_str = template_str.replace(marcador, str(func(ctx)))
        except Exception:
            # Fail-safe: remove marcador se função falhar
            template_str = template_str.replace(marcador, "")
    return template_str


def renderizar_documento_html(log_emissao_id: int) -> str:
    """Renderiza HTML do documento (window.print) a partir de um LogEmissao.

    - Busca o LogEmissao e o TemplateDocumento associado
    - Constrói o contexto flatten (Globais + dados_chave)
    - Aplica blocos condicionais e substitui variáveis com string.Template
    """
    try:
        log = db.session.get(LogEmissao, log_emissao_id)
        if not log:
            raise ValueError("LogEmissao não encontrado")

        template_string = (
            getattr(log.template, "template_body", "") or ""
        ).strip()
        if not template_string:
            raise ValueError("Template do documento está vazio")

        globais = _construir_contexto_globais(log)
        dados_chave: Mapping[str, Any]
        try:
            dados_chave = log.dados_chave or {}
        except Exception:
            dados_chave = {}

        # Merge com prioridade para dinâmicos
        contexto_final = dict(globais)
        try:
            contexto_final.update(dados_chave)
        except Exception:
            pass

        # Aplica blocos condicionais antes da substituição de variáveis
        pre = _aplicar_blocos_condicionais(template_string, contexto_final)

        # Renderização segura (variáveis ausentes viram string vazia)
        html_renderizado = Template(pre).safe_substitute(contexto_final)
        return html_renderizado

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Falha ao renderizar documento: {e}")


def criar_log_emissao(
    paciente_id: int,
    usuario_id: int,
    template_id: int,
    dados_chave: dict | None,
    dentista_responsavel_id: int,
) -> int:
    """Cria um LogEmissao de forma atômica e retorna seu ID (int).

    Regras aplicadas:
    - Atomicidade (try/commit/rollback) conforme Regra 7 do AGENTS.MD.
    - Sanitização de campos livres via utils.sanitizar_input em dados_chave.
        - Validação de FKs (paciente/usuário/template/dentista) e de papel do
            dentista.
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

        dentista_resp = db.session.get(Usuario, dentista_responsavel_id)
        if not dentista_resp:
            raise ValueError("Dentista responsável não encontrado")
        # Papel precisa ser DENTISTA
        if getattr(dentista_resp, "role", None) != RoleEnum.DENTISTA:
            raise ValueError("Usuário selecionado não é um dentista válido")

        # Sanitiza dados_chave (campos livres)
        dados_sanitizados: dict[str, Any] = {}
        if dados_chave:
            for k, v in dict(dados_chave).items():
                dados_sanitizados[k] = sanitizar_input(v)

        novo_log = LogEmissao(
            template_id=template.id,
            paciente_id=paciente.id,
            usuario_id=usuario.id,
            dentista_responsavel_id=dentista_resp.id,
            dados_chave=dados_sanitizados,
        )
        db.session.add(novo_log)
        db.session.flush()
        new_id = int(novo_log.id)
        db.session.commit()
        return new_id
    except Exception:
        db.session.rollback()
        raise
