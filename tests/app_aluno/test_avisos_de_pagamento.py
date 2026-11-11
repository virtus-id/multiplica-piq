"""Avisos do plano sobre o pagamento da dívida — `T-530`, `T-531` (Fase 2).

Plano real (motor de verdade, `engine/` intocado) lido por
`montar_contexto_plano`: o aviso de inviabilidade, a hipótese de 24 meses e o
"não é um zero declarado". Textos provisórios (`T-532`); os testes conferem
estrutura, não redação.

REGRAS: `RF-533`, `RF-535`, `RF-536`, `AC-545`, `AC-548`
"""

from __future__ import annotations

from datetime import date

from app.http.serializacao_plano import vocabulario_do_caso
from app.montagem.conversao import converter_para_dinheiro as d
from app.montagem.conversao import converter_para_taxa as t
from app.montagem.estado import montar_divida, montar_estado_financeiro
from app.montagem.premissas import premissas_da_ficha
from collection.respostas import NAO_SEI
from engine.motor import calcular_plano
from engine.snapshot import SnapshotOrdem
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from report.plano import (
    ContextoPlano,
    VocabularioDoCaso,
    carregar_textos_canonicos,
    montar_contexto_estado_inputs,
    montar_contexto_plano,
)
from tests.app_aluno.fixtures.caso_completo import DATA_REFERENCIA, PARAMETROS_EXTERNOS_PADRAO
from tests.app_aluno.test_montagem_divida_calculada import _caso, _itens, _por_escopo

_PARCELA = "PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)"
_PARAMETROS = FonteParametrosArquivo().carregar("1.0.1")
_FICHA: dict[str, object] = {
    "TIPO_DIVIDA": "PESSOAL",
    "SALDO_DEVEDOR_ATUAL": d("10.000,00"),
    "TAXA_DIVIDA": t("2"),
    "PERIODICIDADE_TAXA_DIVIDA": "MENSAL",
    "PESO_EMOCIONAL": 5,
    "PRAZO_RESTANTE_MESES": NAO_SEI,
}


def _plano(
    ficha: dict[str, object],
) -> tuple[SnapshotOrdem, VocabularioDoCaso, ContextoPlano]:
    respostas = _caso({"D001": {**_FICHA, **ficha}})
    itens = _por_escopo(_itens(("D001",)))

    estado = montar_estado_financeiro(
        respostas,
        DATA_REFERENCIA=DATA_REFERENCIA,
        dividas=(montar_divida(respostas, "D001"),),
        **PARAMETROS_EXTERNOS_PADRAO,  # type: ignore[arg-type]
    )
    snapshot = calcular_plano(estado, _PARAMETROS)
    vocabulario = vocabulario_do_caso(
        (), respostas, ["D001"], (), premissas_da_ficha(respostas, itens)
    )
    contexto = montar_contexto_plano(
        snapshot, carregar_textos_canonicos(), vocabulario, None, date(2026, 11, 5)
    )
    return snapshot, vocabulario, contexto


def _avisos(contexto: ContextoPlano) -> str:
    return " ".join(contexto.avisos_gerais)


def test_ac548_inviavel_pagamento_informado_permanece_e_texto_nao_cita_24_meses() -> None:
    snapshot, _, contexto = _plano({_PARCELA: d("150,00")})
    divida = snapshot.estado_inputs.dividas[0]
    assert divida.PARCELA_CONTRATUAL == divida.PAGAMENTO_MENSAL_EFETIVO == d("150,00")
    texto = _avisos(contexto)
    assert "R$ 150,00" in texto and "não cobre os juros" in texto
    assert "24 meses" not in texto


def test_ac545_habitual_ausente_avisa_hipotese_de_24_meses() -> None:
    snapshot, vocabulario, contexto = _plano({_PARCELA: NAO_SEI})
    divida = snapshot.estado_inputs.dividas[0]
    # `T-543` (`OQ-96`): a estimada é o devido e o pago
    assert divida.PARCELA_CONTRATUAL == divida.PAGAMENTO_MENSAL_EFETIVO == d("528,72")
    texto = _avisos(contexto)
    assert "24 meses" in texto and "R$ 528,72" in texto
    assert "R$ 0,00" not in texto
    assert "não cobre os juros" not in texto  # a ausência não vira "pagamento informado"
    estado = montar_contexto_estado_inputs(
        snapshot.estado_inputs, carregar_textos_canonicos(), vocabulario
    )
    marcas = {c.codigo: c.marca for c in estado.dividas[0].campos if c.marca}
    assert marcas.get("PAGAMENTO_MENSAL_EFETIVO") == marcas.get("PARCELA_CONTRATUAL") == "estimado"


def test_t543_mes_que_nao_comporta_a_estimada_e_deficit_com_uma_conta_so() -> None:
    """`OQ-96`: o resultado do mês e o caixa são o mesmo número; o plano
    estabiliza por déficit, sem o aviso de caixa negativo à parte."""
    snapshot, _, contexto = _plano(
        {_PARCELA: NAO_SEI, "SALDO_DEVEDOR_ATUAL": d("40.000,00"), "TAXA_DIVIDA": t("3")}
    )
    diagnostico = snapshot.diagnostico
    assert diagnostico.RESULTADO_CAIXA_OBSERVADO == diagnostico.RESULTADO_MENSAL_ATUAL < 0
    assert diagnostico.MODO_ESTABILIZACAO
    assert "seu mês fecha em" not in _avisos(contexto)


def test_valor_declarado_acima_da_sobra_avisa_o_valor_que_o_plano_usa() -> None:
    """Especialista, 2026-11-06: o aluno é informado; `T-540`: com o valor
    que o motor de fato usa (`MIN(estrutural, declarado) × fator`)."""
    snapshot, _, contexto = _plano({_PARCELA: d("1.000,00")})
    assert snapshot.estado_inputs.CAPACIDADE_ATAQUE_DECLARADA == d("500")
    texto = _avisos(contexto)
    assert "maior do que sobra no seu mês (R$ 400,00)" in texto
    assert "usa R$ 380,00 por mês" in texto


def test_valor_declarado_sem_aviso_quando_cabe_ou_sem_cronograma() -> None:
    _, _, cabe = _plano({_PARCELA: d("300,00")})
    assert "maior do que sobra" not in _avisos(cabe)
    snapshot, _, estabilizacao = _plano({_PARCELA: d("2.000,00")})
    assert snapshot.diagnostico.MODO_ESTABILIZACAO
    assert "maior do que sobra" not in _avisos(estabilizacao)
