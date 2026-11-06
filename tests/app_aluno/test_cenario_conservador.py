"""Cenário conservador (hipótese) para quatro valores incompatíveis — `T-538`.

`T-534` a `T-536` (`RF-538`, `RF-539`, `RF-540`, `OQ-82`, `EC-76`, `AC-550` a
`AC-553`). A cascata é testada pela porta pública `escolher_hipotese`; para dar
a cada nível dois candidatos que diferem só naquele ponto, os "teóricos" são
trocados por candidatos escritos à mão (a conta de cada teórico já é coberta
por `test_calculo_divida_formulas.py`). O resto usa o cálculo real.

REGRAS: `RF-538`, `RF-539`, `RF-540`, `OQ-82`, `EC-76`, `AC-550`, `AC-551`, `AC-552`, `AC-553`
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.montagem import cenario_conservador as cenario_modulo
from app.montagem.calculo_divida import CAMPO_DA_DIVIDA
from app.montagem.cenario_conservador import Candidato, HipoteseConservadora, escolher_hipotese
from app.montagem.conversao import converter_para_dinheiro as d
from app.montagem.conversao import converter_para_taxa as t
from app.montagem.estado import montar_divida, montar_estado_financeiro
from app.montagem.premissas import MARCA_DO_VALOR, SITUACAO_DA_DIVIDA, resolver_divida
from engine.motor import calcular_plano
from engine.taxa import derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA
from engine.tipos import SISTEMA_AMORTIZACAO
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from report.plano import (
    carregar_textos_canonicos,
    formatar_dinheiro_br,
    montar_contexto_estado_inputs,
)
from tests.app_aluno.fixtures.caso_completo import DATA_REFERENCIA, PARAMETROS_EXTERNOS_PADRAO
from tests.app_aluno.test_avisos_de_pagamento import _avisos, _plano
from tests.app_aluno.test_montagem_divida_calculada import _caso
from tests.app_aluno.test_premissas_da_divida import _com_escolha, _resolver
from tests.app_aluno.test_rotas_calculadora import _PREVIA, _cliente

PRICE = SISTEMA_AMORTIZACAO.PRICE
SAC = SISTEMA_AMORTIZACAO.SAC
_PARCELA = "PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)"
_2_POR_CENTO = derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(t("2"), "MENSAL")

_BASE = Candidato(d("10000"), d("600"), _2_POR_CENTO, 24)


def _hipotese(c: Candidato, sistema: SISTEMA_AMORTIZACAO = PRICE) -> HipoteseConservadora | None:
    return escolher_hipotese(c.saldo, c.parcela, c.taxa_mensal, c.prazo, sistema)


def _contra(
    monkeypatch: pytest.MonkeyPatch, outro: Candidato | None
) -> HipoteseConservadora | None:
    """`_BASE` (digitado) contra um único candidato adversário, os demais descartados."""

    def so_o_saldo(
        campo: str, digitado: Candidato, sistema: SISTEMA_AMORTIZACAO
    ) -> Candidato | None:
        return outro if campo == "SALDO" else None

    monkeypatch.setattr(cenario_modulo, "_teorico_sem", so_o_saldo)
    return _hipotese(_BASE)


def _valores(h: HipoteseConservadora | None) -> tuple[Decimal, Decimal, Decimal, int]:
    assert h is not None
    return h.saldo, h.parcela, h.taxa_mensal, h.prazo


# --- AC-550: cada nível da cascata, nesta ordem (RF-538, OQ-82) ----------------------------


def test_ac550_nivel_1_maior_parcela_vence_mesmo_com_o_resto_maior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Candidato com saldo, taxa e prazo maiores, mas parcela menor, perde."""
    outro = Candidato(d("12000"), d("500"), t("3"), 36)
    assert _valores(_contra(monkeypatch, outro)) == _args(_BASE)


def test_ac550_nivel_1_o_de_maior_parcela_ganha_quando_e_o_outro(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outro = Candidato(d("9000"), d("650"), t("1"), 12)
    assert _valores(_contra(monkeypatch, outro)) == _args(outro)


def test_ac550_nivel_2_empate_em_parcela_vence_o_maior_saldo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outro = Candidato(d("11000"), d("600"), t("1"), 12)  # menor taxa e prazo, maior saldo
    assert _valores(_contra(monkeypatch, outro)) == _args(outro)


def test_ac550_nivel_3_empate_em_parcela_e_saldo_vence_a_maior_taxa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outro = Candidato(d("10000"), d("600"), t("3"), 12)  # maior taxa, menor prazo
    assert _valores(_contra(monkeypatch, outro)) == _args(outro)


def test_ac550_nivel_4_empate_ate_a_taxa_vence_o_maior_prazo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outro = Candidato(d("10000"), d("600"), _2_POR_CENTO, 30)
    assert _valores(_contra(monkeypatch, outro)) == _args(outro)


def test_ac550_nivel_5_custo_total_so_desempata_quando_os_quatro_primeiros_empatam() -> None:
    """O custo total é função dos quatro primeiros: nunca decide sozinho. Dois
    candidatos iguais nos quatro têm o mesmo custo e a cascata termina em `EC-76`."""
    custo = cenario_modulo._custo_total
    assert custo(_BASE, PRICE) == custo(Candidato(*_args(_BASE)), PRICE)
    assert custo(_BASE, PRICE) is not None


def _args(c: Candidato) -> tuple[Decimal, Decimal, Decimal, int]:
    return c.saldo, c.parcela, c.taxa_mensal, c.prazo


# --- EC-76: empate total ---------------------------------------------------------------------


def test_ec76_empate_total_e_deterministico_e_devolve_o_digitado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gemeo = Candidato(*_args(_BASE))
    primeira = _contra(monkeypatch, gemeo)
    segunda = _hipotese(_BASE)
    assert _valores(primeira) == _valores(segunda) == _args(_BASE)


# --- Candidatos reais: o caso do AC-534 -----------------------------------------------------


def test_ac550_caso_do_ac534_vence_a_parcela_teorica_pela_maior_parcela() -> None:
    """R$ 10.000, 2% a.m., 24 meses, parcela digitada R$ 400,00: o candidato de
    maior parcela é o teórico (R$ 528,72); o candidato da taxa não fecha e é descartado."""
    h = escolher_hipotese(d("10000"), d("400"), _2_POR_CENTO, 24, PRICE)
    assert h is not None
    assert (h.saldo, h.parcela, h.taxa_mensal, h.prazo) == (
        d("10000"),
        d("528.72"),
        _2_POR_CENTO,
        24,
    )


def test_candidato_que_falha_no_calculo_e_descartado_sem_derrubar_a_escolha() -> None:
    """Parcela abaixo dos juros: o teórico do prazo e o da taxa não existem; ainda há resposta."""
    h = escolher_hipotese(d("10000"), d("150"), _2_POR_CENTO, 24, PRICE)
    assert h is not None
    assert h.parcela >= d("150")


def test_sac_tambem_escolhe_pela_cascata() -> None:
    h = escolher_hipotese(d("12000"), d("1500"), t("1"), 12, SAC)
    assert h is not None
    assert h.parcela >= d("1500")


def test_nenhum_candidato_valido_devolve_none_e_o_chamador_mantem_os_digitados() -> None:
    assert escolher_hipotese(d("0"), d("0"), t("0"), 1, PRICE) is None


# --- AC-551 / RF-539: só saldo e taxa entram no motor ---------------------------------------

_INCOMPATIVEL: dict[str, object] = {
    "TIPO_DIVIDA": "PESSOAL",
    "SALDO_DEVEDOR_ATUAL": d("10.000,00"),
    _PARCELA: d("700,00"),  # a teórica é 528,72: não bate
    "TAXA_DIVIDA": t("2"),
    "PERIODICIDADE_TAXA_DIVIDA": "MENSAL",
    "PRAZO_RESTANTE_MESES": 24,
}


def test_ac551_so_saldo_e_taxa_viram_hipotese_e_o_digitado_fica_preservado() -> None:
    premissas = resolver_divida(_caso({"D001": _INCOMPATIVEL}), "D001")
    assert premissas.situacao is SITUACAO_DA_DIVIDA.INCOMPATIVEL
    assert premissas.hipotese_conservadora is not None

    valores = premissas.valores
    for campo in (CAMPO_DA_DIVIDA.SALDO, CAMPO_DA_DIVIDA.TAXA):
        assert valores[campo].marca is MARCA_DO_VALOR.HIPOTESE
    # parcela e prazo continuam como o aluno digitou: não governam o plano
    assert valores[CAMPO_DA_DIVIDA.PARCELA].marca is MARCA_DO_VALOR.INFORMADO
    assert valores[CAMPO_DA_DIVIDA.PRAZO].marca is MARCA_DO_VALOR.INFORMADO
    assert valores[CAMPO_DA_DIVIDA.PARCELA].valor == d("700.00")
    # o original do saldo/taxa fica guardado ao lado da hipótese
    assert valores[CAMPO_DA_DIVIDA.SALDO].original == d("10000.00")


def test_ac551_o_motor_recebe_saldo_e_taxa_da_hipotese_e_o_pagamento_declarado() -> None:
    respostas = _caso({"D001": _INCOMPATIVEL})
    hipotese = resolver_divida(respostas, "D001").hipotese_conservadora
    assert hipotese is not None

    divida = montar_divida(respostas, "D001")

    assert divida.SALDO_DEVEDOR_ATUAL == hipotese.saldo
    assert divida.TAXA_EFETIVA_MENSAL_NORMALIZADA == hipotese.taxa_mensal
    assert divida.PARCELA_CONTRATUAL == d("700.00")  # o declarado, não o do candidato
    assert divida.PAGAMENTO_MENSAL_EFETIVO == d("700.00")


def test_ac551_compativel_ou_com_escolha_de_recalculo_nao_tem_hipotese() -> None:
    compativel = {**_INCOMPATIVEL, _PARCELA: d("528,72")}
    assert resolver_divida(_caso({"D001": compativel}), "D001").hipotese_conservadora is None
    # `RF-525`: o aluno escolheu recalcular a parcela ⇒ completa, sem hipótese
    escolhida = _resolver(_com_escolha("PARCELA", parcela=d("700")))
    assert escolhida.situacao is SITUACAO_DA_DIVIDA.COMPLETA
    assert escolhida.hipotese_conservadora is None
    # sem escolha (ou "NENHUMA") ⇒ incompatível, e a hipótese vale
    sem_escolha = _resolver(_com_escolha("NENHUMA", parcela=d("700")).copy())
    assert sem_escolha.situacao is SITUACAO_DA_DIVIDA.INCOMPATIVEL
    assert sem_escolha.hipotese_conservadora is not None


# --- AC-552 / RF-540: o resultado do mês não muda com a hipótese ----------------------------


def _resultado_do_mes(ficha: dict[str, object]) -> tuple[Decimal, Decimal]:
    respostas = _caso({"D001": ficha})
    estado = montar_estado_financeiro(
        respostas,
        DATA_REFERENCIA=DATA_REFERENCIA,
        dividas=(montar_divida(respostas, "D001"),),
        **PARAMETROS_EXTERNOS_PADRAO,  # type: ignore[arg-type]
    )
    diagnostico = calcular_plano(estado, FonteParametrosArquivo().carregar("1.0.1")).diagnostico
    return diagnostico.RESULTADO_MENSAL_ATUAL, diagnostico.RESULTADO_CAIXA_OBSERVADO


def test_ac552_dois_cenarios_diferentes_dao_o_mesmo_resultado_do_mes() -> None:
    um = _INCOMPATIVEL
    outro = {**_INCOMPATIVEL, "SALDO_DEVEDOR_ATUAL": d("8.000,00"), "PRAZO_RESTANTE_MESES": 36}
    h_um = resolver_divida(_caso({"D001": um}), "D001").hipotese_conservadora
    h_outro = resolver_divida(_caso({"D001": outro}), "D001").hipotese_conservadora
    assert h_um is not None and h_outro is not None
    assert (h_um.saldo, h_um.taxa_mensal) != (
        h_outro.saldo,
        h_outro.taxa_mensal,
    )  # cenários distintos

    assert _resultado_do_mes(um) == _resultado_do_mes(outro)


# --- AC-553: a hipótese é sinalizada ao aluno (ficha e relatório) e ao revisor ---------------

_PREVIA_INCOMPATIVEL = {
    "sistema": "PRICE",
    "periodicidade": "MENSAL",
    "saldo": "10.000,00",
    "parcela": "700,00",
    "taxa": "2,00",
    "prazo": "24",
    "recalcular": None,
}


def test_ac553_previa_marca_a_hipotese_e_so_expoe_saldo_e_taxa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente, _ = _cliente(monkeypatch)
    dados = cliente.post(_PREVIA, json=_PREVIA_INCOMPATIVEL).json()

    assert dados["estado"] == "INCOMPATIVEL"
    hipotese = dados["hipotese_conservadora"]
    assert hipotese["marca"] == "HIPOTESE"
    assert hipotese["saldo"].startswith("R$ ") and hipotese["taxa"]
    # RF-539: parcela e prazo da hipótese não governam o plano, então não saem
    assert not {"parcela", "prazo"} & set(hipotese)


def test_ac553_previa_com_escolha_de_recalculo_ou_compativel_nao_tem_hipotese(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente, _ = _cliente(monkeypatch)
    escolhida = cliente.post(_PREVIA, json={**_PREVIA_INCOMPATIVEL, "recalcular": "PARCELA"}).json()
    compativel = cliente.post(_PREVIA, json={**_PREVIA_INCOMPATIVEL, "parcela": "528,72"}).json()
    assert escolhida.get("hipotese_conservadora") is None
    assert compativel.get("hipotese_conservadora") is None


def test_ac553_relatorio_avisa_a_hipotese_e_o_revisor_ve_estimado() -> None:
    snapshot, vocabulario, contexto = _plano({_PARCELA: d("700,00"), "PRAZO_RESTANTE_MESES": 24})
    divida = snapshot.estado_inputs.dividas[0]

    assert vocabulario.dividas_com_hipotese == frozenset({"D001"})
    # o motor recebeu saldo e taxa da hipótese e o pagamento declarado (RF-539, RF-540)
    assert divida.SALDO_DEVEDOR_ATUAL != d("10000")
    assert divida.PARCELA_CONTRATUAL == divida.PAGAMENTO_MENSAL_EFETIVO == d("700,00")
    # aluno: o aviso nomeia a dívida e traz o saldo da hipótese
    assert formatar_dinheiro_br(divida.SALDO_DEVEDOR_ATUAL) in _avisos(contexto)  # type: ignore[arg-type]
    # revisor: a hipótese aparece como `estimado` em saldo e taxa; parcela sem marca (OQ-87)
    estado = montar_contexto_estado_inputs(
        snapshot.estado_inputs, carregar_textos_canonicos(), vocabulario
    )
    marcas = {c.codigo: c.marca for c in estado.dividas[0].campos if c.marca}
    assert marcas.get("SALDO_DEVEDOR_ATUAL") == "estimado"
    assert marcas.get("TAXA_EFETIVA_MENSAL_NORMALIZADA") == "estimado"
    assert "PARCELA_CONTRATUAL" not in marcas
