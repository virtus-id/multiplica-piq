"""Valores neutros no lugar das perguntas retiradas na `T-404` (`RF-418`, `RF-403`).

`B1.02`, `B1.05`, `B1.10`, `B9.04`, `B2.01` a `B2.05`, `B2.07`, `B3.02`,
`B3.02A`, `B3.05A`, `B3.NM02D`, `B3.S01`, `B3.S03`, `B5.A02V` e `B5.C07` saíram
dos registros. A montagem entrega valores neutros, sem tocar `engine/`
(`app/montagem/estado.py`). Este arquivo prova:

(a) o plano é calculado sem essas respostas;
(b) para um caso sem sinais de risco o resultado é o esperado com os neutros:
    nível de controle `PARCIAL`, confiabilidade `MEDIA` e fator de segurança
    menor que o do perfil "forte" que as respostas antigas permitiam;
(c) quem tem `B2.06` ou `B2.12` fracos continua `FRAGIL`/`BAIXA`;
(d) a renda variável perde a redução de segurança de renda variável.

REGRAS: `RF-418`, `RF-403`, `AC-407`
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from app.montagem.estado import montar_divida, montar_estado_financeiro
from engine.comportamento import derivar_CONFIABILIDADE_DADOS, derivar_NIVEL_CONTROLE
from engine.diagnostico import calcular_fator_seguranca
from engine.estado import (
    COBERTURA_MEIOS_PAGAMENTO,
    COBERTURA_PEQUENOS_GASTOS,
    DEFASAGEM_REGISTRO,
    FREQUENCIA_REGISTRO,
    GASTOS_NAO_IDENTIFICADOS,
    REGISTRO_GASTOS,
    TIPO_RENDA,
    EstadoFinanceiro,
)
from engine.motor import calcular_plano
from engine.tipos import CONFIABILIDADE_DADOS, NIVEL_CONTROLE, NIVEL_RISCO, SimNaoTalvez
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.app_aluno.fixtures.caso_completo import (
    DATA_REFERENCIA,
    DIVIDA_ID_UNICA,
    PARAMETROS_EXTERNOS_PADRAO,
    caso_completo,
)

_PARAMETROS = FonteParametrosArquivo().carregar("1.0.1")


def _estado(**valores_caso: object) -> EstadoFinanceiro:
    respostas = caso_completo(valores_caso=valores_caso).respostas
    return montar_estado_financeiro(
        respostas,
        DATA_REFERENCIA=DATA_REFERENCIA,
        dividas=(montar_divida(respostas, DIVIDA_ID_UNICA),),
        **PARAMETROS_EXTERNOS_PADRAO,  # type: ignore[arg-type]
    )


def test_a_plano_e_calculado_sem_as_respostas_removidas() -> None:
    estado = _estado()

    snapshot = calcular_plano(estado, _PARAMETROS)

    assert snapshot.DIVIDA_ALVO_ATUAL == DIVIDA_ID_UNICA
    assert estado.TIPO_RENDA is TIPO_RENDA.RELATIVAMENTE_ESTAVEL
    assert estado.sinais_comportamentais.NOVA_DIVIDA_PREVISTA is SimNaoTalvez.NAO
    assert estado.sinais_comportamentais.HISTORICO_RECAIDA is SimNaoTalvez.TALVEZ
    assert estado.sinais_comportamentais.HISTORICO_ABANDONO is SimNaoTalvez.TALVEZ
    assert estado.sinais_comportamentais.JANELA_NOVA_DIVIDA is None
    perfil = estado.perfil_comportamental
    assert perfil.REGISTRO_GASTOS is REGISTRO_GASTOS.PARTE
    assert perfil.FREQUENCIA_REGISTRO is FREQUENCIA_REGISTRO.INDEFINIDA
    assert perfil.DEFASAGEM_REGISTRO is DEFASAGEM_REGISTRO.DIAS_DEPOIS
    assert perfil.COBERTURA_PEQUENOS_GASTOS is COBERTURA_PEQUENOS_GASTOS.ALGUNS
    assert perfil.COBERTURA_MEIOS_PAGAMENTO is COBERTURA_MEIOS_PAGAMENTO.QUASE_TOTAL
    assert perfil.GASTOS_NAO_IDENTIFICADOS is GASTOS_NAO_IDENTIFICADOS.ALGUMAS_MES


def test_b_sem_sinais_de_risco_controle_parcial_confiabilidade_media_e_fator_menor() -> None:
    estado = _estado()
    depois = calcular_plano(estado, _PARAMETROS).diagnostico

    assert depois.NIVEL_CONTROLE is NIVEL_CONTROLE.PARCIAL
    assert depois.CONFIABILIDADE_DADOS is CONFIABILIDADE_DADOS.MEDIA
    assert depois.RISCO_RECAIDA is NIVEL_RISCO.BAIXO
    assert depois.RISCO_COMPORTAMENTAL_GERAL is NIVEL_RISCO.BAIXO
    assert depois.FATOR_SEGURANCA == Decimal(1) - _PARAMETROS.numero(
        "P_REDUCAO_CONFIABILIDADE_MEDIA"
    )

    # O que as respostas antigas ("registro de tudo, todo dia") davam: forte e alta.
    forte = replace(
        estado.perfil_comportamental,
        REGISTRO_GASTOS=REGISTRO_GASTOS.TUDO,
        FREQUENCIA_REGISTRO=FREQUENCIA_REGISTRO.DIARIA,
        DEFASAGEM_REGISTRO=DEFASAGEM_REGISTRO.NA_HORA,
        COBERTURA_PEQUENOS_GASTOS=COBERTURA_PEQUENOS_GASTOS.TODOS,
        COBERTURA_MEIOS_PAGAMENTO=COBERTURA_MEIOS_PAGAMENTO.TOTAL,
        GASTOS_NAO_IDENTIFICADOS=GASTOS_NAO_IDENTIFICADOS.NUNCA,
    )
    antes = calcular_plano(replace(estado, perfil_comportamental=forte), _PARAMETROS).diagnostico
    assert antes.NIVEL_CONTROLE is NIVEL_CONTROLE.FORTE
    assert antes.CONFIABILIDADE_DADOS is CONFIABILIDADE_DADOS.ALTA
    assert antes.FATOR_SEGURANCA > depois.FATOR_SEGURANCA
    assert antes.CAPACIDADE_ATAQUE_CONSERVADORA > depois.CAPACIDADE_ATAQUE_CONSERVADORA


def test_c_conhecimento_ou_revisao_fracos_seguem_fragil_e_baixa() -> None:
    for campo, valor in (("CONHECIMENTO_GASTO", "NAO_SEI"), ("REVISAO_SEMANAL", "NUNCA")):
        perfil = _estado(**{campo: valor}).perfil_comportamental

        nivel = derivar_NIVEL_CONTROLE(perfil)

        assert nivel is NIVEL_CONTROLE.FRAGIL
        assert derivar_CONFIABILIDADE_DADOS(nivel, perfil) is CONFIABILIDADE_DADOS.BAIXA


def test_d_resposta_antiga_de_renda_variavel_nao_aciona_a_reducao() -> None:
    estado = _estado(TIPO_RENDA="VARIAVEL")
    assert estado.TIPO_RENDA is TIPO_RENDA.RELATIVAMENTE_ESTAVEL

    args = (CONFIABILIDADE_DADOS.MEDIA, NIVEL_RISCO.BAIXO, NIVEL_RISCO.BAIXO, _PARAMETROS)
    estavel = calcular_fator_seguranca(estado.TIPO_RENDA, *args)
    variavel = calcular_fator_seguranca(TIPO_RENDA.VARIAVEL, *args)

    assert variavel.FATOR_SEGURANCA == estavel.FATOR_SEGURANCA - _PARAMETROS.numero(
        "P_REDUCAO_RENDA_VARIAVEL"
    )
