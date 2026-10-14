"""Remoção de perguntas sem efeito no cálculo — `T-389` (`RF-402`).

O especialista retirou 87 perguntas dos Blocos 1 a 5 que o motor não lê
(`specs/enxugamento-questionario.spec.md`, RF-402; a lista é a de `T-389`,
menos `B3.S03` e `B5.I01`, que ficaram porque outras perguntas dependem
delas). Este arquivo prova duas coisas:

1. nenhuma delas existe mais nos registros (e os IDs não são reaproveitados);
2. para os casos de prova que usam respostas (`caso_completo`, o de `GAB-03`
   e o perfil T02 de duas dívidas), o `EstadoFinanceiro` montado e o
   `SnapshotOrdem` calculado são IDÊNTICOS com e sem as respostas dessas
   perguntas — cada uma sozinha e todas juntas. Respostas já gravadas de caso
   antigo ficam no banco e são ignoradas (`RespostasCaso` não quebra).

`GAB-A/B/C` (`tests/fixtures/gab_*.json`) entram no motor como
`EstadoFinanceiro` pronto, sem passar por respostas; a remoção não os toca
(o motor e os parâmetros não mudaram) e eles seguem cobertos por
`tests/gabaritos/`.

`specs/piq-app-spec.md` (canônica congelada) continua listando as 87: a
nova versão da canônica é decisão do especialista. Por isso a lista vive
aqui, com a origem acima.

REGRAS: `RF-402`, `AC-13`, `AC-18`
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.montagem.estado import montar_divida, montar_estado_financeiro
from collection.carga import carregar_registros
from collection.respostas import Resposta, RespostasCaso, ValorResposta
from engine.estado import EstadoFinanceiro
from engine.motor import calcular_plano
from engine.snapshot import SnapshotOrdem
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.app_aluno.fixtures.caso_completo import (
    CASO_ID,
    DATA_REFERENCIA,
    DESPESA_NAO_MENSAL_ID_UNICA,
    DIVIDA_ID_UNICA,
    ITEM_DESPESA_ID_UNICA,
    PARAMETROS_EXTERNOS_PADRAO,
    QUESTIONARIO_VERSION,
    RESPONDIDA_EM,
    caso_completo,
    caso_completo_com_divida_gab03,
)
from tests.app_aluno.test_plano_ponta_a_ponta import _respostas_t02

# Item de cada escopo de repetição onde a pergunta removida era respondida.
# Os de despesa e de dívida reaproveitam as fichas que a fixture já tem, para
# que a resposta removida caia ao lado das que o motor lê.
_ITEM_POR_ESCOPO: dict[str, str] = {
    "DIVIDA_ID": DIVIDA_ID_UNICA,
    "ITEM_DESPESA": ITEM_DESPESA_ID_UNICA,
    "DESPESA_NAO_MENSAL_ID": DESPESA_NAO_MENSAL_ID_UNICA,
    "VINCULO_ID": "V001",
    "MARGEM_ID": "M001",
    "RENDA_ADICIONAL_ID": "REND001",
    "RECURSO_EXTRAORDINARIO_ID": "EXT001",
}

# (ID da pergunta, VARIAVEL_GRAVADA como era no registro, escopo, valor de
# teste). Origem da lista: `specs/enxugamento-questionario.spec.md`, RF-402.
_REMOVIDAS: tuple[tuple[str, str, str | None, ValorResposta], ...] = (
    ("B1.03", "FINALIDADE_NOVA_DIVIDA", None, "NECESSIDADE"),
    ("B1.03A", "FINALIDADE_NOVA_DIVIDA_OUTRA", None, "Texto"),
    ("B1.04", "VALOR_NOVA_DIVIDA", None, Decimal("123.45")),
    ("B1.06", "OBRIGACAO_FUTURA_INEVITAVEL", None, "SIM"),
    ("B1.06A", "TIPO_OBRIGACAO_FUTURA", None, "IMPOSTO_OU_OBRIGACAO_ANUAL"),
    ("B1.06B", "VALOR_OBRIGACAO_FUTURA", None, Decimal("123.45")),
    ("B1.06C", "JANELA_OBRIGACAO_FUTURA", None, "ATE_30D"),
    ("B1.08", "USO_CREDITO_PREVISTO", None, frozenset({"DESPESAS_MES"})),
    ("B1.11", "CAUSA_RECAIDA", None, "RENDA_INSUFICIENTE"),
    ("B1.12", "PARTICIPACAO_FAMILIAR", None, "NAO_APLICAVEL"),
    ("B2.05A", "MEIOS_PAGAMENTO_FORA_CONTROLE", None, frozenset({"PIX"})),
    ("B2.08", "VALOR_GASTOS_NAO_IDENTIFICADOS", None, Decimal("123.45")),
    ("B3.02B", "RENDA_VARIAVEL_PISO_DECLARADO", None, Decimal("123.45")),
    ("B3.03A", "TIPO_RENDA_ADICIONAL", "RENDA_ADICIONAL_ID", "SEGUNDO_TRABALHO_OU_VINCULO"),
    ("B3.03AO", "DESCRICAO_RENDA_ADICIONAL", "RENDA_ADICIONAL_ID", "Texto"),
    ("B3.03C", "TIPO_RENDA_ADICIONAL_ESTABILIDADE", "RENDA_ADICIONAL_ID", "FIXA"),
    ("B3.05AO", "DESCRICAO_RECURSO_EXTRAORDINARIO", "RECURSO_EXTRAORDINARIO_ID", "Texto"),
    ("B3.06", "RENDA_EXTRA_RECORRENTE_POTENCIAL_EXISTE", None, "CONCRETA"),
    ("B3.06A", "ORIGEM_RENDA_EXTRA_POTENCIAL", None, "TRABALHO_EXTRA"),
    ("B3.06B", "RENDA_EXTRA_RECORRENTE_POTENCIAL", None, Decimal("123.45")),
    ("B3.DF03", "CLASSIFICACAO_OBRIGATORIA", "ITEM_DESPESA", "OBRIGATORIA"),
    ("B3.DF04", "QUALIDADE_VALOR_DESPESA", "ITEM_DESPESA", "CONFIRMADA"),
    ("B3.NM02A", "TIPO_DESPESA_NAO_MENSAL", "DESPESA_NAO_MENSAL_ID", "IPTU"),
    ("B3.NM02AO", "DESCRICAO_DESPESA_NAO_MENSAL", "DESPESA_NAO_MENSAL_ID", "Texto"),
    ("B3.NM02C", "FREQUENCIA_DESPESA_NAO_MENSAL", "DESPESA_NAO_MENSAL_ID", "ANUAL"),
    ("B3.NM02CO", "DESCRICAO_FREQUENCIA_DESPESA_NAO_MENSAL", "DESPESA_NAO_MENSAL_ID", "Texto"),
    ("B3.S02", "REGIME_MARGEM", "VINCULO_ID", frozenset({"FEDERAL"})),
    ("B3.S04", "RENDA_BRUTA_VINCULO", "VINCULO_ID", Decimal("123.45")),
    ("B3.S04L", "RENDA_LIQUIDA_VINCULO", "VINCULO_ID", Decimal("123.45")),
    ("B3.S05", "ACESSO_MARGENS", "VINCULO_ID", "SIM"),
    ("B3.S05C", "CONSIGNACAO_EXISTE_VINCULO", "VINCULO_ID", "SIM"),
    ("B3.S06A", "TIPO_MARGEM", "MARGEM_ID", "EMPRESTIMO"),
    ("B3.S06AO", "DESCRICAO_MARGEM", "MARGEM_ID", "Texto"),
    ("B3.S06B", "VALOR_TOTAL_MARGEM", "MARGEM_ID", Decimal("123.45")),
    ("B3.S06C", "VALOR_UTILIZADO_MARGEM", "MARGEM_ID", Decimal("123.45")),
    ("B3.S06D", "VALOR_LIVRE_MARGEM", "MARGEM_ID", Decimal("123.45")),
    ("B3.S06E", "DATA_REFERENCIA_MARGEM", "MARGEM_ID", date(2026, 1, 15)),
    ("B3.S07", "MARGEM_A_LIBERAR_EXISTE", None, "SIM"),
    ("B3.S07A", "VALOR_A_LIBERAR_MARGEM", None, Decimal("123.45")),
    ("B3.S07B", "JANELA_LIBERACAO_MARGEM", None, "1_3M"),
    ("B3.S08", "DESCONTO_CONTRACHEQUE_NAO_RECONHECIDO", None, "SIM"),
    ("B4.02B", "LOCAL_RESERVA", None, frozenset({"CONTA_CORRENTE"})),
    ("B4.04A", "TIPO_INVESTIMENTO", None, "POUPANCA"),
    ("B4.06A", "CUSTO_DESMOBILIZACAO_INVESTIMENTOS", None, Decimal("123.45")),
    ("B4.06B", "DISPOSICAO_USO_INVESTIMENTO", None, "SIM"),
    ("B4.I02", "TIPO_IMOVEL", None, "CASA_APARTAMENTO_ONDE_MORO"),
    ("B4.I03", "VALOR_IMOVEL (= VALOR_ESTIMADO_ATIVO)", None, Decimal("123.45")),
    ("B4.I06", "CUSTO_IMOVEL", None, Decimal("123.45")),
    ("B4.I07", "IMOVEL_ESSENCIAL", None, "ESSENCIAL"),
    ("B4.I08", "POSSIBILIDADE_VENDA_IMOVEL", None, "NAO"),
    ("B4.I09", "CUSTOS_ESTIMADOS_DESMOBILIZACAO (imóvel)", None, Decimal("123.45")),
    ("B4.V02", "TIPO_VEICULO", None, "CARRO"),
    ("B4.V03", "VALOR_VEICULO (= VALOR_ESTIMADO_ATIVO)", None, Decimal("123.45")),
    ("B4.V04", "VEICULO_POSSUI_PASSIVO", None, "SIM"),
    ("B4.V04A", "SALDO_FINANCIAMENTO_VEICULO (= SALDO_PASSIVO_VINCULADO)", None, Decimal("123.45")),
    ("B4.V05", "CUSTO_RECORRENTE_VEICULO", None, Decimal("123.45")),
    ("B4.V06", "VEICULO_ESSENCIAL", None, "ESSENCIAL"),
    ("B4.V07", "POSSIBILIDADE_VENDA_VEICULO", None, "NAO"),
    ("B4.V08", "POSSIBILIDADE_SUBSTITUICAO", None, "SIM"),
    ("B4.V08A", "VALOR_VEICULO_SUBSTITUTO", None, Decimal("123.45")),
    ("B4.V08B", "SUBSTITUICAO_REDUZ_CUSTO", None, "SIM"),
    ("B4.V08C", "ECONOMIA_RECORRENTE_SUBSTITUICAO_VEICULO", None, Decimal("123.45")),
    ("B4.V09", "CUSTOS_ESTIMADOS_DESMOBILIZACAO (veículo)", None, Decimal("123.45")),
    ("B4.O01", "OUTRO_ATIVO_EXISTE", None, "SIM"),
    ("B4.O02", "TIPO_OUTRO_ATIVO", None, "EQUIPAMENTO_PROFISSIONAL"),
    ("B4.O03", "VALOR_ESTIMADO_ATIVO (outro)", None, Decimal("123.45")),
    ("B4.O04", "OUTRO_ATIVO_POSSUI_PASSIVO", None, "SIM"),
    ("B4.O04A", "SALDO_PASSIVO_VINCULADO (outro)", None, Decimal("123.45")),
    ("B4.O05", "RENDA_OUTRO_ATIVO", None, "SIM"),
    ("B4.O06", "CUSTO_OUTRO_ATIVO", None, "SIM"),
    ("B4.O07", "OUTRO_ATIVO_ESSENCIAL", None, "ESSENCIAL"),
    ("B4.O08", "POSSIBILIDADE_VENDA_OUTRO_ATIVO", None, "NAO"),
    ("B4.O09", "CUSTOS_ESTIMADOS_DESMOBILIZACAO (outro)", None, Decimal("123.45")),
    ("B4.F01", "CONFIRMACAO_MAPEAMENTO_PATRIMONIAL", None, "COMPLETO"),
    ("B5.00A", "TIPOS_DIVIDA_DECLARADOS", None, frozenset({"CONSIGNADO"})),
    ("B5.A03", "FINALIDADE_DIVIDA", "DIVIDA_ID", "PAGAR_DESPESAS_DO_MES"),
    ("B5.A05", "ORIGEM_RENEGOCIACAO", "DIVIDA_ID", "SIM"),
    ("B5.A05A", "DIVIDA_ANTERIOR_SUBSISTE", "DIVIDA_ID", "SUBSTITUIDA"),
    ("B5.B01", "QUALIDADE_VALOR_ORIGINAL", "DIVIDA_ID", "CONFIRMADA"),
    ("B5.B02", "VALOR_JA_PAGO", "DIVIDA_ID", Decimal("123.45")),
    ("B5.B04", "DATA_REFERENCIA_SALDO", "DIVIDA_ID", "DATA_DD_MM_AAAA"),
    ("B5.C04", "DATA_TERMINO_CONTRATUAL", "DIVIDA_ID", date(2026, 1, 15)),
    ("B5.C07A", "NOVO_USO", "DIVIDA_ID", Decimal("123.45")),
    ("B5.D02", "NATUREZA_TAXA", "DIVIDA_ID", "EFETIVA"),
    ("B5.G02", "JA_RENEGOCIADA", "DIVIDA_ID", "SIM"),
    ("B5.G03", "PORTABILIDADE_CONSULTADA", "DIVIDA_ID", "SIM"),
    ("B5.H02", "MOTIVO_PESO_EMOCIONAL", "DIVIDA_ID", frozenset({"JUROS_MUITO_ALTOS"})),
)

_MANTIDAS_QUE_OUTRAS_USAM: tuple[str, ...] = (
    "B3.S03",  # `origem_opcoes` de B5.A02V (vínculo da dívida consignada)
    "B5.I01",  # `nivel_comprovacao_se` de B5.I02 (comprovação da fonte)
    "B3.C02",  # pai de B3.C02A/B3.C02B, que o especialista quer ligar ao motor
    "B5.D03",  # substituída pela pergunta única de CET ou taxa (RF-407)
    "B5.D03A",  # idem
    "B4.04",  # o responsável do produto decidiu manter
)


def test_perguntas_removidas_nao_existem_e_as_mantidas_continuam() -> None:
    ids = {r.ID for r in carregar_registros().registros}

    assert len(_REMOVIDAS) == 87
    assert len({ID for ID, *_ in _REMOVIDAS}) == 87
    assert {ID for ID, *_ in _REMOVIDAS} & ids == set()
    assert set(_MANTIDAS_QUE_OUTRAS_USAM) <= ids


def _com(
    respostas: RespostasCaso, extras: tuple[tuple[str, str | None, ValorResposta], ...]
) -> RespostasCaso:
    novas = tuple(
        Resposta(
            CASO_ID=CASO_ID,
            ID_PERGUNTA=variavel,
            item_id=None if escopo is None else _ITEM_POR_ESCOPO[escopo],
            valor=valor,
            QUESTIONARIO_VERSION=QUESTIONARIO_VERSION,
            respondida_em=RESPONDIDA_EM,
        )
        for variavel, escopo, valor in extras
    )
    return RespostasCaso(respostas=(*respostas.respostas, *novas))


def _estado(respostas: RespostasCaso, dividas: tuple[str, ...]) -> EstadoFinanceiro:
    return montar_estado_financeiro(
        respostas,
        DATA_REFERENCIA=DATA_REFERENCIA,
        dividas=tuple(montar_divida(respostas, d) for d in dividas),
        **PARAMETROS_EXTERNOS_PADRAO,  # type: ignore[arg-type]
    )


def _snapshot(estado: EstadoFinanceiro) -> SnapshotOrdem:
    return calcular_plano(estado, FonteParametrosArquivo().carregar("1.0.1"))


_CASOS: dict[str, tuple[RespostasCaso, tuple[str, ...]]] = {
    "caso_completo": (caso_completo().respostas, (DIVIDA_ID_UNICA,)),
    "gab03_nao_sei": (caso_completo_com_divida_gab03().respostas, (DIVIDA_ID_UNICA,)),
    "perfil_t02_duas_dividas": (_respostas_t02(), ("D001", "D002")),
}


@pytest.mark.parametrize("caso", sorted(_CASOS))
def test_estado_e_snapshot_identicos_com_todas_as_respostas_removidas(caso: str) -> None:
    sem, dividas = _CASOS[caso]
    com = _com(sem, tuple((v, e, valor) for _, v, e, valor in _REMOVIDAS))

    estado_sem = _estado(sem, dividas)
    estado_com = _estado(com, dividas)

    assert estado_com == estado_sem
    assert _snapshot(estado_com) == _snapshot(estado_sem)


@pytest.mark.parametrize(("ID", "variavel", "escopo", "valor"), _REMOVIDAS)
def test_estado_identico_com_a_resposta_de_cada_pergunta_removida(
    ID: str, variavel: str, escopo: str | None, valor: ValorResposta
) -> None:
    sem, dividas = _CASOS["perfil_t02_duas_dividas"]

    assert _estado(_com(sem, ((variavel, escopo, valor),)), dividas) == _estado(sem, dividas)
