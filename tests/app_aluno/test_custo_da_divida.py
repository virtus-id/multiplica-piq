"""Pergunta única de custo da dívida — `T-393` (`RF-407`), regra `§16.1`.

Prova: (a) o registro de `B5.D06`; (b) o bloqueio do cálculo sem o valor;
(c) o ranking por juros com a taxa informada ao ano; (d) o plano não cobra o
CET como informação pendente.

REGRAS: RF-407 (enxugamento-questionario), §16.1
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.casos.progresso import pendencias_obrigatorias
from app.montagem.estado import montar_divida, montar_estado_financeiro
from collection.carga import carregar_registros
from collection.registro import EscopoRepeticao, Obrigatoriedade, RegistroPergunta, TipoResposta
from collection.respostas import RespostasCaso
from engine.motor import calcular_plano
from engine.snapshot import SnapshotOrdem
from engine.tipos import DESCONHECIDO
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from report.plano import _campos_desconhecidos_da_divida, carregar_textos_canonicos
from tests.app_aluno.fixtures.caso_completo import (
    DATA_REFERENCIA,
    caso_completo,
    montar_respostas_caso,
    sem_o_custo_da_divida,
)

_ANTIGAS = ("B5.D01", "B5.D01A", "B5.D01B", "B5.D03", "B5.D03A")


def _registro_d06() -> RegistroPergunta:
    return next(r for r in carregar_registros().registros if r.ID == "B5.D06")


def test_registro_substitui_as_cinco_perguntas_por_uma() -> None:
    ids = {r.ID for r in carregar_registros().registros}
    assert not (set(_ANTIGAS) & ids)
    d06 = _registro_d06()
    assert d06.tipo is TipoResposta.SELECAO_UNICA
    assert d06.escopo_repeticao is EscopoRepeticao.DIVIDA_ID
    assert d06.obrigatoriedade == frozenset({Obrigatoriedade.OBR, Obrigatoriedade.REP})
    assert d06.indispensavel is True
    assert d06.admite_nao_sei is False
    assert all(not o.admite_nao_sei for o in d06.opcoes)
    assert {o.valor_interno for o in d06.opcoes} == {"MENSAL", "ANUAL"}
    assert {o.variavel_do_campo for o in d06.opcoes} == {"TAXA_DIVIDA"}
    assert "CET" in d06.enunciado and "taxa de juros" in d06.enunciado


def _respostas_sem_o_custo(divida_id: str) -> RespostasCaso:
    return sem_o_custo_da_divida(caso_completo(DIVIDA_ID=divida_id).respostas)


def test_bloqueio_divida_sem_o_valor_impede_o_calculo() -> None:
    """`pendencias_obrigatorias` é o que o Bloco 6 consulta antes de calcular."""
    registros = carregar_registros().registros
    itens = {EscopoRepeticao.DIVIDA_ID: ("D-CASO-COMPLETO",)}
    completo = caso_completo().respostas
    assert not [p for p in pendencias_obrigatorias(registros, completo, itens) if p.ID == "B5.D06"]

    sem = _respostas_sem_o_custo("D-CASO-COMPLETO")
    pendentes = [(p.ID, p.item_id) for p in pendencias_obrigatorias(registros, sem, itens)]
    assert ("B5.D06", "D-CASO-COMPLETO") in pendentes


def _snapshot(taxa_a: tuple[str, Decimal], taxa_b: tuple[str, Decimal]) -> SnapshotOrdem:
    """Duas dívidas iguais, só o custo muda (mesmo padrão de `test_plano.py`)."""
    a = caso_completo(
        DIVIDA_ID="D-A",
        valores_divida={"PERIODICIDADE_TAXA_DIVIDA": taxa_a[0], "TAXA_DIVIDA": taxa_a[1]},
    )
    b = montar_respostas_caso(
        valores_divida={"PERIODICIDADE_TAXA_DIVIDA": taxa_b[0], "TAXA_DIVIDA": taxa_b[1]},
        DIVIDA_ID="D-B",
    )
    respostas = RespostasCaso(respostas=a.respostas.respostas + b.respostas)
    estado = montar_estado_financeiro(
        respostas,
        DATA_REFERENCIA=DATA_REFERENCIA,
        dividas=(montar_divida(respostas, "D-A"), montar_divida(respostas, "D-B")),
        **a.parametros_externos,  # type: ignore[arg-type]
    )
    return calcular_plano(estado, FonteParametrosArquivo().carregar("1.0.1"))


@pytest.mark.parametrize("anual_vence", [True, False])
def test_ranking_usa_a_taxa_mensal_normalizada_mesmo_se_veio_ao_ano(anual_vence: bool) -> None:
    """60% a.a. (≈ 3,9% a.m.) contra 3% a.m.: a dívida informada ao ano sobe
    na ordem; com 30% a.a. (≈ 2,2% a.m.) contra 3% a.m., desce."""
    anual = Decimal("0.6") if anual_vence else Decimal("0.3")
    snapshot = _snapshot(("MENSAL", Decimal("0.03")), ("ANUAL", anual))
    ordem = [p.DIVIDA_ID for p in snapshot.ORDEM_QUITACAO]
    assert ordem == (["D-B", "D-A"] if anual_vence else ["D-A", "D-B"])


def test_plano_nao_cobra_o_cet_como_pendencia() -> None:
    """Dívida sem o custo (e `CET` sempre desconhecido): a lista de
    informações pendentes do plano traz a taxa, nunca o `CET` sozinho."""
    respostas = _respostas_sem_o_custo("D-CASO-COMPLETO")
    divida = montar_divida(respostas, "D-CASO-COMPLETO")
    assert divida.CET is DESCONHECIDO

    campos = _campos_desconhecidos_da_divida(divida)
    assert "TAXA_EFETIVA_MENSAL_NORMALIZADA" in campos
    assert "CET" not in campos

    textos = carregar_textos_canonicos()
    rotulo = textos.rotulos_de_pendencia["TAXA_EFETIVA_MENSAL_NORMALIZADA"]
    assert rotulo == "o CET ou a taxa de juros"
    assert "CET" not in textos.rotulos_de_pendencia
    assert "CET" not in textos.onde_achar
    assert "CET" not in textos.pergunta_do_campo
    assert textos.pergunta_do_campo["TAXA_EFETIVA_MENSAL_NORMALIZADA"] == "B5.D06"
