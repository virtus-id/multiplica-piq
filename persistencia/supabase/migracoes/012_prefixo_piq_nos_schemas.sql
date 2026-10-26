-- RF-455..RF-459 (T-441): os schemas do PIQ passam a começar com `piq_`, para
-- se distinguirem dos demais sistemas que dividem o mesmo banco.
--
--   app_aluno     -> piq_app_aluno
--   motor_calculo -> piq_motor_calculo
--
-- Só metadado, sem mover dado: tabelas, índices, FKs, gatilhos, funções e
-- REVOKE acompanham o schema. Idempotente: só renomeia se o nome antigo
-- existe e o novo não. As migrações 001 a 011 seguem intactas (citam os nomes
-- antigos) e devem rodar ANTES desta.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'app_aluno')
       AND NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'piq_app_aluno') THEN
        ALTER SCHEMA app_aluno RENAME TO piq_app_aluno;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'motor_calculo')
       AND NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'piq_motor_calculo') THEN
        ALTER SCHEMA motor_calculo RENAME TO piq_motor_calculo;
    END IF;
END
$$;

-- RF-457: a mensagem de erro cita o schema; o gatilho referencia a função por
-- OID, então o CREATE OR REPLACE atualiza o texto sem recriar o gatilho.
CREATE OR REPLACE FUNCTION piq_motor_calculo.impedir_sobrescrita_v01()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'V-01: piq_motor_calculo.snapshots é append-only — % em % não é permitido (SNAPSHOT_ID=%)',
        TG_OP, TG_TABLE_NAME, COALESCE(OLD."SNAPSHOT_ID", 'desconhecido');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION piq_app_aluno.impedir_sobrescrita_revisao_v01()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'RF-24: piq_app_aluno.revisoes é append-only — % em % não é permitido (revisao_id=%)',
        TG_OP, TG_TABLE_NAME, COALESCE(OLD.revisao_id, 'desconhecido');
END;
$$ LANGUAGE plpgsql;
