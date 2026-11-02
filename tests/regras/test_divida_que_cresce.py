"""Dívida que cresce — `RF-79`, `AC-142`, `AC-143`, `AC-144`, `EC-59` (`T-460`).

Parte do `GAB-B` (renda − despesas = 2.000; uma dívida de parcela 1.800 sem
saldo nem taxa) e troca o inventário pelo do caso `aluno.teste3`: cheque
especial de saldo 20.000, taxa 5% a.m. e parcela 500, e financiamento de saldo
200.000, taxa 0,949% a.m. e parcela 1.500. Faltas de juros: 500 e 398.
"""

from dataclasses import replace
from decimal import Decimal

from engine.diagnostico import (
    calcular_diagnostico,
    calcular_faltas_de_juros,
    classificar_estabilizacao,
)
from engine.estado import Divida, EstadoFinanceiro
from engine.precisao import dinheiro
from engine.tipos import MOTIVO_ESTABILIZACAO
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.fixtures.carregar import carregar_gab_a, carregar_gab_b


def _divida(base: Divida, divida_id: str, saldo: str, taxa: str, parcela: str) -> Divida:
    return replace(
        base,
        DIVIDA_ID=divida_id,
        SALDO_DEVEDOR_ATUAL=dinheiro(saldo),
        TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal(taxa),
        PARCELA_CONTRATUAL=dinheiro(parcela),
        PAGAMENTO_MENSAL_EFETIVO=dinheiro(parcela),
    )


def _caso_teste3(renda_a_mais: str = "0") -> EstadoFinanceiro:
    estado = carregar_gab_b()
    base = estado.dividas[0]
    return replace(
        estado,
        RENDA_TOTAL_RECORRENTE=dinheiro(estado.RENDA_TOTAL_RECORRENTE) + dinheiro(renda_a_mais),
        dividas=(
            _divida(base, "D001", "20000", "0.05", "500"),
            _divida(base, "D002", "200000", "0.00949", "1500"),
        ),
    )


def test_ac142_faltas_de_juros_do_caso_teste3() -> None:
    faltas = calcular_faltas_de_juros(_caso_teste3())
    assert faltas.FALTA_TOTAL_DE_JUROS == dinheiro("898")
    assert [d.DIVIDA_ID for d in faltas.DIVIDAS_QUE_CRESCEM] == ["D001", "D002"]
    crescem = faltas.DIVIDAS_QUE_CRESCEM
    assert [d.JUROS_DO_MES for d in crescem] == [dinheiro("1000"), dinheiro("1898")]
    assert [d.FALTA_DE_JUROS for d in crescem] == [dinheiro("500"), dinheiro("398")]


def test_ac142_sobra_menor_que_as_faltas_entra_em_estabilizacao_por_divida_que_cresce() -> None:
    parametros = FonteParametrosArquivo().carregar("1.0.1")
    diagnostico = calcular_diagnostico(_caso_teste3(), parametros)
    assert diagnostico.RESULTADO_MENSAL_ATUAL == dinheiro("0")
    assert diagnostico.MODO_ESTABILIZACAO is True
    assert diagnostico.MOTIVO_ESTABILIZACAO is MOTIVO_ESTABILIZACAO.DIVIDA_QUE_CRESCE
    assert diagnostico.FALTA_TOTAL_DE_JUROS == dinheiro("898")
    assert [d.DIVIDA_ID for d in diagnostico.DIVIDAS_QUE_CRESCEM] == ["D001", "D002"]
    assert diagnostico.DEFICIT_MENSAL == dinheiro("0")


def test_ac143_sobra_que_cobre_as_faltas_nao_entra_em_estabilizacao() -> None:
    parametros = FonteParametrosArquivo().carregar("1.0.1")
    diagnostico = calcular_diagnostico(_caso_teste3("1000"), parametros)
    assert diagnostico.RESULTADO_MENSAL_ATUAL == dinheiro("1000")
    assert diagnostico.MODO_ESTABILIZACAO is False
    assert diagnostico.MOTIVO_ESTABILIZACAO is MOTIVO_ESTABILIZACAO.NENHUM
    assert [d.DIVIDA_ID for d in diagnostico.DIVIDAS_QUE_CRESCEM] == ["D001", "D002"]


def test_resultado_negativo_continua_sendo_deficit() -> None:
    parametros = FonteParametrosArquivo().carregar("1.0.1")
    diagnostico = calcular_diagnostico(carregar_gab_a(), parametros)
    assert diagnostico.MODO_ESTABILIZACAO is True
    assert diagnostico.MOTIVO_ESTABILIZACAO is MOTIVO_ESTABILIZACAO.DEFICIT


def test_ac144_gabarito_sem_saldo_ou_taxa_nao_tem_falta_de_juros() -> None:
    """EC-59: saldo/taxa desconhecidos deixam a dívida de fora (RF-16)."""
    parametros = FonteParametrosArquivo().carregar("1.0.1")
    diagnostico = calcular_diagnostico(carregar_gab_b(), parametros)
    assert diagnostico.FALTA_TOTAL_DE_JUROS == dinheiro("0")
    assert diagnostico.DIVIDAS_QUE_CRESCEM == ()
    assert diagnostico.MOTIVO_ESTABILIZACAO is MOTIVO_ESTABILIZACAO.NENHUM
    assert diagnostico.MODO_ESTABILIZACAO is False


def test_parcela_que_cobre_os_juros_nao_cresce() -> None:
    estado = carregar_gab_b()
    divida = _divida(estado.dividas[0], "D001", "20000", "0.05", "1000")
    faltas = calcular_faltas_de_juros(replace(estado, dividas=(divida,)))
    assert faltas.DIVIDAS_QUE_CRESCEM == ()
    assert classificar_estabilizacao(dinheiro("0"), faltas) == (
        False,
        MOTIVO_ESTABILIZACAO.NENHUM,
    )
