"""Ordem em estabilização — `RF-552`, `RF-553`, `RF-554` (`T-604`, `T-616`–`T-620`).

O caso de teste do aluno `rodrigo@teste.com` (cabeçalho da Rodada 8 da spec):
renda 13.701,27, saídas 24.058,11, D001 financiamento 120.000 a 1,58% a.m.,
D002 consignado 100.000 a 2% a.m. com `PREFERENCIA_QUITACAO`. Tolerância zero
para ordem, motivo, mês, método e status.

O digest da simulação (`_DIGEST_SIMULACAO_RODRIGO`) foi lido da execução de
`calcular_plano` na branch anterior à `T-606`, não escrito à mão: a correção
não pode mudar a simulação, o método nem o status (`RF-552` item 3).
"""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal

from engine.ciclo_mensal import Cenario, EstadoSimulacao, SelecionarAlvo, simular_cenario
from engine.diagnostico import Diagnostico
from engine.estado import Divida, EstadoFinanceiro
from engine.metodos.avalanche import beneficio_de_ranqueamento, criar_selecionar_alvo_avalanche
from engine.metodos.bola_de_neve import criar_selecionar_alvo_bola_de_neve
from engine.motor import calcular_plano
from engine.parametros import Parametros
from engine.precisao import dinheiro
from engine.prioridade_ordem import aplicar_prioridade_ordem
from engine.snapshot import SnapshotOrdem, _serializar_canonico
from engine.tipos import METODO, MOTIVO_POSICAO, Dinheiro, SimNaoTalvez
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.fixtures.carregar import carregar_gab_c
from tests.regras.test_ordem_em_estabilizacao_identidade import _CONGELADOS, digest_do_snapshot


def _parametros() -> Parametros:
    return FonteParametrosArquivo().carregar("1.0.1")


def _divida(
    base: Divida, divida_id: str, saldo: str, taxa: str, parcela: str, **campos: object
) -> Divida:
    return replace(
        base,
        **campos,  # type: ignore[arg-type]
        DIVIDA_ID=divida_id,
        SALDO_DEVEDOR_ATUAL=dinheiro(saldo),
        VALOR_QUITACAO_HOJE=dinheiro(saldo),
        TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal(taxa),
        PARCELA_CONTRATUAL=dinheiro(parcela),
        PAGAMENTO_MENSAL_EFETIVO=dinheiro(parcela),
    )


def _estado_rodrigo() -> EstadoFinanceiro:
    """`GAB-C` com a renda, as despesas e as duas dívidas do caso: saídas =
    parcelas 2.256 + 5.287,11 + despesas 16.515 (16.015 operacionais + 500
    não mensais) = 24.058,11. As duas sem garantia e sem negativação (as do
    `GAB-C`)."""
    estado = carregar_gab_c()
    base = estado.dividas[0]
    return replace(
        estado,
        RENDA_TOTAL_RECORRENTE=dinheiro("13701.27"),
        DESPESAS_OPERACIONAIS_ATUAIS=dinheiro("16015"),
        DESPESAS_NAO_MENSAIS_NORMALIZADAS=dinheiro("500"),
        dividas=(
            _divida(base, "D001", "120000", "0.0158", "2256"),
            _divida(base, "D002", "100000", "0.02", "5287.11", PREFERENCIA_QUITACAO=True),
        ),
    )


def digest_da_simulacao(snapshot: SnapshotOrdem) -> str:
    """SHA-256 do que `RF-552` item 3 não deixa mudar: método, status,
    diagnóstico, prazo, custo e mês a mês de cada cenário e `MESES_DO_PLANO`."""
    assert snapshot.prognostico is not None
    congelado = {
        "METODO_RECOMENDADO_PIQ": snapshot.METODO_RECOMENDADO_PIQ,
        "STATUS_METODO": snapshot.STATUS_METODO,
        "ORDEM_STATUS": snapshot.ORDEM_STATUS,
        "diagnostico": snapshot.diagnostico,
        "cenarios": {
            metodo: {
                "PRAZO_TOTAL": cenario.PRAZO_TOTAL,
                "CUSTO_FUTURO_TOTAL": cenario.CUSTO_FUTURO_TOTAL,
                "meses": cenario.meses,
            }
            for metodo, cenario in snapshot.cenarios.items()
        },
        "MESES_DO_PLANO": snapshot.prognostico.MESES_DO_PLANO,
    }
    texto = json.dumps(_serializar_canonico(congelado), sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


# Lido antes de RF-552 (T-604).
_DIGEST_SIMULACAO_RODRIGO = "0c12c808516ac64a1c878e1d1bc4276598c8faa424acccd5c5310fbeed7ffe53"


def test_cabecalho_da_rodada_8_o_caso_do_rodrigo() -> None:
    snapshot = calcular_plano(_estado_rodrigo(), _parametros())
    diagnostico = snapshot.diagnostico
    assert diagnostico.MODO_ESTABILIZACAO
    assert diagnostico.RESULTADO_MENSAL_ATUAL == dinheiro("-10356.84")
    assert diagnostico.CAPACIDADE_ATAQUE_CONSERVADORA == dinheiro("-10356.84")
    # 13.701,27 × 3% (P_PISO_CAPACIDADE_PERCENTUAL), exato; 411,04 na exibição
    assert diagnostico.PISO_CAPACIDADE == Decimal("411.0381")
    assert snapshot.METODO_RECOMENDADO_PIQ is METODO.AVALANCHE
    assert snapshot.cenarios[METODO.AVALANCHE].ESTOUROU_HORIZONTE


def test_ac576_simulacao_metodo_e_status_sao_os_de_antes() -> None:
    snapshot = calcular_plano(_estado_rodrigo(), _parametros())
    assert digest_da_simulacao(snapshot) == _DIGEST_SIMULACAO_RODRIGO


# --- T-616: AC-576, AC-585, EC-90 --------------------------------------------


def test_ac576_ordem_completa_com_o_motivo_de_cada_posicao() -> None:
    snapshot = calcular_plano(_estado_rodrigo(), _parametros())
    cenario = snapshot.cenarios[METODO.AVALANCHE]

    assert cenario.ORDEM_DE_ATAQUE == ("D001", "D002")
    assert [(p.posicao, p.DIVIDA_ID, p.MOTIVO_POSICAO) for p in snapshot.ORDEM_QUITACAO] == [
        (1, "D001", MOTIVO_POSICAO.MAIOR_BENEFICIO_MARGINAL),
        # a preferência de D002 não decidiu: 1,58% e 2% a.m. diferem mais de 5%
        (2, "D002", MOTIVO_POSICAO.ULTIMA_RESTANTE),
    ]
    assert cenario.ORDEM_FORA_DO_HORIZONTE == tuple(
        divida_id
        for divida_id in cenario.ORDEM_DE_ATAQUE
        if divida_id not in cenario.ORDEM_QUITACAO
    )
    assert cenario.ORDEM_FORA_DO_HORIZONTE == ("D001",)
    assert digest_da_simulacao(snapshot) == _DIGEST_SIMULACAO_RODRIGO


def test_ac585_previsao_so_com_as_parcelas_no_caso_do_rodrigo() -> None:
    snapshot = calcular_plano(_estado_rodrigo(), _parametros())
    assert snapshot.prognostico is not None
    so_parcelas = snapshot.prognostico.sem_acao.QUITACOES_SO_PARCELAS
    assert so_parcelas is not None
    # D002: 24 parcelas. D001 (Price): −ln(1 − 0,0158 × 120.000 / 2.256) ÷ ln(1,0158)
    # ≈ 117,07 → quita no mês 118, dentro dos 120 de P_HORIZONTE_MAXIMO_SIMULACAO.
    assert ("D002", 24) in so_parcelas
    assert ("D001", 118) in so_parcelas


def test_ac585_plano_que_termina_antes_nao_corta_a_previsao() -> None:
    """`GAB-C`: o plano acaba no mês 6; só com as parcelas (Price) D003 termina
    no mês 10, D002 no 17 e D001 no 30 — nenhuma delas em `sem_acao.QUITACOES`."""
    snapshot = calcular_plano(carregar_gab_c(), _parametros())
    assert snapshot.prognostico is not None
    sem_acao = snapshot.prognostico.sem_acao
    assert sem_acao.HORIZONTE_MESES == 6
    assert sem_acao.QUITACOES == ()
    assert sem_acao.QUITACOES_SO_PARCELAS == (("D003", 10), ("D002", 17), ("D001", 30))
    # Os demais campos de sem_acao: os do digest congelado antes da mudança (T-603).
    assert digest_do_snapshot(snapshot) == dict((n, d) for n, _, d in _CONGELADOS)["GAB-C"]


def test_ec90_parcela_que_nao_cobre_os_juros_ou_pagamento_zero_fica_de_fora() -> None:
    estado = _estado_rodrigo()
    base = estado.dividas[0]
    cresce = _divida(base, "D003", "10000", "0.05", "100")  # juros 500 > parcela 100
    sem_pagamento = replace(
        _divida(base, "D004", "5000", "0.01", "200"), PAGAMENTO_MENSAL_EFETIVO=dinheiro(0)
    )
    snapshot = calcular_plano(
        replace(estado, dividas=(*estado.dividas, cresce, sem_pagamento)), _parametros()
    )
    assert snapshot.prognostico is not None
    so_parcelas = snapshot.prognostico.sem_acao.QUITACOES_SO_PARCELAS
    assert so_parcelas is not None
    assert dict(so_parcelas) == {"D002": 24, "D001": 118}


# --- T-617: AC-578, AC-579, AC-580, EC-87 ------------------------------------


def _variacao(
    renda: str, *dividas: tuple[str, str, str, str], **campos: object
) -> EstadoFinanceiro:
    """`_estado_rodrigo()` com a renda e a carteira (id, saldo, taxa, parcela)
    trocadas; despesas de 16.515 mantidas."""
    estado = _estado_rodrigo()
    base = estado.dividas[0]
    return replace(
        estado,
        **campos,  # type: ignore[arg-type]
        RENDA_TOTAL_RECORRENTE=dinheiro(renda),
        dividas=tuple(_divida(base, *divida) for divida in dividas),
    )


def _inventario(estado: EstadoFinanceiro) -> dict[str, Divida]:
    return {divida.DIVIDA_ID: divida for divida in estado.dividas}


def _ordem_pelo_seletor(
    sel: SelecionarAlvo, dividas: Mapping[str, Divida], delta: Dinheiro
) -> tuple[str, ...]:
    """Oráculo: o seletor escolhendo do estado inicial, uma dívida por vez, com
    o mesmo delta, até não haver candidata."""
    estado = EstadoSimulacao(
        mes=0,
        saldos={},
        quitadas=frozenset(),
        DIVIDA_ALVO_ATUAL=None,
        CAPACIDADE_ATAQUE_M=delta,
        ATAQUE_NAO_UTILIZADO_ACUMULADO=dinheiro(0),
        DESEMBOLSO_ACUMULADO=dinheiro(0),
    )
    ordem: list[str] = []
    while estado.quitadas != frozenset(dividas):
        escolhida = sel(estado, delta)
        if escolhida is None:
            break
        ordem.append(escolhida.DIVIDA_ID)
        estado = replace(estado, quitadas=estado.quitadas | {escolhida.DIVIDA_ID})
    return tuple(ordem)


_TRES_DIVIDAS: tuple[tuple[str, str, str, str], ...] = (
    ("D001", "3000", "0.02", "300"),
    ("D002", "5000", "0.03", "400"),
    ("D003", "8000", "0.04", "500"),
)


def test_ac578_ec87_bola_de_neve_em_estabilizacao_da_menor_para_a_maior() -> None:
    estado = _variacao("13701.27", *_TRES_DIVIDAS)
    parametros = _parametros()
    snapshot = calcular_plano(estado, parametros)
    diagnostico = snapshot.diagnostico
    assert diagnostico.MODO_ESTABILIZACAO
    assert snapshot.METODO_RECOMENDADO_PIQ is METODO.BOLA_DE_NEVE

    cenario = snapshot.cenarios[METODO.BOLA_DE_NEVE]
    assert cenario.ORDEM_DE_ATAQUE == ("D001", "D002", "D003")
    assert [(p.DIVIDA_ID, p.MOTIVO_POSICAO) for p in snapshot.ORDEM_QUITACAO] == [
        ("D001", MOTIVO_POSICAO.MENOR_VALOR_RELEVANTE),
        ("D002", MOTIVO_POSICAO.MENOR_VALOR_RELEVANTE),
        ("D003", MOTIVO_POSICAO.ULTIMA_RESTANTE),
    ]
    # EC-87: a Bola de Neve não usa o delta — a sequência com a capacidade
    # negativa (antes de RF-552) é a mesma com o piso.
    dividas = _inventario(estado)
    sel = criar_selecionar_alvo_bola_de_neve(dividas, parametros)
    assert (
        _ordem_pelo_seletor(sel, dividas, diagnostico.CAPACIDADE_ATAQUE_CONSERVADORA)
        == _ordem_pelo_seletor(sel, dividas, diagnostico.PISO_CAPACIDADE)
        == cenario.ORDEM_DE_ATAQUE
    )


def test_ac579_deficit_sem_estouro_publica_a_ordem_de_ataque_com_motivo() -> None:
    snapshot = calcular_plano(_variacao("17000", *_TRES_DIVIDAS), _parametros())
    diagnostico = snapshot.diagnostico
    assert diagnostico.MODO_ESTABILIZACAO
    assert diagnostico.CAPACIDADE_ATAQUE_CONSERVADORA < 0

    cenario = snapshot.cenarios[snapshot.METODO_RECOMENDADO_PIQ]
    assert not cenario.ESTOUROU_HORIZONTE
    assert cenario.ORDEM_DE_ATAQUE == ("D003", "D002", "D001")
    # a ordem de ataque, não a ordem em que a simulação terminou as dívidas
    assert cenario.ORDEM_QUITACAO == ("D001", "D002", "D003")
    assert tuple(p.DIVIDA_ID for p in snapshot.ORDEM_QUITACAO) == cenario.ORDEM_DE_ATAQUE
    assert all(p.MOTIVO_POSICAO is not None for p in snapshot.ORDEM_QUITACAO)


def _estado_ac580() -> EstadoFinanceiro:
    """Fora de estabilização (resultado +735), `CAPACIDADE_ATAQUE_DECLARADA = 0`,
    sinais neutros (Avalanche recomendada). D001 e D002 quitam sozinhas
    (benefício por simulação); D003 não cobre a dívida no horizonte e estoura."""
    sinais = replace(
        _estado_rodrigo().sinais_comportamentais,
        NECESSIDADE_VITORIA=0,
        HISTORICO_ABANDONO=SimNaoTalvez.NAO,
    )
    return _variacao(
        "28000",
        ("D001", "3000", "0.02", "300"),
        ("D002", "5000", "0.03", "400"),
        ("D003", "1000000", "0.01", "10050"),
        CAPACIDADE_ATAQUE_DECLARADA=dinheiro("0"),
        sinais_comportamentais=sinais,
    )


def test_ac580_capacidade_zero_fora_de_estabilizacao_ranqueia_com_o_piso() -> None:
    estado, parametros = _estado_ac580(), _parametros()
    snapshot = calcular_plano(estado, parametros)
    diagnostico = snapshot.diagnostico
    assert not diagnostico.MODO_ESTABILIZACAO
    assert diagnostico.RESULTADO_MENSAL_ATUAL > 0
    assert diagnostico.CAPACIDADE_ATAQUE_CONSERVADORA == 0
    assert snapshot.METODO_RECOMENDADO_PIQ is METODO.AVALANCHE
    cenario = snapshot.cenarios[METODO.AVALANCHE]
    assert cenario.ESTOUROU_HORIZONTE

    dividas = _inventario(estado)
    sel = aplicar_prioridade_ordem(
        criar_selecionar_alvo_avalanche(dividas, parametros), dividas, parametros
    )
    assert cenario.ORDEM_DE_ATAQUE == ("D002", "D001", "D003")
    assert cenario.ORDEM_DE_ATAQUE == _ordem_pelo_seletor(sel, dividas, diagnostico.PISO_CAPACIDADE)
    # com a capacidade (zero) como delta, D001 e D002 não teriam benefício
    for divida_id in ("D001", "D002"):
        divida = dividas[divida_id]
        assert beneficio_de_ranqueamento(divida, dinheiro(0), parametros) is None
        com_o_piso = beneficio_de_ranqueamento(divida, diagnostico.PISO_CAPACIDADE, parametros)
        assert com_o_piso is not None and com_o_piso.origem == "SIMULACAO"

    # a simulação não lê o piso: com outro piso, só a ordem de ataque muda
    def sem_a_ordem(dg: Diagnostico) -> Cenario:
        simulado = simular_cenario(estado, dg, dividas, sel, parametros)
        return replace(simulado, ORDEM_DE_ATAQUE=(), ORDEM_FORA_DO_HORIZONTE=())

    outro_piso = replace(diagnostico, PISO_CAPACIDADE=dinheiro("1"))
    assert sem_a_ordem(diagnostico) == sem_a_ordem(outro_piso)
    assert replace(cenario, metodo=None, ORDEM_DE_ATAQUE=(), ORDEM_FORA_DO_HORIZONTE=()) == (
        sem_a_ordem(diagnostico)
    )
