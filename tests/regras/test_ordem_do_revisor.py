"""Ordem de quitação definida pelo revisor — `RF-545` (`T-575`, `T-576`).

Estados pequenos fabricados sobre `GAB-C` (renda reduzida para o ataque durar
vários meses por dívida). Tolerância zero para ordem, prazo, método e status.

A "dívida da vez" de cada mês é `MesDoPlano.DIVIDA_ALVO`, o alvo ao fim do mês:
a primeira da lista ainda não quitada até aquele mês (`None` quando todas
acabaram).
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import replace
from decimal import Decimal

import pytest

from engine.estado import Divida, EstadoFinanceiro
from engine.motor import MOTIVO_AJUSTE_DA_ORDEM, ErroOrdemDoRevisor, calcular_plano
from engine.ordem import _DESCRICAO_CRITERIO
from engine.parametros import Parametros
from engine.precisao import dinheiro
from engine.prognostico import MesDoPlano
from engine.tipos import DESCONHECIDO
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.fixtures.carregar import carregar_gab_c
from tests.invariantes.test_gab04_estabilizacao import _estado_gab04


def _parametros() -> Parametros:
    return FonteParametrosArquivo().carregar("1.0.1")


def _estado(reducao_renda: str, *dividas: tuple[str, str, str, str]) -> EstadoFinanceiro:
    """`GAB-C` com a renda reduzida e as dívidas (id, saldo, taxa, parcela)."""
    estado = carregar_gab_c()
    base = estado.dividas[0]
    return replace(
        estado,
        RENDA_TOTAL_RECORRENTE=dinheiro(estado.RENDA_TOTAL_RECORRENTE) - dinheiro(reducao_renda),
        dividas=tuple(
            replace(
                base,
                DIVIDA_ID=divida_id,
                SALDO_DEVEDOR_ATUAL=dinheiro(saldo),
                VALOR_QUITACAO_HOJE=dinheiro(saldo),
                TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal(taxa),
                PARCELA_CONTRATUAL=dinheiro(parcela),
                PAGAMENTO_MENSAL_EFETIVO=dinheiro(parcela),
            )
            for divida_id, saldo, taxa, parcela in dividas
        ),
    )


def _estado_ac555() -> EstadoFinanceiro:
    """Sem estouro; Bola de Neve publica (`D001`, `D002`, `D003`) e cada dívida
    leva meses para quitar."""
    return _estado(
        "4800",
        ("D001", "2000", "0.02", "200"),
        ("D002", "4000", "0.03", "250"),
        ("D003", "6000", "0.04", "300"),
    )


_LISTA = ("D003", "D001", "D002")


def _primeira_nao_quitada(lista: Sequence[str], quitadas: Iterable[str]) -> str | None:
    return next((divida_id for divida_id in lista if divida_id not in set(quitadas)), None)


def _assertar_vez_segue_a_lista(meses: Sequence[MesDoPlano], lista: Sequence[str]) -> None:
    assert meses
    quitadas: set[str] = set()
    for mes in meses:
        quitadas |= set(mes.QUITACOES)
        assert mes.DIVIDA_ALVO == _primeira_nao_quitada(lista, quitadas), mes.MES


def test_ac555_divida_da_vez_e_a_primeira_da_lista_e_o_metodo_nao_muda() -> None:
    estado, parametros = _estado_ac555(), _parametros()
    sem = calcular_plano(estado, parametros)
    assert [p.DIVIDA_ID for p in sem.ORDEM_QUITACAO] == ["D001", "D002", "D003"]

    com = calcular_plano(estado, parametros, ordem_do_revisor=_LISTA)

    assert com.prognostico is not None
    _assertar_vez_segue_a_lista(com.prognostico.MESES_DO_PLANO, _LISTA)
    assert com.prognostico.MESES_DO_PLANO[0].DIVIDA_ALVO == "D003"
    cenario = com.cenarios[com.METODO_RECOMENDADO_PIQ]
    assert not cenario.ESTOUROU_HORIZONTE
    assert [p.DIVIDA_ID for p in com.ORDEM_QUITACAO] == list(cenario.ORDEM_QUITACAO)
    assert com.ORDEM_DO_REVISOR == _LISTA
    assert com.METODO_RECOMENDADO_PIQ is sem.METODO_RECOMENDADO_PIQ
    assert com.STATUS_METODO is sem.STATUS_METODO
    assert cenario.metodo is com.METODO_RECOMENDADO_PIQ


def test_ac556_com_estouro_a_ordem_publicada_e_a_de_ataque_e_a_lista() -> None:
    """Carteira própria: a dos testes de `T-467`/`T-469` está em
    `MODO_ESTABILIZACAO` e recusaria a lista (`EC-79`)."""
    estado = _estado(
        "3000",
        ("D001", "3000", "0.02", "200"),
        ("D002", "5000", "0.03", "250"),
        ("D003", "8000", "0.01", "200"),
        ("D004", "300000", "0.005", "1600"),
    )
    parametros = _parametros()
    sem = calcular_plano(estado, parametros)
    assert not sem.diagnostico.MODO_ESTABILIZACAO
    assert [p.DIVIDA_ID for p in sem.ORDEM_QUITACAO] == ["D001", "D002", "D003", "D004"]
    lista = ("D004", "D003", "D002", "D001")

    com = calcular_plano(estado, parametros, ordem_do_revisor=lista)

    cenario = com.cenarios[com.METODO_RECOMENDADO_PIQ]
    assert cenario.ESTOUROU_HORIZONTE
    assert tuple(p.DIVIDA_ID for p in com.ORDEM_QUITACAO) == lista
    assert cenario.ORDEM_DE_ATAQUE == lista
    assert cenario.meses[0].estado_final.DIVIDA_ALVO_ATUAL == "D004"
    assert cenario.ORDEM_FORA_DO_HORIZONTE == tuple(
        divida_id for divida_id in lista if divida_id not in cenario.ORDEM_QUITACAO
    )
    assert cenario.ORDEM_FORA_DO_HORIZONTE


def _estado_com_divida_bloqueada() -> EstadoFinanceiro:
    """`AC-555` mais `D004` sem saldo: Gate 1 (`INFORMACAO_PENDENTE`)."""
    estado = _estado_ac555()
    bloqueada: Divida = replace(
        estado.dividas[0], DIVIDA_ID="D004", SALDO_DEVEDOR_ATUAL=DESCONHECIDO
    )
    return replace(estado, dividas=(*estado.dividas, bloqueada))


@pytest.mark.parametrize(
    ("estado", "lista", "causa"),
    [
        pytest.param(_estado_ac555, ("D001", "D001", "D002", "D003"), "D001", id="a-repetida"),
        pytest.param(_estado_ac555, ("D001", "D002"), "D003", id="b-faltando"),
        pytest.param(_estado_ac555, ("D001", "D002", "D003", "D004"), "D004", id="c-inexistente"),
        pytest.param(
            _estado_com_divida_bloqueada,
            ("D001", "D002", "D003", "D004"),
            "D004",
            id="d-bloqueada-gate-1",
        ),
    ],
)
def test_ac557_lista_invalida_e_recusada_sem_snapshot(
    estado: Callable[[], EstadoFinanceiro], lista: tuple[str, ...], causa: str
) -> None:
    with pytest.raises(ErroOrdemDoRevisor, match=causa):
        calcular_plano(estado(), _parametros(), ordem_do_revisor=lista)


def test_ec79_em_estabilizacao_lista_nao_vazia_e_recusada_e_vazia_aceita() -> None:
    estado, parametros = _estado_gab04(), _parametros()
    sem = calcular_plano(estado, parametros)
    assert sem.diagnostico.MODO_ESTABILIZACAO
    lista = tuple(p.DIVIDA_ID for p in sem.ORDEM_QUITACAO)

    with pytest.raises(ErroOrdemDoRevisor, match="MODO_ESTABILIZACAO"):
        calcular_plano(estado, parametros, ordem_do_revisor=lista)
    assert calcular_plano(estado, parametros, ordem_do_revisor=()) == sem


def test_ac558_mesma_entrada_mesmo_snapshot() -> None:
    estado, parametros = _estado_ac555(), _parametros()
    anterior = calcular_plano(estado, parametros)

    primeiro = calcular_plano(estado, parametros, anterior, ordem_do_revisor=_LISTA)
    segundo = calcular_plano(estado, parametros, anterior, ordem_do_revisor=_LISTA)

    assert primeiro == segundo
    assert primeiro.hash_inputs == segundo.hash_inputs
    assert primeiro.SNAPSHOT_ID == segundo.SNAPSHOT_ID


def test_ac560_a_lista_entra_no_hash_e_no_snapshot_id() -> None:
    """A leitura do snapshot antigo (sem a chave) está em
    `tests/regras/test_repositorio_snapshots.py` (`T-568`)."""
    estado, parametros = _estado_ac555(), _parametros()
    sem = calcular_plano(estado, parametros)
    com = calcular_plano(estado, parametros, ordem_do_revisor=_LISTA)
    outra = calcular_plano(estado, parametros, ordem_do_revisor=("D002", "D003", "D001"))

    assert sem.ORDEM_DO_REVISOR is None
    assert len({sem.hash_inputs, com.hash_inputs, outra.hash_inputs}) == 3
    assert len({sem.SNAPSHOT_ID, com.SNAPSHOT_ID, outra.SNAPSHOT_ID}) == 3


def test_ac562_v2_encadeada_com_motivo_e_justificativa_do_revisor() -> None:
    estado, parametros = _estado_ac555(), _parametros()
    v1 = calcular_plano(estado, parametros)

    v2 = calcular_plano(estado, parametros, v1, ordem_do_revisor=_LISTA)

    assert v2.versao == 2
    assert v2.snapshot_anterior_id == v1.SNAPSHOT_ID
    assert v2.MOTIVO_RECALCULO == MOTIVO_AJUSTE_DA_ORDEM
    assert v2.EVENTO_RECALCULO is None
    assert v2.ORDEM_QUITACAO
    for posicao in v2.ORDEM_QUITACAO:
        texto = posicao.JUSTIFICATIVA_POSICAO
        assert texto
        assert "definida pelo revisor" in texto
        for criterio in _DESCRICAO_CRITERIO.values():
            assert criterio not in texto
        for regra in ("O-01", "O-04", "H-05"):
            assert regra not in texto


def test_ec78_divida_que_acaba_sozinha_antes_da_vez_e_pulada() -> None:
    """`D002` se quita só com as parcelas no mês 3, antes da sua vez; quando
    `D003` acaba, a vez passa direto a `D001`."""
    estado = _estado(
        "4800",
        ("D001", "4000", "0.02", "200"),
        ("D002", "900", "0.00", "300"),
        ("D003", "6000", "0.04", "300"),
    )
    lista = ("D003", "D002", "D001")

    com = calcular_plano(estado, _parametros(), ordem_do_revisor=lista)

    assert com.prognostico is not None
    meses = com.prognostico.MESES_DO_PLANO
    _assertar_vez_segue_a_lista(meses, lista)
    mes_d002 = next(m.MES for m in meses if "D002" in m.QUITACOES)
    mes_d003 = next(m.MES for m in meses if "D003" in m.QUITACOES)
    assert mes_d002 < mes_d003
    assert meses[mes_d003 - 1].DIVIDA_ALVO == "D001"
    assert tuple(p.DIVIDA_ID for p in com.ORDEM_QUITACAO) != lista
    assert com.ORDEM_DO_REVISOR == lista
