# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão Geral

Sistema web de fluxo de caixa para prefeituras, estados e órgãos públicos. Backend em **FastAPI + SQLAlchemy 2.0**, templates **Jinja2** server-rendered (não é SPA), banco padrão **SQLite** em `instance/fluxo.db` (PostgreSQL suportado via `DATABASE_URL`). Inclui motor de simulação de cenários (regressão, média histórica, modelos econométricos com XGBoost/LightGBM/statsmodels) para projeção de receitas e despesas públicas.

## Comandos Essenciais

### Executar aplicação (desenvolvimento)
```bash
# Forma recomendada — app.py já injeta src no PYTHONPATH
python app.py

# Alternativa direta com uvicorn (precisa PYTHONPATH=src)
PYTHONPATH=src uvicorn fluxocaixa.main:app --reload --host 0.0.0.0 --port 8000
```
App sobe em `http://localhost:8000`. Docs OpenAPI em `/docs`.

### Banco de dados
- `GET /init-db` — cria tabelas e popula dados de exemplo (executa `seed_data()`).
- `GET /recreate-db` — `drop_all` + `create_all` + seed. Use quando alterar schema.
- Apagar manualmente: `rm instance/fluxo.db` e acessar `/init-db`.
- Não há Alembic — schema é gerenciado por `Base.metadata.create_all()` em `create_app()`. Migrações ad-hoc ficam em `migrations/*.sql` e em funções `ensure_*_schema()` (ex: `models/alerta.py:ensure_alerta_schema`) que fazem `ALTER TABLE` idempotente para colunas adicionadas após o lançamento.

### Testes
```bash
# Suíte oficial (pytest)
PYTHONPATH=src pytest src/tests/

# Um teste específico
PYTHONPATH=src pytest src/tests/unit/test_alertas.py::test_name -v

# Scripts de teste manuais na raiz (não são pytest — rodar com python diretamente)
python test_simulador_db.py
python test_simulador_full.py
python test_xgboost_lightgbm.py
python verify_calculation.py
python debug_dfc.py
```
A fixture `client` em `src/tests/conftest.py` força `DATABASE_URL=sqlite:///./test.db` antes de importar `fluxocaixa` — não importe o módulo no topo de testes que precisem de DB isolado.

### Deploy (Render.com)
`render.yaml` define start: `gunicorn src.fluxocaixa.main:app -k uvicorn.workers.UvicornWorker`. Gunicorn não funciona em Windows (depende de `fcntl`) — apenas Linux em produção.

## Arquitetura

### Camadas
```
web/ (rotas FastAPI)  →  services/ (lógica de negócio)  →  repositories/ (queries)  →  models/ (SQLAlchemy)
                                  ↑
                            domain/ (Pydantic DTOs: *Create, *Out, *Update)
```
- **`web/`**: Cada arquivo é um módulo de rotas (`base.py`, `relatorios.py`, `simulador_cenarios.py`, etc.). Todos compartilham um único `router` e `templates` Jinja2 expostos por `web/__init__.py`. As rotas são registradas por **import side-effect** na linha final de `web/__init__.py` — adicionar um novo módulo de rotas requer importá-lo lá.
- **`services/relatorio/`**: Pacote modular que substituiu o antigo `relatorio_service.py` monolítico. Cada relatório (DFC, indicadores, previsão de receita, etc.) tem seu próprio service.
- **`domain/`**: DTOs Pydantic v2. Nomes seguem `<Entidade>Create` / `<Entidade>Out` / `<Entidade>Update`.

### Padrões importantes

**SafeAPIRouter** (`web/safe_router.py`): subclasse de `APIRouter` que envolve automaticamente todo endpoint com `handle_exceptions`. Esse wrapper faz log de exceções não tratadas, executa `db.session.rollback()` e retorna 500. Não é necessário decorar manualmente — mas alguns endpoints existentes ainda têm `@handle_exceptions` redundante por histórico.

**Sessão SQLAlchemy** (`models/base.py`): `SessionLocal` é um `scoped_session` global compartilhado. `Base.query` está disponível como query property no estilo Flask-SQLAlchemy (`Lancamento.query.all()`). Há também `Query.get_or_404` monkey-patched que levanta `HTTPException(404)`. O helper `_DB` em `models/base.py` simula a interface mínima de Flask-SQLAlchemy (`db.session`, `db.create_all()`, `db.drop_all()`) — não é Flask, apesar do nome.

**Bootstrap** (`fluxocaixa/__init__.py:create_app`): A cada start o app executa `db.create_all()` + `ensure_alerta_schema()` + `seed_data()`. Em produção isso significa que tabelas ausentes são criadas no boot, mas `seed_data` é idempotente (limpa e repopula apenas dados de exemplo conhecidos).

**Convenções de schema**:
- Todas as tabelas têm prefixo `flc_` (ex: `flc_lancamento`, `flc_qualificador`).
- PKs nomeadas `seq_*`, FKs `cod_*` ou `seq_*_fk`.
- Soft delete via `ind_status` (`'A'` ativo / `'I'` inativo) — preferir filtrar do que `DELETE`.
- Auditoria: `dat_inclusao`, `cod_pessoa_inclusao`, `dat_alteracao`, `cod_pessoa_alteracao`.
- Valores monetários: `NUMERIC(18,2)` — nunca `Float`.
- `flc_qualificador` é hierárquico (auto-FK em `cod_qualificador_pai`); folha = sem filhos ativos. Helper: `Qualificador.is_folha()`.

**Modelo de simulação de cenários** (`flc_simulador_cenario`): Um cenário tem N receitas e N despesas (`flc_cenario_receita`, `flc_cenario_despesa`), cada uma com `cod_tipo_cenario` (`MANUAL`, `REGRESSAO`, `MEDIA_HISTORICA`, etc.) e `json_configuracao` com parâmetros do modelo. Ajustes manuais por (ano, mês) ficam em tabelas `_ajuste`. Snapshots completos são serializados em `flc_simulador_cenario_historico.json_snapshot`. Veja `services/simulador_cenario_service.py`, `services/previsao_service.py`, `services/modelos_economicos_service.py`, `services/feature_engineering.py`.

**Templates**: Jinja2 carregado de `templates/` na raiz do projeto (não dentro de `src/`). Path resolvido via `BASE_DIR` em `config.py`. Filtro custom `format_currency` registrado em `web/__init__.py`. Templates de relatórios seguem o prefixo `rel_*.html`.

**Importação CSV/XLSX**: Endpoints `/saldos/import` e `/saldos/template-xlsx` usam `openpyxl`. Template gerado em código (não há arquivo estático).

## Notas

- Python 3.8–3.11 (`pyproject.toml`); Render usa 3.10.
- Não há linter/formatter configurado — sem `ruff`, `black` ou `mypy` no projeto.
- `auth/` existe como diretório mas está vazio (apenas `__init__.py`); o sistema **não tem autenticação** atualmente.
- Documento de roadmap/contexto: `MelhoriasPrevisoesReceitaseDespesas.md` no repo pai descreve o plano para os modelos de previsão.
