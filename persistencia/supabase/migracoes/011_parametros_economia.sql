-- RF-448 (T-435): hipóteses de economia do aluno deficitário (5% e 10% da renda).
-- Colunas opcionais: as versões 1.0.1 e 1.0.2 não as têm e continuam válidas.
ALTER TABLE motor_calculo.parametros
    ADD COLUMN IF NOT EXISTS "P_ECONOMIA_RENDA_CENARIO_1" numeric NULL,
    ADD COLUMN IF NOT EXISTS "P_ECONOMIA_RENDA_CENARIO_2" numeric NULL;
