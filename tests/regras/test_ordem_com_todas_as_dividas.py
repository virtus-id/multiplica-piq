"""A ordem publicada traz todas as dívidas — `RF-512`, `AC-512`, `AC-513`, `EC-61` (`T-467`).

O caso é o do `aluno.teste3`: consignado, veículo, cheque especial e
financiamento imobiliário. O cheque especial e o financiamento não quitam em
10 anos (a parcela não cobre os juros), então a simulação não os quita; a
ordem publicada os traz depois das quitadas.
"""

from dataclasses import replace
from decimal import Decimal

from engine.estado import Divida, EstadoFinanceiro
from engine.motor import calcular_plano
from engine.precisao import dinheiro
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.fixtures.carregar import carregar_gab_a, carregar_gab_b, carregar_gab_c


def _divida(base: Divida, divida_id: str, saldo: str, taxa: str, parcela: str) -> Divida:
    return replace(
        base,
        DIVIDA_ID=divida_id,
        SALDO_DEVEDOR_ATUAL=dinheiro(saldo),
        TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal(taxa),
        PARCELA_CONTRATUAL=dinheiro(parcela),
        PAGAMENTO_MENSAL_EFETIVO=dinheiro(parcela),
    )


def _caso_teste3() -> EstadoFinanceiro:
    estado = carregar_gab_b()
    base = estado.dividas[0]
    return replace(
        estado,
        RENDA_TOTAL_RECORRENTE=dinheiro(estado.RENDA_TOTAL_RECORRENTE) + dinheiro("2000"),
        dividas=(
            _divida(base, "D001", "10000", "0.01877", "500"),
            _divida(base, "D002", "48000", "0.015", "1000"),
            _divida(base, "D003", "20000", "0.05", "500"),
            _divida(base, "D004", "200000", "0.00949", "1500"),
        ),
    )


def test_ac512_ordem_publicada_traz_as_quatro_dividas() -> None:
    parametros = FonteParametrosArquivo().carregar("1.0.1")
    snapshot = calcular_plano(_caso_teste3(), parametros)
    publicada = [p.DIVIDA_ID for p in snapshot.ORDEM_QUITACAO]
    cenario = snapshot.cenarios[snapshot.METODO_RECOMENDADO_PIQ]
    assert cenario.ESTOUROU_HORIZONTE is True
    assert sorted(publicada) == ["D001", "D002", "D003", "D004"]
    # as que a simulação quita vêm na frente, na mesma ordem de antes
    assert publicada[: len(cenario.ORDEM_QUITACAO)] == list(cenario.ORDEM_QUITACAO)
    assert set(publicada[len(cenario.ORDEM_QUITACAO) :]) == {"D003", "D004"}
    assert list(cenario.ORDEM_FORA_DO_HORIZONTE) == publicada[len(cenario.ORDEM_QUITACAO) :]
    assert [p.posicao for p in snapshot.ORDEM_QUITACAO] == [1, 2, 3, 4]


def test_ac513_gabaritos_que_quitam_tudo_nao_mudam() -> None:
    parametros = FonteParametrosArquivo().carregar("1.0.1")
    for carregar in (carregar_gab_a, carregar_gab_b, carregar_gab_c):
        snapshot = calcular_plano(carregar(), parametros)
        for cenario in snapshot.cenarios.values():
            if not cenario.ESTOUROU_HORIZONTE:
                assert cenario.ORDEM_FORA_DO_HORIZONTE == ()
        recomendado = snapshot.cenarios[snapshot.METODO_RECOMENDADO_PIQ]
        if not recomendado.ESTOUROU_HORIZONTE:
            assert [p.DIVIDA_ID for p in snapshot.ORDEM_QUITACAO] == list(
                recomendado.ORDEM_QUITACAO
            )
