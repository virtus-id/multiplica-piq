"""Costura da calculadora com o motor — `T-498` a `T-501`.

`montar_divida` lê de `resolver_divida` (valor informado ou calculado), a dívida
pendente fica fora do estado do motor e o Bloco 6 recusa quando todas estão
pendentes. `engine/` não muda (hashes de `estatica/test_engine_congelado.py`).

REGRAS: `RF-479`, `RF-517`, `RF-523`, `RF-527`, `RF-531`, `AC-542`, `AC-539`, `EC-74`
"""

from __future__ import annotations

import dataclasses
import time
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.casos.maquina import ESTADO_CASO
from app.montagem.calculo_divida import CAMPO_DA_DIVIDA, calcular_saldo
from app.montagem.conversao import converter_para_dinheiro as d
from app.montagem.conversao import converter_para_taxa as t
from app.montagem.estado import montar_divida, montar_estado_financeiro
from app.montagem.premissas import dividas_pendentes, resolver_divida
from app.revisao.comprovacao import pendencias_de_homologacao
from collection.carga import carregar_registros
from collection.registro import EscopoRepeticao
from collection.respostas import NAO_SEI, RespostasCaso
from engine.estado import Divida
from engine.snapshot import SnapshotOrdem
from engine.taxa import derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA
from engine.tipos import ORDEM_STATUS, SISTEMA_AMORTIZACAO
from persistencia.app_aluno.itens import ItemRepetido
from tests.app_aluno.fixtures.caso_completo import (
    CASO_ID,
    DATA_REFERENCIA,
    DESPESA_NAO_MENSAL_ID_UNICA,
    ITEM_DESPESA_ID_UNICA,
    PARAMETROS_EXTERNOS_PADRAO,
    montar_respostas_caso,
)
from tests.app_aluno.test_plano_ponta_a_ponta import _T02_CASO, _T02_D001, _T02_D002
from tests.app_aluno.test_rotas_calculo import (
    _caso_fabricado,
    _montar_aplicacao_de_teste,
    _RepositorioCasosDublê,
)

_PARCELA = "PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)"
_SEM_VALOR: dict[str, object] = {"SALDO_DEVEDOR_ATUAL": NAO_SEI, _PARCELA: NAO_SEI}
_ITEM_PENDENTE = "D003"


def _ficha(item: str, valores: dict[str, object]) -> RespostasCaso:
    todas = montar_respostas_caso(valores_divida=valores, DIVIDA_ID=item).respostas
    return RespostasCaso(respostas=tuple(r for r in todas if r.item_id == item))


def _itens(dividas: tuple[str, ...]) -> tuple[ItemRepetido, ...]:
    escopos = [(x, EscopoRepeticao.DIVIDA_ID) for x in dividas] + [
        (ITEM_DESPESA_ID_UNICA, EscopoRepeticao.ITEM_DESPESA),
        (DESPESA_NAO_MENSAL_ID_UNICA, EscopoRepeticao.DESPESA_NAO_MENSAL_ID),
    ]
    return tuple(
        ItemRepetido(
            item_id=i,
            CASO_ID=CASO_ID,
            escopo=e,
            removido_em=None,
            criado_em=datetime(2026, 1, 1, tzinfo=UTC),
        )
        for i, e in escopos
    )


def _por_escopo(itens: tuple[ItemRepetido, ...]) -> dict[EscopoRepeticao, tuple[str, ...]]:
    agrupado: dict[EscopoRepeticao, tuple[str, ...]] = {}
    for item in itens:
        agrupado[item.escopo] = (*agrupado.get(item.escopo, ()), item.item_id)
    return agrupado


def _caso(fichas: dict[str, dict[str, object]]) -> RespostasCaso:
    """Caso completo (perfil T02) com as fichas dadas; `fichas[item]` sobrescreve a base."""
    primeiro, *_ = fichas
    caso = dict(_T02_CASO) | {"QUANTIDADE_DIVIDAS_DECLARADA_INICIAL": len(fichas)}
    base = montar_respostas_caso(
        valores_caso=caso,
        valores_divida=fichas[primeiro],
        valores_item_despesa={"VALOR_DESPESA": d("3.500,00")},
        valores_despesa_nao_mensal={"VALOR_DESPESA_NAO_MENSAL": d("1.200,00")},
        DIVIDA_ID=primeiro,
    ).respostas
    outras = tuple(r for item in list(fichas)[1:] for r in _ficha(item, fichas[item]).respostas)
    return RespostasCaso(respostas=base + outras)


# --- T-498: montar_divida lê de resolver_divida ---------------------------------------


def test_ac542_valor_calculado_chega_ao_motor_e_prazo_nao() -> None:
    """Saldo desconhecido, com parcela, taxa e prazo: o saldo calculado vai ao motor."""
    informado = {
        "TIPO_DIVIDA": "PESSOAL",
        "SALDO_DEVEDOR_ATUAL": NAO_SEI,
        _PARCELA: d("528,72"),
        "TAXA_DIVIDA": t("2"),
        "PERIODICIDADE_TAXA_DIVIDA": "MENSAL",
        "PRAZO_RESTANTE_MESES": 24,
    }
    respostas = _ficha("D001", informado)

    divida = montar_divida(respostas, "D001")

    esperado = calcular_saldo(
        d("528,72"),
        derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(t("2"), "MENSAL"),
        24,
        SISTEMA_AMORTIZACAO.PRICE,
    )
    assert divida.SALDO_DEVEDOR_ATUAL == esperado
    assert (
        divida.SALDO_DEVEDOR_ATUAL
        == resolver_divida(respostas, "D001").valores[CAMPO_DA_DIVIDA.SALDO].valor
    )
    assert divida.PARCELA_CONTRATUAL == divida.PAGAMENTO_MENSAL_EFETIVO == d("528,72")
    assert not any("PRAZO" in campo.name for campo in dataclasses.fields(Divida))


def test_ac542_parcela_calculada_vai_nos_dois_campos_de_pagamento() -> None:
    informado: dict[str, object] = {
        "SALDO_DEVEDOR_ATUAL": d("10.000,00"),
        _PARCELA: NAO_SEI,
        "TAXA_DIVIDA": t("2"),
        "PERIODICIDADE_TAXA_DIVIDA": "MENSAL",
        "PRAZO_RESTANTE_MESES": 24,
    }
    respostas = _ficha("D001", informado)

    divida = montar_divida(respostas, "D001")

    assert divida.PARCELA_CONTRATUAL == divida.PAGAMENTO_MENSAL_EFETIVO
    assert divida.PARCELA_CONTRATUAL == d("528,72")  # AC-526


def test_ac542_so_respostas_antigas_monta_como_antes() -> None:
    respostas = _ficha("D001", {})

    divida = montar_divida(respostas, "D001")

    assert divida.SALDO_DEVEDOR_ATUAL == d("5.000,00")
    assert divida.PARCELA_CONTRATUAL == divida.PAGAMENTO_MENSAL_EFETIVO == d("300,00")
    assert divida.TAXA_EFETIVA_MENSAL_NORMALIZADA == derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(
        t("2"), "MENSAL"
    )
    assert divida.SISTEMA_AMORTIZACAO is SISTEMA_AMORTIZACAO.PRICE


@pytest.mark.parametrize("tipo", ["CARTAO_ROTATIVO", "PESSOAL", "CONSIGNADO", "FIN_IMOBILIARIO"])
def test_rf523_sac_chega_ao_motor_em_qualquer_modalidade(tipo: str) -> None:
    respostas = _ficha("D001", {"TIPO_DIVIDA": tipo, "SISTEMA_AMORTIZACAO": "SAC"})

    assert montar_divida(respostas, "D001").SISTEMA_AMORTIZACAO is SISTEMA_AMORTIZACAO.SAC


def test_ac428_parcela_maior_que_o_saldo_segue_aviso_sem_bloqueio() -> None:
    from app.montagem.entrada import avisos_da_gravacao

    respostas = _ficha("D001", {"SALDO_DEVEDOR_ATUAL": d("200,00"), _PARCELA: d("300,00")})

    divida = montar_divida(respostas, "D001")  # não recusa
    avisos = avisos_da_gravacao(_PARCELA, "D001", respostas)

    assert divida.PAGAMENTO_MENSAL_EFETIVO == d("300,00")
    assert [a.codigo for a in avisos] == ["PARCELA_MAIOR_QUE_O_SALDO"]


# --- T-499 / T-501: dívida pendente fora do estado -----------------------------------


def _tres_dividas() -> RespostasCaso:
    return _caso(
        {"D001": dict(_T02_D001), "D002": dict(_T02_D002), _ITEM_PENDENTE: dict(_SEM_VALOR)}
    )


def test_ac539_pendente_sai_do_estado_e_inventario_fica_incompleto() -> None:
    respostas = _tres_dividas()
    itens = _por_escopo(_itens(("D001", "D002", _ITEM_PENDENTE)))
    pendentes = dividas_pendentes(respostas, itens)
    assert [p.DIVIDA_ID for p in pendentes] == [_ITEM_PENDENTE]

    estado = montar_estado_financeiro(
        respostas,
        DATA_REFERENCIA=DATA_REFERENCIA,
        dividas=tuple(montar_divida(respostas, x) for x in ("D001", "D002")),
        dividas_pendentes=pendentes,
        **PARAMETROS_EXTERNOS_PADRAO,  # type: ignore[arg-type]
    )

    assert [x.DIVIDA_ID for x in estado.dividas] == ["D001", "D002"]
    assert estado.INVENTARIO_COMPLETO is False


def test_inventario_continua_completo_sem_pendente() -> None:
    respostas = _caso({"D001": dict(_T02_D001)})

    estado = montar_estado_financeiro(
        respostas,
        DATA_REFERENCIA=DATA_REFERENCIA,
        dividas=(montar_divida(respostas, "D001"),),
        dividas_pendentes=(),
        **PARAMETROS_EXTERNOS_PADRAO,  # type: ignore[arg-type]
    )

    assert estado.INVENTARIO_COMPLETO is True


def _disparar(
    monkeypatch: pytest.MonkeyPatch, respostas: RespostasCaso, dividas: tuple[str, ...]
) -> tuple[int, dict[str, object], ESTADO_CASO, list[SnapshotOrdem]]:
    repositorio = _RepositorioCasosDublê(
        _caso_fabricado(ESTADO_CASO.COLETA_INICIAL, caso_id=CASO_ID), conta_id_da_sessao="CONTA-1"
    )
    cliente, snapshots = _montar_aplicacao_de_teste(
        monkeypatch,
        repositorio_casos=repositorio,
        colecao=carregar_registros(),
        respostas=respostas.respostas,
        itens=_itens(dividas),
    )
    with cliente:
        resposta = cliente.post(f"/caso/{CASO_ID}/calculo")
        if resposta.status_code == 200:
            prazo = time.monotonic() + 30
            while time.monotonic() < prazo:
                caso = repositorio.buscar(CASO_ID)
                assert caso is not None
                if caso.estado is not ESTADO_CASO.CALCULANDO:
                    break
                time.sleep(0.05)
    caso = repositorio.buscar(CASO_ID)
    assert caso is not None
    return resposta.status_code, resposta.json(), caso.estado, snapshots.snapshots


def test_ac539_bloco_6_com_uma_pendente_gera_plano_provisorio_sem_a_pendente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status, corpo, _, snapshots = _disparar(
        monkeypatch, _tres_dividas(), ("D001", "D002", _ITEM_PENDENTE)
    )

    assert status == 200, corpo
    (snapshot,) = snapshots
    assert snapshot.ORDEM_STATUS is ORDEM_STATUS.PROVISORIA
    assert snapshot.estado_inputs.INVENTARIO_COMPLETO is False
    assert _ITEM_PENDENTE not in {p.DIVIDA_ID for p in snapshot.ORDEM_QUITACAO}
    assert _ITEM_PENDENTE not in {x.DIVIDA_ID for x in snapshot.estado_inputs.dividas}


def test_ec74_todas_pendentes_recusa_com_422_e_nao_chama_o_motor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chamadas: list[object] = []
    monkeypatch.setattr("app.motor.executor.calcular_plano", lambda *a, **k: chamadas.append(a))
    respostas = _caso({"D001": dict(_SEM_VALOR) | {"TAXA_DIVIDA": NAO_SEI}})

    status, corpo, estado, snapshots = _disparar(monkeypatch, respostas, ("D001",))

    assert status == 422
    assert corpo["mensagem"] == "Não há dívida com dados suficientes para montar o plano."
    pendencias = corpo["pendencias"]
    assert isinstance(pendencias, list) and pendencias
    assert {p["item_id"] for p in pendencias} == {"D001"}
    assert {p["ID"] for p in pendencias} == {"B5.B03", "B5.C02", "B5.D06"}
    assert chamadas == [] and snapshots == []
    assert estado is ESTADO_CASO.COLETA_INICIAL


# --- T-500: resolvidas em pendencias_de_homologacao -----------------------------------


def test_ac538_nao_sei_em_campo_calculado_nao_e_ausente_e_em_pendente_e() -> None:
    from app.montagem.premissas import campos_dispensados

    registros = carregar_registros().registros
    calculada = _ficha(
        "D001",
        {
            "SALDO_DEVEDOR_ATUAL": NAO_SEI,
            "PRAZO_RESTANTE_MESES": 24,
        },
    )
    itens = {EscopoRepeticao.DIVIDA_ID: ("D001",)}
    resolvidas = campos_dispensados(calculada, itens)
    assert ("D001", "SALDO_DEVEDOR_ATUAL") in resolvidas

    sem = [
        (p.item_id, p.ID_PERGUNTA) for p in pendencias_de_homologacao(registros, calculada, itens)
    ]
    com = [
        (p.item_id, p.ID_PERGUNTA)
        for p in pendencias_de_homologacao(registros, calculada, itens, resolvidas)
    ]
    assert ("D001", "B5.B03") in sem and ("D001", "B5.B03") not in com

    # `OQ-89` (especialista, 2026-11-06): dívida pendente fica fora do plano e
    # não bloqueia a liberação; a pendência é apontada ao aluno no plano.
    pendente = _ficha("D001", dict(_SEM_VALOR))
    dispensados = campos_dispensados(pendente, itens)
    liberada = [
        (p.item_id, p.ID_PERGUNTA)
        for p in pendencias_de_homologacao(registros, pendente, itens, dispensados)
    ]
    assert ("D001", "B5.B03") not in liberada


def test_sem_calculadora_homologacao_inalterada() -> None:
    registros = carregar_registros().registros
    respostas = _ficha("D001", {})
    itens = {EscopoRepeticao.DIVIDA_ID: ("D001",)}

    assert pendencias_de_homologacao(registros, respostas, itens) == pendencias_de_homologacao(
        registros, respostas, itens, frozenset()
    )


# --- T-529: alerta de dívida que cresce com o habitual (`RF-535`, `AC-547`) ---------------


def _faltas_de_juros(ficha: dict[str, object]) -> dict[str, Decimal]:
    from engine.motor import calcular_plano
    from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo

    respostas = _caso({"D001": ficha})
    estado = montar_estado_financeiro(
        respostas,
        DATA_REFERENCIA=DATA_REFERENCIA,
        dividas=(montar_divida(respostas, "D001"),),
        **PARAMETROS_EXTERNOS_PADRAO,  # type: ignore[arg-type]
    )
    diagnostico = calcular_plano(estado, FonteParametrosArquivo().carregar("1.0.1")).diagnostico
    return {x.DIVIDA_ID: x.FALTA_DE_JUROS for x in diagnostico.DIVIDAS_QUE_CRESCEM}


_DEZ_MIL_A_2: dict[str, object] = {
    "TIPO_DIVIDA": "PESSOAL",
    "SALDO_DEVEDOR_ATUAL": d("10.000,00"),
    "TAXA_DIVIDA": t("2"),
    "PERIODICIDADE_TAXA_DIVIDA": "MENSAL",
    "PRAZO_RESTANTE_MESES": NAO_SEI,
}


def test_ac547_crescimento_habitual_150_falta_50_sem_estimada() -> None:
    """Habitual `> 0` prevalece: nada é estimado e a falta é juros (200) menos habitual (150)."""
    ficha = {**_DEZ_MIL_A_2, _PARCELA: d("150,00")}
    assert resolver_divida(_caso({"D001": ficha}), "D001").parcela_estimada is None
    assert _faltas_de_juros(ficha) == {"D001": d("50,00")}


@pytest.mark.parametrize("habitual", [NAO_SEI, d("0,00")])
def test_ac547_crescimento_habitual_zero_ou_ausente_falta_200_mesmo_com_estimada(
    habitual: object,
) -> None:
    ficha = {**_DEZ_MIL_A_2, _PARCELA: habitual}
    respostas = _caso({"D001": ficha})
    premissas = resolver_divida(respostas, "D001")
    assert premissas.parcela_estimada is not None
    assert premissas.parcela_estimada.valor == d("528,72")
    divida = montar_divida(respostas, "D001")
    assert divida.PARCELA_CONTRATUAL == d("0")  # devido: o habitual, nunca a estimada
    assert divida.PAGAMENTO_MENSAL_EFETIVO == d("528,72")  # o que o plano paga
    assert _faltas_de_juros(ficha) == {"D001": d("200,00")}
