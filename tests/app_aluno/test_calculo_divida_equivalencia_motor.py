"""Prazo da calculadora = mês de quitação do motor — `T-484`.

Para uma dívida isolada, sem ataque extra, o prazo que a tela mostra é o que
`engine.motor.calcular_plano` projeta (`RF-517`, `RF-531`, `AC-526`). O teste
importa o motor; o módulo de produção, não (fronteira em
`estatica/test_fronteira_import_engine.py`).

REGRAS: `RF-517`, `RF-531`, `AC-526`
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.montagem.calculo_divida import calcular_parcela, calcular_prazo
from app.montagem.conversao import converter_para_dinheiro as d
from app.montagem.conversao import converter_para_taxa as t
from engine.estado import EstadoFinanceiro
from engine.motor import calcular_plano
from engine.precisao import dinheiro
from engine.tipos import SISTEMA_AMORTIZACAO, Dinheiro, Taxa
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.invariantes.test_gab01_seguro import _estado_com_seguro_embutido

PRICE = SISTEMA_AMORTIZACAO.PRICE
SAC = SISTEMA_AMORTIZACAO.SAC


def _prazo_do_motor(
    saldo: Dinheiro, parcela: Dinheiro, taxa: Taxa, sistema: SISTEMA_AMORTIZACAO
) -> int:
    base: EstadoFinanceiro = _estado_com_seguro_embutido()
    divida = replace(
        base.dividas[0],
        SALDO_DEVEDOR_ATUAL=saldo,
        VALOR_QUITACAO_HOJE=saldo,
        TAXA_EFETIVA_MENSAL_NORMALIZADA=taxa,
        CET=taxa,
        PARCELA_CONTRATUAL=parcela,
        PAGAMENTO_MENSAL_EFETIVO=parcela,
        SEGURO_INCLUIDO_PARCELA=False,
        CUSTO_SEGURO=dinheiro("0"),
        SISTEMA_AMORTIZACAO=sistema,
    )
    # Sem ataque: capacidade declarada zero, a dívida só recebe a parcela.
    estado = replace(base, dividas=(divida,), CAPACIDADE_ATAQUE_DECLARADA=dinheiro("0"))
    snapshot = calcular_plano(estado, FonteParametrosArquivo().carregar("1.0.1"))
    prazos = {int(cenario.PRAZO_TOTAL) for cenario in snapshot.cenarios.values()}
    assert len(prazos) == 1
    return prazos.pop()


def test_ac526_price_528_72_quita_em_24_nao_em_25() -> None:
    saldo, taxa = d("10000"), t("2")
    assert _prazo_do_motor(saldo, d("528,72"), taxa, PRICE) == 24
    assert calcular_prazo(saldo, d("528,72"), taxa, PRICE) == 24


@pytest.mark.parametrize("sistema", [PRICE, SAC])
@pytest.mark.parametrize(
    ("saldo", "taxa", "prazo"),
    [
        ("10000", "2", 24),
        ("5000", "0", 10),
        ("3500,50", "4,5", 18),
        ("20000", "1", 12),
        ("800", "8", 1),
        ("15000", "1,75", 60),
        ("45000", "0,9", 120),
    ],
)
def test_prazo_da_calculadora_e_o_do_motor(
    sistema: SISTEMA_AMORTIZACAO, saldo: str, taxa: str, prazo: int
) -> None:
    s, i = d(saldo), t(taxa)
    parcela = calcular_parcela(s, i, prazo, sistema)
    assert calcular_prazo(s, parcela, i, sistema) == prazo
    assert _prazo_do_motor(s, parcela, i, sistema) == prazo


@pytest.mark.parametrize("parcela", ["600", "450", "1000"])
def test_prazo_fracionario_sobe_e_o_motor_concorda(parcela: str) -> None:
    s, i, p = d("10000"), t("2"), d(parcela)
    assert calcular_prazo(s, p, i, PRICE) == _prazo_do_motor(s, p, i, PRICE)
