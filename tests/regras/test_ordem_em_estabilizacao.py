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
from dataclasses import replace
from decimal import Decimal

from engine.estado import Divida, EstadoFinanceiro
from engine.motor import calcular_plano
from engine.parametros import Parametros
from engine.precisao import dinheiro
from engine.snapshot import SnapshotOrdem, _serializar_canonico
from engine.tipos import METODO
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.fixtures.carregar import carregar_gab_c


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
