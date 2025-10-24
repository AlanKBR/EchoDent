# EchoDent: Software de Gestão Odontológica Offline‑First com Flask e HTMX

EchoDent é um sistema de gestão odontológica com foco em clínica local (rede interna), simplicidade operacional e robustez. O backend é Flask (renderizando HTML), a UI é baseada em hipermídia com HTMX, e PDFs são gerados via WeasyPrint.

## Filosofia central e “peculiaridades” de arquitetura

- Multi‑bind SQLite
  - 3 bancos separados com SQLAlchemy binds: `pacientes.db` (padrão), `users.db` e `history.db` (auditoria).
  - Configuração em `app/config.py` (veja `SQLALCHEMY_BINDS`). Arquivos ficam em `instance/`.
  - Não use Foreign Keys entre binds: a integridade entre bancos é validada explicitamente na camada de services (`app/services/`).
- Concorrência em rede local (WAL)
  - Todos os engines SQLite são configurados com `PRAGMA journal_mode=WAL` via listeners em `app/__init__.py` (evento `connect`).
- “Fluxo de Ouro” (Financeiro)
  - O `PlanoTratamento` é a única fonte de débito (fonte da verdade).
  - O saldo devedor só existe após `PlanoTratamento.status == APROVADO`.
  - Todo `LancamentoFinanceiro` deve referenciar um `PlanoTratamento` válido (mesmo bind).
  - Recibo “avulso” cria um plano “fantasma” (ex.: `CONCLUIDO`) e associa o lançamento a ele.
- Temporalidade e auditoria
  - Todos `DateTime` relevantes usam timezone (`timezone=True`) com default em UTC.
  - Soft‑delete para `Usuario` (`is_active`) e logs de auditoria no bind `history` (`LogAuditoria`).

## Instalação

> Requisitos: Python 3.10+ (recomendado), `pip`. Para recursos de PDF no Windows, ver seção “WeasyPrint (Windows)”.

1) Crie o ambiente virtual e instale dependências

```powershell
# Windows PowerShell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Configure variáveis de ambiente

- Copie `.env.example` para `.env` e ajuste:
  - `SECRET_KEY` (obrigatório)
  - `FLASK_APP=run.py` (já sugerido no example)
  - (Windows) `WEASYPRINT_DLL_DIRECTORIES` se necessário (ver seção seguinte)

3) Migrações de banco de dados (cria tabelas nos 3 binds)

```powershell
flask db upgrade
```

## WeasyPrint (Windows) — dependência crítica

Para gerar PDFs no Windows, o WeasyPrint depende de bibliotecas nativas (MSYS2 + Pango/GTK/Cairo).

- Instale MSYS2 e os pacotes de Pango/GTK seguindo a documentação oficial do WeasyPrint.
- Se instalado em `C:\msys64\mingw64\bin`, o `run.py` já tenta configurar `WEASYPRINT_DLL_DIRECTORIES` automaticamente.
- Alternativamente, defina manualmente no `.env`:

```powershell
# Exemplo no .env (Windows)
WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin
```

O projeto usa import “lazy” do WeasyPrint nas rotas. Se as DLLs não estiverem presentes, a rota falha de forma amigável sem derrubar o servidor.

## Executando a aplicação

Com o ambiente ativado e `.env` configurado:

```powershell
# já com FLASK_APP=run.py no .env
flask run
```

A aplicação cria `instance/` automaticamente e utiliza os arquivos `pacientes.db`, `users.db` e `history.db` nessa pasta.

## Testes automatizados

Com o ambiente virtual ativo:

```powershell
pytest
```

Observações:
- A configuração de testes está em `pytest.ini`, apontando a descoberta para `tests/`.
- Os testes criam bancos temporários para cada execução (sem tocar em `instance/`).

## Pre-commit (opcional)

Para padronização de código com Black/Flake8/isort:

```powershell
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Arquitetura da UI (Design System)

- Tokens e temas
  - Toda a UI utiliza Design Tokens definidos em `app/static/css/global.css`.
  - Suporte a Dark Mode via atributo `[data-theme-mode="dark"]`. Há um botão de alternância (“Mudar Tema”).
- Componentes e padrões
  - Sem CSS/JS inline. Use classes de componentes: `.card`, `.btn`, `.alert`, tabelas e utilitários (espaçamento, flex, largura).
  - Formulários e páginas seguem a estrutura `.card` com `.card-header` e `.card-body`.
  - Fragments HTMX retornam HTML parcial com ids/âncoras estáveis para `hx-target`.
- Modal de erro global (HTMX)
  - Exibe mensagens de erro de respostas HTMX, inclui log bruto do servidor (pre), botão “Copiar Erro” e auto‑dismiss.

## Estrutura de pastas (resumo)

- `app/__init__.py` — Application Factory, inicializa extensões, configura WAL e registra blueprints.
- `app/config.py` — Configuração, URIs SQLite por bind, disables track modifications.
- `app/models.py` — Todos os modelos SQLAlchemy (um único arquivo para evitar import circular).
- `app/services/` — Lógica de negócio e validações (inclui validação entre binds e “Fluxo de Ouro”).
- `app/blueprints/` — Rotas leves (thin controllers) que chamam services e rendem templates Jinja.
- `app/templates/` — Páginas e parciais Jinja (arquitetura hipermídia com HTMX).
- `app/static/css/global.css` — Tokens, temas, componentes (cards, botões, alertas), utilitários.
- `app/static/js/` — `theme-toggle.js` (modo claro/escuro) e `app.js` (modal de erro, handlers delegados).
- `instance/` — Armazena os bancos SQLite e mídia (`media_storage/`).

## Dicas operacionais

- Evite FKs entre bancos (`users`/`history`/padrão); faça validações na camada de services.
- O `PRAGMA journal_mode=WAL` já é aplicado por listeners a todos os engines.
- Para PDFs, mantenha os assets locais (offline‑first): fontes/imagens referenciadas no template Jinja.

## Solução de Problemas (Troubleshooting)

- WeasyPrint (Windows) não encontra DLLs (Pango/GTK/Cairo)
  - Verifique se o MSYS2 está instalado e se o diretório `C:\msys64\mingw64\bin` existe.
  - O `run.py` tenta configurar `WEASYPRINT_DLL_DIRECTORIES` automaticamente; se necessário, defina manualmente no `.env`.
  - Reinicie o shell após alterar variáveis de ambiente.

- Erro de import do WeasyPrint ou falha ao gerar PDF
  - O app usa import “lazy” para não quebrar a inicialização. A rota de impressão deve reportar um erro amigável sem derrubar o servidor.
  - Confirme que `weasyprint` está instalado: `pip install -r requirements.txt`.

- Conflitos de arquivo SQLite ou “database is locked”
  - Garanta que a pasta `instance/` exista e que os `.db` não estejam abertos em outro programa.
  - O WAL é habilitado por listeners; se notar problemas, reinicie o app e confirme que não há múltiplas cópias competindo pelo mesmo arquivo em rede compartilhada.

- `flask db upgrade` falhando
  - Verifique se o ambiente virtual está ativado e dependências instaladas.
  - Confirme que `FLASK_APP=run.py` está no seu `.env` e que o diretório `instance/` existe.
  - Em setups customizados (testes), confira as variáveis `ECHO_TEST_*` usadas em `create_app('testing')`.

- SECRET_KEY ausente
  - Defina `SECRET_KEY` no `.env`. Sem isso, sessões/CSRF podem falhar.

- Erros HTMX em telas com requisições parciais
  - O modal de erro global exibe o log bruto da resposta. Use o botão “Copiar Erro” para compartilhar a falha.
  - Ative o modo debug (variáveis de ambiente) para obter tracebacks detalhados em desenvolvimento.

---

Para diretrizes detalhadas, consulte `AGENTS.MD`.
