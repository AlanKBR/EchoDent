"""
Serviço de Procedimentos (Catálogo Clínico) - EchoDent v4
Fase 2: Página Tratamentos

CRUD de procedimentos com:
- Soft-delete (is_active=False)
- Ajuste de preços em massa
- Log de auditoria obrigatório
- Atomicidade (try/commit/rollback)
"""

from decimal import Decimal

from flask import current_app

from app.models import CategoriaEnum, LogAuditoria, Procedimento, db
from app.utils.sanitization import sanitizar_input

# Lista de categorias fixas (para UI)
CATEGORIAS_FIXAS = [
    "Clínica Geral",
    "Ortodontia",
    "Endodontia",
    "Periodontia",
    "Prótese",
    "Implantodontia",
    "Odontopediatria",
    "Cirurgia Bucomaxilofacial",
    "Estética/Cosmética",
    "Outros",
]


def list_tratamentos(
    categoria: str | None = None, ativo: bool | None = True
) -> list[Procedimento]:
    """
    Lista tratamentos com filtros opcionais.

    Args:
        categoria: Filtro por categoria (string exata do Enum)
        ativo: Se True, apenas ativos; Se False, apenas inativos;
            Se None, todos

    Returns:
        Lista de objetos Procedimento
    """
    query = db.session.query(Procedimento)

    if categoria:
        # Converter string para Enum
        try:
            categoria_enum = CategoriaEnum(categoria)
            query = query.filter_by(categoria=categoria_enum)
        except ValueError:
            current_app.logger.warning(
                f"Categoria inválida ignorada: {categoria}"
            )

    if ativo is not None:
        query = query.filter_by(is_active=ativo)

    return query.order_by(Procedimento.categoria, Procedimento.nome).all()


def create_tratamento(data: dict, user_id: int) -> Procedimento | None:
    """
    Cria novo tratamento com validação e log de auditoria.

    Args:
        data: Dict com nome, codigo (opcional), categoria,
            valor_padrao, descricao (opcional)
        user_id: ID do usuário que criou (auditoria)

    Returns:
        Objeto Procedimento criado ou None em caso de erro
    """
    try:
        # Validar e sanitizar inputs
        nome = sanitizar_input(data.get("nome", "").strip())
        if not nome:
            raise ValueError("Nome do tratamento é obrigatório")

        codigo = sanitizar_input(data.get("codigo", "").strip()) or None
        categoria_str = data.get("categoria", "").strip()
        valor_padrao = Decimal(str(data.get("valor_padrao", 0)))
        descricao = sanitizar_input(data.get("descricao", "").strip()) or None

        # Validar categoria
        try:
            categoria_enum = CategoriaEnum(categoria_str)
        except ValueError:
            raise ValueError(f"Categoria inválida: {categoria_str}")

        # Validar valor
        if valor_padrao <= 0:
            raise ValueError("Valor padrão deve ser maior que zero")

        # Criar procedimento
        proc = Procedimento(
            nome=nome,
            codigo=codigo,
            categoria=categoria_enum,
            valor_padrao=valor_padrao,
            descricao=descricao,
        )

        db.session.add(proc)
        db.session.commit()

        # Log de auditoria
        log = LogAuditoria()
        log.user_id = user_id
        log.action = "create"
        log.model_name = "procedimentos"
        log.model_id = proc.id
        log.changes_json = {
            "nome": nome,
            "codigo": codigo,
            "categoria": categoria_str,
            "valor_padrao": float(valor_padrao),
            "descricao": descricao,
        }
        db.session.add(log)
        db.session.commit()

        current_app.logger.info(
            f"Tratamento criado: {proc.nome} (ID {proc.id}) por user {user_id}"
        )
        return proc

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao criar tratamento: {e}")
        return None


def update_tratamento(
    proc_id: int, data: dict, user_id: int
) -> Procedimento | None:
    """
    Atualiza tratamento existente (apenas se ativo).

    Args:
        proc_id: ID do procedimento
        data: Dicionário com campos a atualizar
        user_id: ID do usuário que atualizou

    Returns:
        Objeto Procedimento atualizado ou None em caso de erro
    """
    try:
        proc = db.session.get(Procedimento, proc_id)
        if not proc:
            raise ValueError("Tratamento não encontrado")

        if not proc.is_active:
            raise ValueError("Não é possível editar tratamento inativo")

        # Capturar estado anterior para auditoria
        anterior = {
            "nome": proc.nome,
            "codigo": proc.codigo,
            "categoria": proc.categoria.value,
            "valor_padrao": float(proc.valor_padrao),
            "descricao": proc.descricao,
        }

        # Atualizar campos (sanitizados)
        if "nome" in data and data["nome"].strip():
            proc.nome = sanitizar_input(data["nome"].strip())

        if "codigo" in data:
            proc.codigo = sanitizar_input(data["codigo"].strip()) or None

        if "categoria" in data and data["categoria"].strip():
            try:
                proc.categoria = CategoriaEnum(data["categoria"].strip())
            except ValueError:
                raise ValueError(f"Categoria inválida: {data['categoria']}")

        if "valor_padrao" in data:
            novo_valor = Decimal(str(data["valor_padrao"]))
            if novo_valor <= 0:
                raise ValueError("Valor padrão deve ser maior que zero")
            proc.valor_padrao = novo_valor

        if "descricao" in data:
            proc.descricao = sanitizar_input(data["descricao"].strip()) or None

        db.session.commit()

        # Log de auditoria
        log = LogAuditoria()
        log.user_id = user_id
        log.action = "update"
        log.model_name = "procedimentos"
        log.model_id = proc.id
        log.changes_json = {
            "anterior": anterior,
            "novo": {
                "nome": proc.nome,
                "codigo": proc.codigo,
                "categoria": proc.categoria.value,
                "valor_padrao": float(proc.valor_padrao),
                "descricao": proc.descricao,
            },
        }
        db.session.add(log)
        db.session.commit()

        msg = (
            f"Tratamento atualizado: {proc.nome} (ID {proc.id}) por user "
            f"{user_id}"
        )
        current_app.logger.info(msg)
        return proc

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao atualizar tratamento: {e}")
        return None


def soft_delete_tratamento(proc_id: int, user_id: int) -> bool:
    """
    Soft-delete de tratamento (is_active=False).

    Args:
        proc_id: ID do procedimento
        user_id: ID do usuário que desativou

    Returns:
        True se sucesso, False se erro
    """
    try:
        proc = db.session.get(Procedimento, proc_id)
        if not proc:
            raise ValueError("Tratamento não encontrado")

        if not proc.is_active:
            raise ValueError("Tratamento já está inativo")

        proc.is_active = False
        db.session.commit()

        # Log de auditoria
        log = LogAuditoria()
        log.user_id = user_id
        log.action = "delete"
        log.model_name = "procedimentos"
        log.model_id = proc.id
        log.changes_json = {
            "nome": proc.nome,
            "categoria": proc.categoria.value,
        }
        db.session.add(log)
        db.session.commit()

        msg = (
            f"Tratamento desativado: {proc.nome} (ID {proc.id}) por user "
            f"{user_id}"
        )
        current_app.logger.info(msg)
        return True

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao desativar tratamento: {e}")
        return False


def ajustar_precos_em_massa(
    percentual: float,
    categoria: str | None = None,
    user_id: int | None = None,
) -> dict:
    """
    Ajusta preços de tratamentos em massa com percentual.

    Args:
        percentual: Percentual (5.0 => +5%, -3.0 => -3%)
        categoria: Filtro opcional por categoria
        user_id: ID do usuário que executou (auditoria)

    Returns:
        {
            'sucesso': bool,
            'afetados': int,
            'preview': [
                {'nome': str, 'preco_antigo': float, 'preco_novo': float},
                ...
            ],
            'erro': str (opcional)
        }
    """
    try:
        query = db.session.query(Procedimento).filter_by(is_active=True)

        if categoria:
            try:
                categoria_enum = CategoriaEnum(categoria)
                query = query.filter_by(categoria=categoria_enum)
            except ValueError:
                return {
                    "sucesso": False,
                    "erro": f"Categoria inválida: {categoria}",
                }

        tratamentos = query.all()
        afetados = 0
        preview = []

        for proc in tratamentos:
            preco_antigo = proc.valor_padrao
            preco_novo = preco_antigo * (1 + Decimal(percentual) / 100)
            preco_novo = preco_novo.quantize(
                Decimal("0.01")
            )  # Arredondar para 2 casas

            # Validar que preço novo é positivo
            if preco_novo <= 0:
                # Ignorar ajustes que deixariam preço zero/negativo
                continue

            proc.valor_padrao = preco_novo
            afetados += 1

            # Preview dos 10 primeiros
            if len(preview) < 10:
                preview.append(
                    {
                        "nome": proc.nome,
                        "categoria": proc.categoria.value,
                        "preco_antigo": float(preco_antigo),
                        "preco_novo": float(preco_novo),
                    }
                )

        db.session.commit()

        # Log de auditoria (operação em massa)
        if user_id:
            log = LogAuditoria()
            log.user_id = user_id
            log.action = "update"
            log.model_name = "procedimentos"
            log.model_id = 0  # Operação em massa
            log.changes_json = {
                "percentual": percentual,
                "categoria": categoria,
                "afetados": afetados,
                "preview": preview,
            }
            db.session.add(log)
            db.session.commit()

        msg = (
            f"Ajuste em massa: {afetados} tratamentos ("
            f"{percentual:+.1f}%) por user {user_id}"
        )
        current_app.logger.info(msg)

        return {
            "sucesso": True,
            "afetados": afetados,
            "preview": preview,
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao ajustar preços: {e}")
        return {"sucesso": False, "erro": str(e)}
