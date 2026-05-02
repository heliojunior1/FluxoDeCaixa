-- Histórico de projeções (Alternativa 2): cabeçalho versionado + linhas normalizadas.
-- Compatível com SQLite e PostgreSQL. Idempotente (CREATE TABLE IF NOT EXISTS).
-- A criação automática também é feita por ensure_projecao_historico_schema()
-- e Base.metadata.create_all() no boot do app — este arquivo cobre deploys
-- onde o boot não roda (psql/sqlite3 manual).

CREATE TABLE IF NOT EXISTS flc_projecao_versao (
    seq_projecao_versao   INTEGER PRIMARY KEY,
    seq_simulador_cenario INTEGER NOT NULL,
    nom_versao            VARCHAR(80) NOT NULL,
    dsc_motivo            VARCHAR(255),
    dat_versao            TIMESTAMP NOT NULL,
    cod_pessoa            INTEGER,
    ind_publicado         CHAR(1) NOT NULL DEFAULT 'N',
    json_inputs           TEXT,
    json_resumo           TEXT,
    FOREIGN KEY (seq_simulador_cenario)
        REFERENCES flc_simulador_cenario (seq_simulador_cenario)
);

CREATE TABLE IF NOT EXISTS flc_projecao_valor (
    seq_projecao_valor    INTEGER PRIMARY KEY,
    seq_projecao_versao   INTEGER NOT NULL,
    seq_qualificador      INTEGER,
    cod_tipo              CHAR(1) NOT NULL,
    ano                   INTEGER NOT NULL,
    mes                   INTEGER NOT NULL,
    val_projetado         NUMERIC(18,2) NOT NULL DEFAULT 0,
    val_realizado         NUMERIC(18,2),
    FOREIGN KEY (seq_projecao_versao)
        REFERENCES flc_projecao_versao (seq_projecao_versao)
        ON DELETE CASCADE,
    FOREIGN KEY (seq_qualificador)
        REFERENCES flc_qualificador (seq_qualificador)
);

CREATE INDEX IF NOT EXISTS ix_projecao_valor_versao_qual_periodo
    ON flc_projecao_valor (seq_projecao_versao, seq_qualificador, ano, mes);

CREATE INDEX IF NOT EXISTS ix_projecao_valor_tipo
    ON flc_projecao_valor (cod_tipo);
