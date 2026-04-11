-- =====================================================
-- Migração: Fórmulas de Projeção LOA
-- Atualiza fórmulas existentes e cria novas
-- =====================================================

-- ==================== PARÂMETROS GLOBAIS ====================

-- Novos parâmetros (INSERT OR IGNORE para não duplicar)
INSERT OR IGNORE INTO flc_parametro_global (nom_parametro, dsc_parametro, cod_tipo, ind_status, dat_inclusao) VALUES
  ('pib_real', 'Crescimento real do PIB estadual', 'P', 'A', date('now')),
  ('efeito_legislacao', 'Efeito ± de mudanças legais (R$)', 'V', 'A', date('now')),
  ('variacao_frota', 'Crescimento líquido da frota tributável (SENATRAN)', 'P', 'A', date('now')),
  ('variacao_fipe', 'Variação média da tabela FIPE veículos usados', 'P', 'A', date('now')),
  ('crescimento_transacoes', 'Variação estimada no volume de transmissões ITCMD', 'P', 'A', date('now')),
  ('percentual_fecoep_sobre_icms', 'Participação histórica FECOEP/ICMS (ex: 0.05)', 'P', 'A', date('now')),
  ('saldo_medio_aplicado', 'Saldo médio projetado das disponibilidades aplicadas (R$)', 'V', 'A', date('now')),
  ('taxa_selic_projetada', 'Selic média projetada para o exercício (Focus/BCB)', 'P', 'A', date('now')),
  ('fator_eficiencia', '% da Selic efetivamente capturado (0.85 a 0.98)', 'P', 'A', date('now')),
  ('vegetativo', 'Crescimento vegetativo da folha: progressões, anuênios', 'P', 'A', date('now')),
  ('reajuste_previsto', 'Reajuste salarial previsto em lei', 'P', 'A', date('now')),
  ('impacto_novas_admissoes', 'R$ estimado de concursos/contratações previstos', 'V', 'A', date('now')),
  ('folha_atual_anualizada', 'Folha mensal atual × 13 anualizada (R$)', 'V', 'A', date('now')),
  ('contratos_novos_previstos', 'R$ de novas contratações previstas para o exercício', 'V', 'A', date('now')),
  ('receita_federal_projetada_ir_ipi', 'Projeção federal de IR+IPI (PLOA União ou STN)', 'V', 'A', date('now')),
  ('coeficiente_al', 'Coeficiente de AL no FPE (fixado pelo TCU anualmente)', 'P', 'A', date('now')),
  ('deducao_fundeb', 'Dedução FUNDEB (20%) + PASEP (1%) = 0.21', 'P', 'A', date('now')),
  ('aliquota_efetiva_ir', 'Alíquota efetiva média de IRRF sobre a folha (0.06 a 0.10)', 'P', 'A', date('now')),
  ('receita_corrente_projetada_total', 'Soma de todas as receitas correntes projetadas (R$)', 'V', 'A', date('now')),
  ('receita_impostos_transferencias', 'Base: impostos próprios + transferências constitucionais (R$)', 'V', 'A', date('now')),
  ('rcl_projetada', 'Receita Corrente Líquida projetada (R$)', 'V', 'A', date('now')),
  ('percentual_limite_poder', '% da RCL do duodécimo de cada Poder (LDO/CE)', 'P', 'A', date('now')),
  ('projecao_icms', 'ICMS projetado — resultado da fórmula ICMS (R$)', 'V', 'A', date('now')),
  ('projecao_ipva', 'IPVA projetado — resultado da fórmula IPVA (R$)', 'V', 'A', date('now')),
  ('projecao_itcmd', 'ITCMD projetado — resultado da fórmula ITCMD (R$)', 'V', 'A', date('now')),
  ('projecao_fpe_bruto', 'FPE bruto projetado antes de deduções (R$)', 'V', 'A', date('now')),
  ('projecao_folha_bruta', 'Folha bruta projetada — resultado da fórmula FOLHA (R$)', 'V', 'A', date('now')),
  ('repasse_fundeb', 'Valor FUNDEB projetado — resultado da fórmula FUNDEB (R$)', 'V', 'A', date('now'));

-- ==================== ATUALIZAR FÓRMULAS EXISTENTES ====================

-- 1. ICMS (seq_qualificador=3) — adicionar efeito_legislacao, usar pib_real
UPDATE flc_rubrica_formula
SET dsc_formula_expressao = 'base * (1 + ipca) * (1 + pib_real * elasticidade) + efeito_legislacao',
    json_config_base = '{"anos": [2023, 2024, 2025]}'
WHERE seq_qualificador = 3;

-- 2. IPVA (seq_qualificador=4) — corrigir para variação frota + FIPE
UPDATE flc_rubrica_formula
SET nom_formula = 'Projeção IPVA',
    dsc_formula_expressao = 'base * (1 + variacao_frota) * (1 + variacao_fipe) + efeito_legislacao',
    json_config_base = '{"anos": [2023, 2024, 2025]}'
WHERE seq_qualificador = 4;

-- 3. FPE (seq_qualificador=7) — fórmula completa
UPDATE flc_rubrica_formula
SET nom_formula = 'Projeção FPE',
    dsc_formula_expressao = 'receita_federal_projetada_ir_ipi * 0.215 * coeficiente_al * (1 - deducao_fundeb)',
    cod_metodo_base = 'MEDIA_SIMPLES',
    json_config_base = '{"anos": [2024, 2025]}'
WHERE seq_qualificador = 7;

-- ==================== CRIAR NOVAS FÓRMULAS ====================

-- RECEITAS --

-- ITCMD (seq_qualificador=5)
INSERT OR IGNORE INTO flc_rubrica_formula (seq_qualificador, nom_formula, dsc_formula_expressao, cod_metodo_base, json_config_base, ind_status, dat_inclusao)
VALUES (5, 'Projeção ITCMD', 'base * (1 + ipca) * (1 + crescimento_transacoes) + efeito_legislacao', 'MEDIA_SIMPLES', '{"anos": [2023, 2024, 2025]}', 'A', date('now'));

-- FECOEP (seq_qualificador=9) — derivada do ICMS
INSERT OR IGNORE INTO flc_rubrica_formula (seq_qualificador, nom_formula, dsc_formula_expressao, cod_metodo_base, json_config_base, ind_status, dat_inclusao)
VALUES (9, 'Projeção FECOEP', 'projecao_icms * percentual_fecoep_sobre_icms', 'MEDIA_SIMPLES', '{"anos": [2023, 2024, 2025]}', 'A', date('now'));

-- APLICAÇÕES FINANCEIRAS (seq_qualificador=11)
INSERT OR IGNORE INTO flc_rubrica_formula (seq_qualificador, nom_formula, dsc_formula_expressao, cod_metodo_base, json_config_base, ind_status, dat_inclusao)
VALUES (11, 'Projeção Aplicações Financeiras', 'saldo_medio_aplicado * taxa_selic_projetada * fator_eficiencia', 'MEDIA_SIMPLES', '{"anos": [2024, 2025]}', 'A', date('now'));

-- IR Retido na Fonte (seq_qualificador=12) — derivada da folha
INSERT OR IGNORE INTO flc_rubrica_formula (seq_qualificador, nom_formula, dsc_formula_expressao, cod_metodo_base, json_config_base, ind_status, dat_inclusao)
VALUES (12, 'Projeção IR Retido', 'projecao_folha_bruta * aliquota_efetiva_ir', 'MEDIA_SIMPLES', '{"anos": [2024, 2025]}', 'A', date('now'));

-- OUTRAS RECEITAS (seq_qualificador=13)
INSERT OR IGNORE INTO flc_rubrica_formula (seq_qualificador, nom_formula, dsc_formula_expressao, cod_metodo_base, json_config_base, ind_status, dat_inclusao)
VALUES (13, 'Projeção Outras Receitas', 'base * (1 + ipca)', 'MEDIA_SIMPLES', '{"anos": [2023, 2024, 2025]}', 'A', date('now'));

-- DESPESAS --

-- FOLHA (seq_qualificador=16)
INSERT OR IGNORE INTO flc_rubrica_formula (seq_qualificador, nom_formula, dsc_formula_expressao, cod_metodo_base, json_config_base, ind_status, dat_inclusao)
VALUES (16, 'Projeção Folha de Pessoal', 'folha_atual_anualizada * (1 + vegetativo) * (1 + reajuste_previsto) + impacto_novas_admissoes', 'MEDIA_SIMPLES', '{"anos": [2024, 2025]}', 'A', date('now'));

-- PASEP (seq_qualificador=17) — derivada da receita total
INSERT OR IGNORE INTO flc_rubrica_formula (seq_qualificador, nom_formula, dsc_formula_expressao, cod_metodo_base, json_config_base, ind_status, dat_inclusao)
VALUES (17, 'Projeção PASEP', 'receita_corrente_projetada_total * 0.01', 'MEDIA_SIMPLES', '{"anos": [2024, 2025]}', 'A', date('now'));

-- CUSTEIO (seq_qualificador=22)
INSERT OR IGNORE INTO flc_rubrica_formula (seq_qualificador, nom_formula, dsc_formula_expressao, cod_metodo_base, json_config_base, ind_status, dat_inclusao)
VALUES (22, 'Projeção Custeio', 'base * (1 + ipca) + contratos_novos_previstos', 'MEDIA_SIMPLES', '{"anos": [2023, 2024, 2025]}', 'A', date('now'));

-- REPASSE MUNICÍPIOS (seq_qualificador=26) — derivada
INSERT OR IGNORE INTO flc_rubrica_formula (seq_qualificador, nom_formula, dsc_formula_expressao, cod_metodo_base, json_config_base, ind_status, dat_inclusao)
VALUES (26, 'Projeção Repasse Municípios', 'projecao_icms * 0.25 + projecao_ipva * 0.50', 'MEDIA_SIMPLES', '{"anos": [2024, 2025]}', 'A', date('now'));

-- REPASSE FUNDEB (seq_qualificador=27) — derivada
INSERT OR IGNORE INTO flc_rubrica_formula (seq_qualificador, nom_formula, dsc_formula_expressao, cod_metodo_base, json_config_base, ind_status, dat_inclusao)
VALUES (27, 'Projeção Repasse FUNDEB', '(projecao_icms + projecao_fpe_bruto + projecao_ipva + projecao_itcmd) * 0.20', 'MEDIA_SIMPLES', '{"anos": [2024, 2025]}', 'A', date('now'));

-- SAÚDE 12% (seq_qualificador=28) — derivada
INSERT OR IGNORE INTO flc_rubrica_formula (seq_qualificador, nom_formula, dsc_formula_expressao, cod_metodo_base, json_config_base, ind_status, dat_inclusao)
VALUES (28, 'Projeção Saúde 12%', 'receita_impostos_transferencias * 0.12', 'MEDIA_SIMPLES', '{"anos": [2024, 2025]}', 'A', date('now'));

-- EDUCAÇÃO 5% (seq_qualificador=29) — derivada
INSERT OR IGNORE INTO flc_rubrica_formula (seq_qualificador, nom_formula, dsc_formula_expressao, cod_metodo_base, json_config_base, ind_status, dat_inclusao)
VALUES (29, 'Projeção Educação 5%', 'receita_impostos_transferencias * 0.25 - repasse_fundeb', 'MEDIA_SIMPLES', '{"anos": [2024, 2025]}', 'A', date('now'));

-- PODERES (seq_qualificador=30) — derivada da RCL
INSERT OR IGNORE INTO flc_rubrica_formula (seq_qualificador, nom_formula, dsc_formula_expressao, cod_metodo_base, json_config_base, ind_status, dat_inclusao)
VALUES (30, 'Projeção Poderes', 'rcl_projetada * percentual_limite_poder', 'MEDIA_SIMPLES', '{"anos": [2024, 2025]}', 'A', date('now'));

-- ==================== VERIFICAÇÃO ====================
-- SELECT COUNT(*) as total_formulas FROM flc_rubrica_formula WHERE ind_status='A';
-- SELECT COUNT(*) as total_parametros FROM flc_parametro_global WHERE ind_status='A';
