"""Web endpoints for Simulador de Cenários."""

from datetime import date
from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse
import json

from . import router, templates, handle_exceptions
from ..services import (
    list_simuladores,
    list_active_simuladores,
    get_simulador,
    criar_simulador_cenario,
    atualizar_simulador_cenario,
    delete_simulador,
    obter_simulador_completo,
    executar_simulacao,
    list_receita_qualificadores_folha,
    list_despesa_qualificadores_folha,
    get_qualificador,
)
from ..utils.constants import MONTH_NAME_PT


@router.get('/simulador')
@handle_exceptions
async def simulador_menu(request: Request):
    """Menu principal do simulador de cenários."""
    simuladores = list_active_simuladores()
    return templates.TemplateResponse(
        'simulador_menu.html',
        {
            'request': request,
            'simuladores': simuladores,
        }
    )


@router.get('/simulador/novo')
@handle_exceptions
async def simulador_novo(request: Request):
    """Formulário para criar novo cenário simulador."""
    qualificadores_receita = list_receita_qualificadores_folha()
    qualificadores_despesa = list_despesa_qualificadores_folha()
    
    # Buscar todos os anos com dados históricos
    from ..services.formula_engine import listar_todos_anos_disponiveis
    anos_disponiveis = listar_todos_anos_disponiveis()
    
    return templates.TemplateResponse(
        'simulador_criar.html',
        {
            'request': request,
            'qualificadores_receita': qualificadores_receita,
            'qualificadores_despesa': qualificadores_despesa,
            'current_year': date.today().year,
            'meses_nomes': MONTH_NAME_PT,
            'modo': 'criar',
            'anos_disponiveis': anos_disponiveis,
        }
    )


@router.post('/simulador/criar')
@handle_exceptions
async def simulador_criar(request: Request):
    """Cria um novo cenário simulador."""
    form = await request.form()
    
    # Dados básicos
    nom_cenario = form.get('nom_cenario')
    dsc_cenario = form.get('dsc_cenario')
    ano_base = int(form.get('ano_base', date.today().year))
    meses_projecao = int(form.get('meses_projecao', 12))
    cod_periodicidade = form.get('cod_periodicidade', 'MENSAL')
    cod_metodo_base = form.get('cod_metodo_base', 'MEDIA_SIMPLES')
    json_config_base = _parse_config_base_from_form(form)
    
    # Configuração de receita
    tipo_cenario_receita = form.get('tipo_cenario_receita', 'MANUAL')
    config_receita = _parse_model_config_from_form(form, 'receita')
    
    # Sempre processar ajustes (valores da tabela) - independente do modelo
    ajustes_receita = dict(form)
    
    # Configuração de despesa
    tipo_cenario_despesa = form.get('tipo_cenario_despesa', 'MANUAL')
    config_despesa = _parse_model_config_from_form(form, 'despesa')
    
    # Sempre processar ajustes de despesa
    ajustes_despesa = dict(form)
    
    # Criar cenário
    simulador = criar_simulador_cenario(
        nom_cenario=nom_cenario,
        dsc_cenario=dsc_cenario,
        ano_base=ano_base,
        meses_projecao=meses_projecao,
        tipo_cenario_receita=tipo_cenario_receita,
        config_receita=config_receita,
        tipo_cenario_despesa=tipo_cenario_despesa,
        config_despesa=config_despesa,
        ajustes_receita=ajustes_receita,
        ajustes_despesa=ajustes_despesa,
        cod_periodicidade=cod_periodicidade,
        cod_metodo_base=cod_metodo_base,
        json_config_base=json_config_base,
    )
    
    # Salvar parâmetros de fórmula se tipo FORMULA
    if tipo_cenario_receita == 'FORMULA' or tipo_cenario_despesa == 'FORMULA':
        _salvar_parametros_formula(form, simulador.seq_simulador_cenario)
    
    # Redirecionar para visualização
    return RedirectResponse(
        url=f'/simulador/{simulador.seq_simulador_cenario}',
        status_code=303
    )


@router.get('/simulador/{id}')
@handle_exceptions
async def simulador_visualizar(request: Request, id: int):
    """Visualiza resultados de um cenário simulador."""
    simulador = get_simulador(id)
    if not simulador:
        return RedirectResponse(url='/simulador', status_code=303)
    
    # Executar simulação para obter resultados
    resultado = executar_simulacao(id)
    
    if not resultado:
        return RedirectResponse(url='/simulador', status_code=303)
    
    # Converter DataFrame para formato JSON-friendly
    projecao_receita_json = _dataframe_to_json(resultado['projecao_receita'])
    projecao_despesa_json = _dataframe_to_json(resultado['projecao_despesa'])
    cenario_total_json = _dataframe_to_json(resultado['cenario_total'])
    
    return templates.TemplateResponse(
        'simulador_visualizar.html',
        {
            'request': request,
            'simulador': simulador,
            'projecao_receita': projecao_receita_json,
            'projecao_despesa': projecao_despesa_json,
            'cenario_total': cenario_total_json,
            'resumo': resultado['resumo'],
        }
    )


@router.get('/simulador/{id}/editar')
@handle_exceptions
async def simulador_editar_get(request: Request, id: int):
    """Formulário para editar cenário simulador."""
    simulador = get_simulador(id)
    if not simulador:
        return RedirectResponse(url='/simulador', status_code=303)
    
    cenario_completo = obter_simulador_completo(id)
    qualificadores_receita = list_receita_qualificadores_folha()
    qualificadores_despesa = list_despesa_qualificadores_folha()
    
    # Converter cenario_completo para formato JSON-serializável
    cenario_json = None
    if cenario_completo:
        # Extrair config de receita se existir
        receita_config = cenario_completo.get('receita', {}).get('config')
        despesa_config = cenario_completo.get('despesa', {}).get('config')
        
        # Parse JSON configuration
        receita_json_config = {}
        if receita_config and receita_config.json_configuracao:
            try:
                receita_json_config = json.loads(receita_config.json_configuracao)
            except (json.JSONDecodeError, TypeError):
                pass
        
        despesa_json_config = {}
        if despesa_config and despesa_config.json_configuracao:
            try:
                despesa_json_config = json.loads(despesa_config.json_configuracao)
            except (json.JSONDecodeError, TypeError):
                pass
        
        cenario_json = {
            'receita': {
                'config': {
                    'cod_tipo_cenario': receita_config.cod_tipo_cenario if receita_config else 'MANUAL',
                    'json_configuracao': receita_json_config,
                },
                'ajustes': [
                    {
                        'seq_qualificador': a.seq_qualificador,
                        'ano': a.ano,
                        'mes': a.mes,
                        'cod_tipo_ajuste': a.cod_tipo_ajuste,
                        'val_ajuste': float(a.val_ajuste) if a.val_ajuste else 0
                    }
                    for a in (cenario_completo.get('receita', {}).get('ajustes', []))
                ]
            },
            'despesa': {
                'config': {
                    'cod_tipo_cenario': despesa_config.cod_tipo_cenario if despesa_config else 'MANUAL',
                    'json_configuracao': despesa_json_config,
                },
                'ajustes': [
                    {
                        'seq_qualificador': a.seq_qualificador,
                        'ano': a.ano,
                        'mes': a.mes,
                        'cod_tipo_ajuste': a.cod_tipo_ajuste,
                        'val_ajuste': float(a.val_ajuste) if a.val_ajuste else 0
                    }
                    for a in (cenario_completo.get('despesa', {}).get('ajustes', []))
                ]
            }
        }
    
    # Buscar todos os anos com dados históricos
    from ..services.formula_engine import listar_todos_anos_disponiveis
    anos_disponiveis = listar_todos_anos_disponiveis()
    
    return templates.TemplateResponse(
        'simulador_criar.html',
        {
            'request': request,
            'simulador': simulador,
            'cenario_completo': cenario_json,
            'qualificadores_receita': qualificadores_receita,
            'qualificadores_despesa': qualificadores_despesa,
            'meses_nomes': MONTH_NAME_PT,
            'modo': 'editar',
            'anos_disponiveis': anos_disponiveis,
        }
    )


@router.post('/simulador/{id}/atualizar')
@handle_exceptions
async def simulador_atualizar(request: Request, id: int):
    """Atualiza um cenário simulador existente."""
    form = await request.form()
    
    # Processar dados (similar ao criar)
    nom_cenario = form.get('nom_cenario')
    dsc_cenario = form.get('dsc_cenario')
    ano_base = int(form.get('ano_base'))
    meses_projecao = int(form.get('meses_projecao'))
    cod_periodicidade = form.get('cod_periodicidade', 'MENSAL')
    cod_metodo_base = form.get('cod_metodo_base', 'MEDIA_SIMPLES')
    json_config_base = _parse_config_base_from_form(form)
    
    tipo_cenario_receita = form.get('tipo_cenario_receita')
    tipo_cenario_despesa = form.get('tipo_cenario_despesa')
    
    # Sempre parsear a configuração do modelo para receita e despesa
    config_receita = _parse_model_config_from_form(form, 'receita')
    config_despesa = _parse_model_config_from_form(form, 'despesa')
    
    # Sempre incluir ajustes (valores da tabela) - independente do modelo
    ajustes_receita = dict(form)
    ajustes_despesa = dict(form)
    
    # Atualizar
    atualizar_simulador_cenario(
        seq_simulador_cenario=id,
        nom_cenario=nom_cenario,
        dsc_cenario=dsc_cenario,
        ano_base=ano_base,
        meses_projecao=meses_projecao,
        tipo_cenario_receita=tipo_cenario_receita,
        config_receita=config_receita,
        tipo_cenario_despesa=tipo_cenario_despesa,
        config_despesa=config_despesa,
        ajustes_receita=ajustes_receita,
        ajustes_despesa=ajustes_despesa,
        cod_periodicidade=cod_periodicidade,
        cod_metodo_base=cod_metodo_base,
        json_config_base=json_config_base,
    )
    
    # Salvar parâmetros de fórmula se tipo FORMULA
    if tipo_cenario_receita == 'FORMULA' or tipo_cenario_despesa == 'FORMULA':
        _salvar_parametros_formula(form, id)
    
    return RedirectResponse(url=f'/simulador/{id}', status_code=303)


@router.post('/simulador/{id}/deletar')
@handle_exceptions
async def simulador_deletar(request: Request, id: int):
    """Deleta (inativa) um cenário simulador."""
    delete_simulador(id)
    return RedirectResponse(url='/simulador', status_code=303)


@router.post('/simulador/{id}/executar')
@handle_exceptions
async def simulador_executar_api(id: int):
    """
    API endpoint para executar simulação e retornar JSON.
    Útil para atualizar resultados via AJAX.
    """
    resultado = executar_simulacao(id)
    
    if not resultado:
        return JSONResponse({'error': 'Simulação não encontrada'}, status_code=404)
    
    # Converter DataFrames para JSON
    return JSONResponse({
        'projecao_receita': _dataframe_to_json(resultado['projecao_receita']),
        'projecao_despesa': _dataframe_to_json(resultado['projecao_despesa']),
        'cenario_total': _dataframe_to_json(resultado['cenario_total']),
        'resumo': resultado['resumo'],
    })


@router.post('/simulador/calcular-projecao')
@handle_exceptions
async def simulador_calcular_projecao(request: Request):
    """
    Calcula projeção sob demanda (sem salvar cenário).
    Usado para preencher a tabela no frontend.
    """
    from ..services import modelos_economicos_service as modelos
    from dateutil.relativedelta import relativedelta
    
    data = await request.json()
    
    tipo_modelo = data.get('tipo_modelo')
    seq_qualificador = data.get('seq_qualificador')
    seq_qualificadores = data.get('seq_qualificadores', [])  # Para modelos com múltiplos qualificadores
    meses_projecao = int(data.get('meses_projecao', 12))
    ano_base = int(data.get('ano_base', date.today().year))
    config = data.get('config', {})
    
    # Definir período histórico necessário
    data_fim = date(ano_base - 1, 12, 31)  # Usar dados até o ano anterior
    
    # Converter seq_qualificador para lista se necessário
    if seq_qualificador and not seq_qualificadores:
        seq_qualificadores = [int(seq_qualificador)]
    elif seq_qualificadores:
        seq_qualificadores = [int(sq) for sq in seq_qualificadores]
    
    if not seq_qualificadores:
        return JSONResponse({'error': 'Nenhum qualificador selecionado'}, status_code=400)
    
    try:
        if tipo_modelo == 'HOLT_WINTERS':
            # Holt-Winters precisa de pelo menos 24 meses (2 anos)
            data_inicio = data_fim - relativedelta(years=3)  # Pegar 3 anos para garantir
            
            if len(seq_qualificadores) > 1:
                # Agregar dados de múltiplos qualificadores
                dados_hist = modelos.obter_dados_historicos_agregados(seq_qualificadores, data_inicio, data_fim)
            else:
                dados_hist = modelos.obter_dados_historicos(seq_qualificadores[0], data_inicio, data_fim)
            
            if len(dados_hist) < 12:
                return JSONResponse({'error': f'Dados históricos insuficientes. Encontrados: {len(dados_hist)} meses, mínimo: 12'}, status_code=400)
            
            resultado = modelos.projetar_holt_winters(dados_hist, meses_projecao, config, ano_base)
                
        elif tipo_modelo == 'ARIMA':
            data_inicio = data_fim - relativedelta(years=3)
            
            if len(seq_qualificadores) > 1:
                dados_hist = modelos.obter_dados_historicos_agregados(seq_qualificadores, data_inicio, data_fim)
            else:
                dados_hist = modelos.obter_dados_historicos(seq_qualificadores[0], data_inicio, data_fim)
            
            if len(dados_hist) < 12:
                return JSONResponse({'error': f'Dados históricos insuficientes. Encontrados: {len(dados_hist)} meses, mínimo: 12'}, status_code=400)
            
            resultado = modelos.projetar_arima(dados_hist, meses_projecao, config, ano_base)
                
        elif tipo_modelo == 'SARIMA':
            data_inicio = data_fim - relativedelta(years=4)
            
            if len(seq_qualificadores) > 1:
                dados_hist = modelos.obter_dados_historicos_agregados(seq_qualificadores, data_inicio, data_fim)
            else:
                dados_hist = modelos.obter_dados_historicos(seq_qualificadores[0], data_inicio, data_fim)
            
            if len(dados_hist) < 12:
                return JSONResponse({'error': f'Dados históricos insuficientes. Encontrados: {len(dados_hist)} meses, mínimo: 12'}, status_code=400)
            
            resultado = modelos.projetar_sarima(dados_hist, meses_projecao, config, ano_base)
        
        elif tipo_modelo == 'REGRESSAO':
            resultado = modelos.projetar_regressao_multipla(meses_projecao, config, ano_base)
        
        elif tipo_modelo == 'MEDIA_HISTORICA':
            data_inicio = data_fim - relativedelta(years=3)
            
            if len(seq_qualificadores) > 1:
                dados_hist = modelos.obter_dados_historicos_agregados(seq_qualificadores, data_inicio, data_fim)
            else:
                dados_hist = modelos.obter_dados_historicos(seq_qualificadores[0], data_inicio, data_fim)
            
            if len(dados_hist) == 0:
                return JSONResponse({'error': 'Não há dados históricos disponíveis'}, status_code=400)
            
            resultado = modelos.projetar_media_historica(dados_hist, meses_projecao, config, ano_base)
                
        elif tipo_modelo == 'XGBOOST':
            data_inicio = data_fim - relativedelta(years=3)
            
            if len(seq_qualificadores) > 1:
                dados_hist = modelos.obter_dados_historicos_agregados(seq_qualificadores, data_inicio, data_fim)
            else:
                dados_hist = modelos.obter_dados_historicos(seq_qualificadores[0], data_inicio, data_fim)
            
            if len(dados_hist) < 13:
                return JSONResponse({'error': f'Dados históricos insuficientes. Encontrados: {len(dados_hist)} meses, mínimo: 13'}, status_code=400)
            
            resultado = modelos.projetar_xgboost(dados_hist, meses_projecao, config, ano_base)

        elif tipo_modelo == 'LIGHTGBM':
            data_inicio = data_fim - relativedelta(years=3)
            
            if len(seq_qualificadores) > 1:
                dados_hist = modelos.obter_dados_historicos_agregados(seq_qualificadores, data_inicio, data_fim)
            else:
                dados_hist = modelos.obter_dados_historicos(seq_qualificadores[0], data_inicio, data_fim)
            
            if len(dados_hist) < 13:
                return JSONResponse({'error': f'Dados históricos insuficientes. Encontrados: {len(dados_hist)} meses, mínimo: 13'}, status_code=400)
            
            resultado = modelos.projetar_lightgbm(dados_hist, meses_projecao, config, ano_base)

        elif tipo_modelo == 'CRESCIMENTO_ANO':
            from ..services.formula_engine import projetar_crescimento_ultimo_ano
            anos_selecionados = data.get('anos_selecionados', [])
            mes_referencia = int(config.get('mes_referencia', 6))
            ano_ref = max(anos_selecionados) if anos_selecionados else ano_base - 1
            
            resultado = projetar_crescimento_ultimo_ano(
                seq_qualificadores=seq_qualificadores,
                ano_projecao=ano_base,
                ano_referencia=ano_ref,
                mes_referencia=mes_referencia,
                meses_projecao=meses_projecao,
            )

        elif tipo_modelo == 'MEDIA_CRESCIMENTO':
            from ..services.formula_engine import projetar_media_crescimento_anos
            anos_selecionados = data.get('anos_selecionados', [])
            mes_referencia = int(config.get('mes_referencia', 6))
            
            if not anos_selecionados:
                return JSONResponse({'error': 'Selecione pelo menos um ano na Base Histórica'}, status_code=400)
            
            resultado = projetar_media_crescimento_anos(
                seq_qualificadores=seq_qualificadores,
                ano_projecao=ano_base,
                anos_referencia=anos_selecionados,
                mes_referencia=mes_referencia,
                meses_projecao=meses_projecao,
            )

        else:
            return JSONResponse({'error': 'Modelo não suportado para cálculo automático'}, status_code=400)
        
        return JSONResponse({
            'projecao': _dataframe_to_json(resultado),
            'modelo': tipo_modelo,
            'qualificadores': seq_qualificadores,
        })
        
    except ValueError as e:
        return JSONResponse({'error': str(e)}, status_code=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({'error': f'Erro ao calcular projeção: {str(e)}'}, status_code=500)


@router.get('/simulador/qualificador/{id}/filhos')
@handle_exceptions
async def get_qualificador_filhos(id: int):
    """
    Retorna os qualificadores filhos de um qualificador.
    Usado para popular a seleção de qualificadores filhos no frontend.
    """
    qualificador = get_qualificador(id)
    if not qualificador:
        return JSONResponse({'error': 'Qualificador não encontrado'}, status_code=404)
    
    # Obter todos os filhos ativos
    filhos = qualificador.get_todos_filhos()
    
    resultado = [{
        'seq_qualificador': f.seq_qualificador,
        'num_qualificador': f.num_qualificador,
        'dsc_qualificador': f.dsc_qualificador,
        'nivel': f.nivel,
        'path_completo': f.path_completo,
        'is_folha': f.is_folha(),
    } for f in filhos]
    
    return JSONResponse({
        'qualificador_pai': {
            'seq_qualificador': qualificador.seq_qualificador,
            'dsc_qualificador': qualificador.dsc_qualificador,
        },
        'filhos': resultado,
        'total': len(resultado),
    })


# ==================== Helper Functions ====================

def _parse_model_config_from_form(form, tipo: str) -> dict:
    """Parse configuração de modelo econômico do formulário."""
    config = {}
    
    # Extrair parâmetros específicos do formulário
    for key, value in form.items():
        if key.startswith(f'{tipo}_config_'):
            param_name = key.replace(f'{tipo}_config_', '')
            # Converter valores numéricos
            if param_name in ['seasonal_periods', 'p', 'd', 'q', 'P', 'D', 'Q', 's', 'periodo_meses', 'n_estimators', 'max_depth', 'num_leaves', 'mes_referencia']:
                try:
                    config[param_name] = int(value)
                except (ValueError, TypeError):
                    pass
            elif param_name in ['fator_ajuste', 'alpha', 'beta0', 'beta1', 'beta2', 'val_pib', 'val_inflacao', 'learning_rate']:
                try:
                    config[param_name] = float(value)
                except (ValueError, TypeError):
                    pass
            elif param_name in ['damped_trend', 'auto_order', 'use_boxcox', 'considerar_sazonalidade']:
                config[param_name] = value == 'true' or value == True
            elif param_name == 'seq_qualificador':
                try:
                    config[param_name] = int(value)
                except (ValueError, TypeError):
                    pass
            elif param_name == 'seq_qualificadores':
                # Array de qualificadores selecionados (pode vir como JSON ou múltiplos valores)
                try:
                    if isinstance(value, str):
                        # Tentar parsear como JSON
                        config[param_name] = json.loads(value)
                    elif isinstance(value, list):
                        config[param_name] = [int(v) for v in value]
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass
            else:
                config[param_name] = value
            
    # Tratamento especial para REGRESSAO
    tipo_cenario = form.get(f'tipo_cenario_{tipo}')
    if tipo_cenario == 'REGRESSAO':
        parametros = []
        
        # Beta 0 = Intercepto
        if f'{tipo}_config_beta0' in form:
            try:
                config['alpha'] = float(form.get(f'{tipo}_config_beta0', 0) or 0)
            except ValueError:
                config['alpha'] = 0.0
            
        # Beta 1 + PIB
        if f'{tipo}_config_beta1' in form and f'{tipo}_config_val_pib' in form:
            try:
                parametros.append({
                    'nome': 'PIB',
                    'coeficiente': float(form.get(f'{tipo}_config_beta1', 0) or 0),
                    'valores_projetados': [float(form.get(f'{tipo}_config_val_pib', 0) or 0)],
                    'valores_historicos': []
                })
            except ValueError:
                pass
            
        # Beta 2 + Inflação
        if f'{tipo}_config_beta2' in form and f'{tipo}_config_val_inflacao' in form:
            try:
                parametros.append({
                    'nome': 'Inflação',
                    'coeficiente': float(form.get(f'{tipo}_config_beta2', 0) or 0),
                    'valores_projetados': [float(form.get(f'{tipo}_config_val_inflacao', 0) or 0)],
                    'valores_historicos': []
                })
            except ValueError:
                pass
            
        if parametros:
            config['parametros'] = parametros
    
    return config


def _dataframe_to_json(df):
    """Converte DataFrame pandas para formato JSON."""
    if df is None or len(df) == 0:
        return []
    
    # Converter para lista de dicionários
    records = df.to_dict('records')
    
    # Converter datetime para string
    for record in records:
        if 'data' in record:
            record['data'] = record['data'].strftime('%Y-%m-%d') if hasattr(record['data'], 'strftime') else str(record['data'])
    
    return records


def _salvar_parametros_formula(form, seq_simulador_cenario: int):
    """Extrai e salva parâmetros de fórmula do formulário."""
    from ..repositories import formula_repository as f_repo
    
    parametros = {}
    for key, value in form.items():
        if key.startswith('formula_param_') and value:
            nome = key.replace('formula_param_', '')
            try:
                parametros[nome] = float(value)
            except (ValueError, TypeError):
                pass
    
    if parametros:
        f_repo.set_valores_cenario_batch(seq_simulador_cenario, parametros)


def _parse_config_base_from_form(form) -> str:
    """Extrai configuração da base histórica do formulário."""
    cod_metodo_base = form.get('cod_metodo_base', 'MEDIA_SIMPLES')
    config = {}
    
    if cod_metodo_base == 'VALOR_FIXO':
        valor = form.get('valor_fixo_cenario', '0')
        try:
            config['valor'] = float(valor)
        except (ValueError, TypeError):
            config['valor'] = 0
    else:
        anos_str = form.get('anos_selecionados_cenario', '[]')
        try:
            anos = json.loads(anos_str)
            config['anos'] = [int(a) for a in anos]
        except (json.JSONDecodeError, TypeError):
            config['anos'] = []

        if cod_metodo_base == 'MEDIA_PONDERADA' and config.get('anos'):
            pesos = {}
            for ano in config['anos']:
                peso_val = form.get(f'peso_cenario_{ano}', '1')
                try:
                    pesos[str(ano)] = float(peso_val)
                except (ValueError, TypeError):
                    pesos[str(ano)] = 1.0
            config['pesos'] = pesos

    return json.dumps(config)


# ==================== Histórico de Projeções ====================

@router.get('/simulador/{id}/historico')
@handle_exceptions
async def simulador_historico_listar(request: Request, id: int):
    """Lista as versões salvas da projeção de um cenário."""
    from ..services import projecao_versao_service as historico_service

    simulador = get_simulador(id)
    if not simulador:
        return RedirectResponse(url='/simulador', status_code=303)

    versoes = historico_service.list_versoes(id)
    return templates.TemplateResponse(
        'simulador_historico.html',
        {
            'request': request,
            'simulador': simulador,
            'versoes': versoes,
        },
    )


@router.post('/simulador/{id}/historico/salvar')
@handle_exceptions
async def simulador_historico_salvar(request: Request, id: int):
    """Salva o estado atual da projeção como uma nova versão."""
    from ..services import projecao_versao_service as historico_service

    form = await request.form()
    nom_versao = (form.get('nom_versao') or '').strip()
    dsc_motivo = (form.get('dsc_motivo') or '').strip() or None
    publicar = form.get('publicar') in ('S', 'on', 'true', '1')

    if not nom_versao:
        return JSONResponse({'error': 'nom_versao é obrigatório'}, status_code=400)

    try:
        historico_service.salvar_projecao_como_versao(
            seq_simulador_cenario=id,
            nom_versao=nom_versao,
            dsc_motivo=dsc_motivo,
            publicar=publicar,
        )
    except ValueError as exc:
        return JSONResponse({'error': str(exc)}, status_code=400)

    return RedirectResponse(url=f'/simulador/{id}/historico', status_code=303)


@router.get('/simulador/{id}/historico/comparar')
@handle_exceptions
async def simulador_historico_comparar(request: Request, id: int, v1: int, v2: int):
    """Comparativo entre duas versões salvas (RF-25)."""
    from ..services import projecao_versao_service as historico_service

    simulador = get_simulador(id)
    if not simulador:
        return RedirectResponse(url='/simulador', status_code=303)

    try:
        comparativo = historico_service.comparar_versoes(v1, v2)
    except ValueError as exc:
        return JSONResponse({'error': str(exc)}, status_code=400)

    if comparativo is None:
        return RedirectResponse(url=f'/simulador/{id}/historico', status_code=303)

    return templates.TemplateResponse(
        'simulador_historico_comparar.html',
        {
            'request': request,
            'simulador': simulador,
            'comparativo': comparativo,
            'meses_nomes': MONTH_NAME_PT,
        },
    )


@router.get('/simulador/{id}/historico/{seq_versao}')
@handle_exceptions
async def simulador_historico_detalhe(request: Request, id: int, seq_versao: int):
    """Visualiza o detalhe (linhas) de uma versão salva."""
    from ..services import projecao_versao_service as historico_service

    simulador = get_simulador(id)
    if not simulador:
        return RedirectResponse(url='/simulador', status_code=303)

    detalhe = historico_service.get_versao_detalhe(seq_versao)
    if detalhe is None:
        return RedirectResponse(url=f'/simulador/{id}/historico', status_code=303)

    return templates.TemplateResponse(
        'simulador_historico_detalhe.html',
        {
            'request': request,
            'simulador': simulador,
            'detalhe': detalhe,
            'meses_nomes': MONTH_NAME_PT,
        },
    )


@router.post('/simulador/{id}/historico/{seq_versao}/publicar')
@handle_exceptions
async def simulador_historico_publicar(request: Request, id: int, seq_versao: int):
    """Marca uma versão como publicada (imutável)."""
    from ..services import projecao_versao_service as historico_service
    historico_service.publicar_versao(seq_versao)
    return RedirectResponse(url=f'/simulador/{id}/historico', status_code=303)


@router.post('/simulador/{id}/historico/{seq_versao}/deletar')
@handle_exceptions
async def simulador_historico_deletar(request: Request, id: int, seq_versao: int):
    """Deleta uma versão (apenas rascunhos)."""
    from ..services import projecao_versao_service as historico_service
    try:
        historico_service.deletar_versao(seq_versao)
    except ValueError as exc:
        return JSONResponse({'error': str(exc)}, status_code=400)
    return RedirectResponse(url=f'/simulador/{id}/historico', status_code=303)


@router.post('/simulador/{id}/historico/{seq_versao}/atualizar-realizado')
@handle_exceptions
async def simulador_historico_atualizar_realizado(request: Request, id: int, seq_versao: int):
    """Preenche val_realizado agregando flc_lancamento (frustração x excesso)."""
    from ..services import projecao_versao_service as historico_service
    try:
        historico_service.atualizar_realizados_de_lancamentos(seq_versao)
    except ValueError as exc:
        return JSONResponse({'error': str(exc)}, status_code=400)
    return RedirectResponse(
        url=f'/simulador/{id}/historico/{seq_versao}', status_code=303
    )
