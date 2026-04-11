"""Web endpoints para Fórmulas Parametrizáveis e Parâmetros Globais."""

from datetime import date
from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse
import json

from . import router, templates, handle_exceptions
from ..services import (
    list_receita_qualificadores_folha,
    list_despesa_qualificadores_folha,
    get_qualificador,
)
from ..repositories import formula_repository as formula_repo
from ..services.formula_engine import (
    extrair_variaveis,
    validar_formula,
    avaliar_formula,
    listar_anos_disponiveis,
    calcular_base,
)
from ..models.formula import RubricaFormula, ParametroGlobal, CenarioParametroValor


# ==================== Fórmulas ====================

@router.get('/formulas')
@handle_exceptions
async def formulas_list(request: Request):
    """Lista todas as fórmulas cadastradas."""
    formulas = formula_repo.get_all_formulas()

    # Enriquecer com dados do qualificador
    formulas_data = []
    for f in formulas:
        variaveis = extrair_variaveis(f.dsc_formula_expressao)
        config_base = {}
        if f.json_config_base:
            try:
                config_base = json.loads(f.json_config_base)
            except (json.JSONDecodeError, TypeError):
                pass

        formulas_data.append({
            'formula': f,
            'variaveis': variaveis,
            'config_base': config_base,
            'formula_json': {
                'seq_rubrica_formula': f.seq_rubrica_formula,
                'seq_qualificador': f.seq_qualificador,
                'nom_formula': f.nom_formula,
                'dsc_formula_expressao': f.dsc_formula_expressao,
                'cod_metodo_base': f.cod_metodo_base,
                'json_config_base': f.json_config_base or '{}',
            },
        })

    qualificadores_receita = list_receita_qualificadores_folha()
    qualificadores_despesa = list_despesa_qualificadores_folha()

    return templates.TemplateResponse(
        'formulas.html',
        {
            'request': request,
            'formulas_data': formulas_data,
            'qualificadores_receita': qualificadores_receita,
            'qualificadores_despesa': qualificadores_despesa,
        },
    )


@router.post('/formulas/criar')
@handle_exceptions
async def formula_criar(request: Request):
    """Cria uma nova fórmula."""
    form = await request.form()

    seq_qualificador = int(form.get('seq_qualificador'))
    nom_formula = form.get('nom_formula', '').strip()
    expressao = form.get('dsc_formula_expressao', '').strip()
    cod_metodo_base = form.get('cod_metodo_base', 'MEDIA_SIMPLES')

    # Validar expressão
    valida, erro = validar_formula(expressao)
    if not valida:
        return JSONResponse({'error': f'Expressão inválida: {erro}'}, status_code=400)

    # Montar config_base
    config_base = _parse_config_base_from_form(form, cod_metodo_base)

    # Verificar se já existe fórmula para este qualificador
    existente = formula_repo.get_formula_by_qualificador(seq_qualificador)
    if existente:
        return JSONResponse(
            {'error': 'Já existe uma fórmula cadastrada para este qualificador'},
            status_code=400,
        )

    formula = RubricaFormula(
        seq_qualificador=seq_qualificador,
        nom_formula=nom_formula,
        dsc_formula_expressao=expressao,
        cod_metodo_base=cod_metodo_base,
        json_config_base=json.dumps(config_base),
    )
    formula_repo.create_formula(formula)

    return RedirectResponse(url='/formulas', status_code=303)


@router.post('/formulas/{id}/atualizar')
@handle_exceptions
async def formula_atualizar(request: Request, id: int):
    """Atualiza uma fórmula existente."""
    form = await request.form()
    formula = formula_repo.get_formula_by_id(id)

    if not formula:
        return RedirectResponse(url='/formulas', status_code=303)

    expressao = form.get('dsc_formula_expressao', '').strip()
    cod_metodo_base = form.get('cod_metodo_base', 'MEDIA_SIMPLES')

    # Validar expressão
    valida, erro = validar_formula(expressao)
    if not valida:
        return JSONResponse({'error': f'Expressão inválida: {erro}'}, status_code=400)

    formula.nom_formula = form.get('nom_formula', '').strip()
    formula.dsc_formula_expressao = expressao
    formula.cod_metodo_base = cod_metodo_base
    formula.json_config_base = json.dumps(
        _parse_config_base_from_form(form, cod_metodo_base)
    )
    formula_repo.update_formula(formula)

    return RedirectResponse(url='/formulas', status_code=303)


@router.post('/formulas/{id}/deletar')
@handle_exceptions
async def formula_deletar(request: Request, id: int):
    """Inativa uma fórmula."""
    formula_repo.delete_formula(id)
    return RedirectResponse(url='/formulas', status_code=303)


@router.post('/formulas/validar')
@handle_exceptions
async def formula_validar_api(request: Request):
    """API para validar uma expressão e retornar suas variáveis."""
    data = await request.json()
    expressao = data.get('expressao', '')

    valida, erro = validar_formula(expressao)
    variaveis = extrair_variaveis(expressao) if valida else []

    # Separar variáveis em globais e específicas
    parametros_globais = formula_repo.get_all_parametros_globais()
    nomes_globais = {p.nom_parametro for p in parametros_globais}

    vars_globais = [v for v in variaveis if v in nomes_globais]
    vars_especificas = [v for v in variaveis if v not in nomes_globais and v != 'base']

    return JSONResponse({
        'valida': valida,
        'erro': erro,
        'variaveis': variaveis,
        'variaveis_globais': vars_globais,
        'variaveis_especificas': vars_especificas,
        'tem_base': 'base' in variaveis,
    })


@router.post('/formulas/preview')
@handle_exceptions
async def formula_preview_api(request: Request):
    """API para calcular preview de uma fórmula com valores informados."""
    data = await request.json()
    expressao = data.get('expressao', '')
    variaveis = data.get('variaveis', {})

    # Converter valores para float
    vars_float = {}
    for k, v in variaveis.items():
        try:
            vars_float[k] = float(v)
        except (ValueError, TypeError):
            return JSONResponse(
                {'error': f'Valor inválido para variável "{k}": {v}'},
                status_code=400,
            )

    try:
        resultado = avaliar_formula(expressao, vars_float)
        return JSONResponse({
            'resultado': resultado,
            'formatado': f'R$ {resultado:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
        })
    except ValueError as e:
        return JSONResponse({'error': str(e)}, status_code=400)


@router.get('/formulas/anos-disponiveis/{seq_qualificador}')
@handle_exceptions
async def formula_anos_disponiveis(seq_qualificador: int):
    """API para retornar os anos com dados históricos para um qualificador."""
    anos = listar_anos_disponiveis(seq_qualificador)
    return JSONResponse({'anos': anos, 'total': len(anos)})


# ==================== Parâmetros Globais ====================

@router.get('/parametros-globais')
@handle_exceptions
async def parametros_globais_list(request: Request):
    """Lista todos os parâmetros globais."""
    parametros = formula_repo.get_all_parametros_globais()
    parametros_data = [
        {
            'obj': p,
            'json': {
                'seq_parametro_global': p.seq_parametro_global,
                'nom_parametro': p.nom_parametro,
                'dsc_parametro': p.dsc_parametro,
                'cod_tipo': p.cod_tipo,
            }
        }
        for p in parametros
    ]
    return templates.TemplateResponse(
        'parametros_globais.html',
        {
            'request': request,
            'parametros': parametros,
            'parametros_data': parametros_data,
        },
    )


@router.post('/parametros-globais/criar')
@handle_exceptions
async def parametro_global_criar(request: Request):
    """Cria um novo parâmetro global."""
    form = await request.form()

    nom_parametro = form.get('nom_parametro', '').strip().lower()
    dsc_parametro = form.get('dsc_parametro', '').strip()
    cod_tipo = form.get('cod_tipo', 'P')

    if not nom_parametro:
        return JSONResponse({'error': 'Nome do parâmetro é obrigatório'}, status_code=400)

    # Verificar duplicidade
    existente = formula_repo.get_parametro_global_by_nome(nom_parametro)
    if existente:
        return JSONResponse(
            {'error': f'Parâmetro "{nom_parametro}" já existe'},
            status_code=400,
        )

    parametro = ParametroGlobal(
        nom_parametro=nom_parametro,
        dsc_parametro=dsc_parametro,
        cod_tipo=cod_tipo,
    )
    formula_repo.create_parametro_global(parametro)

    return RedirectResponse(url='/parametros-globais', status_code=303)


@router.post('/parametros-globais/{id}/atualizar')
@handle_exceptions
async def parametro_global_atualizar(request: Request, id: int):
    """Atualiza um parâmetro global."""
    form = await request.form()
    parametro = formula_repo.get_parametro_global_by_id(id)

    if not parametro:
        return RedirectResponse(url='/parametros-globais', status_code=303)

    parametro.nom_parametro = form.get('nom_parametro', '').strip().lower()
    parametro.dsc_parametro = form.get('dsc_parametro', '').strip()
    parametro.cod_tipo = form.get('cod_tipo', 'P')
    formula_repo.update_parametro_global(parametro)

    return RedirectResponse(url='/parametros-globais', status_code=303)


@router.post('/parametros-globais/{id}/deletar')
@handle_exceptions
async def parametro_global_deletar(request: Request, id: int):
    """Inativa um parâmetro global."""
    formula_repo.delete_parametro_global(id)
    return RedirectResponse(url='/parametros-globais', status_code=303)


@router.get('/api/parametros-globais')
@handle_exceptions
async def parametros_globais_api():
    """API JSON com todos os parâmetros globais (para autocomplete no frontend)."""
    parametros = formula_repo.get_all_parametros_globais()
    return JSONResponse({
        'parametros': [
            {
                'seq_parametro_global': p.seq_parametro_global,
                'nom_parametro': p.nom_parametro,
                'dsc_parametro': p.dsc_parametro,
                'cod_tipo': p.cod_tipo,
            }
            for p in parametros
        ]
    })


@router.get('/api/formulas')
@handle_exceptions
async def formulas_api():
    """API JSON com todas as fórmulas ativas (para uso no simulador)."""
    formulas = formula_repo.get_all_formulas()
    result = []
    for f in formulas:
        variaveis = extrair_variaveis(f.dsc_formula_expressao)
        config_base = {}
        if f.json_config_base:
            try:
                config_base = json.loads(f.json_config_base)
            except (json.JSONDecodeError, TypeError):
                pass

        result.append({
            'seq_rubrica_formula': f.seq_rubrica_formula,
            'seq_qualificador': f.seq_qualificador,
            'nom_formula': f.nom_formula,
            'dsc_formula_expressao': f.dsc_formula_expressao,
            'cod_metodo_base': f.cod_metodo_base,
            'config_base': config_base,
            'variaveis': variaveis,
            'qualificador_nome': f.qualificador.dsc_qualificador if f.qualificador else '',
        })

    return JSONResponse({'formulas': result})


# ==================== Helpers ====================

def _parse_config_base_from_form(form, cod_metodo_base: str) -> dict:
    """Extrai configuração de base do formulário."""
    config = {}

    if cod_metodo_base == 'VALOR_FIXO':
        try:
            config['valor'] = float(form.get('valor_fixo', 0) or 0)
        except (ValueError, TypeError):
            config['valor'] = 0.0
    else:
        # MEDIA_SIMPLES ou MEDIA_PONDERADA
        anos_str = form.get('anos_selecionados', '')
        try:
            if anos_str:
                anos = json.loads(anos_str)
                config['anos'] = [int(a) for a in anos]
            else:
                config['anos'] = []
        except (json.JSONDecodeError, ValueError):
            config['anos'] = []

        if cod_metodo_base == 'MEDIA_PONDERADA':
            pesos = {}
            for ano in config.get('anos', []):
                peso_key = f'peso_{ano}'
                try:
                    pesos[str(ano)] = float(form.get(peso_key, 1) or 1)
                except (ValueError, TypeError):
                    pesos[str(ano)] = 1.0
            config['pesos'] = pesos

    return config
