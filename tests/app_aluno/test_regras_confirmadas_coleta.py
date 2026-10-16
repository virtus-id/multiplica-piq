"""`T-399` parte B (`RF-412`) — `B3.C00A` bloqueia, `B3.C02C` compara a sobra ou
falta com o resultado calculado e `B3.04A` soma à renda e aparece no plano.

REGRAS: `RF-412`
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.casos.progresso import coleta_pode_avancar, pendencias_obrigatorias
from app.http.rotas_calculo import _respostas_do_calculo
from app.montagem.conversao import converter_para_dinheiro
from app.montagem.entrada import comparar_sobra_ou_falta, fotografia_do_mes
from collection.carga import carregar_registros
from collection.respostas import NAO_SEI, Resposta, RespostasCaso
from report.plano import formatar_dinheiro_br
from tests.app_aluno.fixtures.caso_completo import _resposta_caso, caso_completo
from tests.app_aluno.test_regras_confirmadas_plano import _plano
from tests.app_aluno.test_rotas_coleta_fotografia import (
    _CASO,
    _cliente,
    _resposta,
)

_REGISTROS = carregar_registros().registros
_R = converter_para_dinheiro


def _ids_pendentes(*respostas: Resposta) -> set[str]:
    return {p.ID for p in pendencias_obrigatorias(_REGISTROS, RespostasCaso(respostas=respostas))}


# --- B3.C00A: bloqueia e exige indicar o que não confere ---------------------


@pytest.mark.parametrize("resposta", ["FALTA_DESPESA", "VALOR_ERRADO"])
def test_ac_c00_que_nao_confere_bloqueia_ate_indicar_o_que_nao_condiz(resposta: str) -> None:
    c00 = _resposta("CONFIRMACAO_MAPEAMENTO_DESPESAS", resposta)
    assert "B3.C00A" in _ids_pendentes(c00)
    respondida = _resposta("ITENS_NAO_USADOS", "x")  # outra variável não destrava
    assert "B3.C00A" in _ids_pendentes(c00, respondida)
    assert "B3.C00A" not in _ids_pendentes(
        c00, _resposta("ITENS_NAO_CONDIZENTES", "Faltou a conta de luz")
    )


def test_ac_c00_que_confere_nao_pede_o_que_nao_condiz() -> None:
    assert "B3.C00A" not in _ids_pendentes(_resposta("CONFIRMACAO_MAPEAMENTO_DESPESAS", "SIM"))


def test_ac_c00_nao_admite_nao_sei() -> None:
    (c00,) = [r for r in _REGISTROS if r.ID == "B3.C00"]
    assert c00.admite_nao_sei is False
    assert [o.valor_interno for o in c00.opcoes] == ["SIM", "FALTA_DESPESA", "VALOR_ERRADO"]


def test_ac_c00a_traz_a_responsabilidade_do_aluno() -> None:
    (c00a,) = [r for r in _REGISTROS if r.ID == "B3.C00A"]
    assert "A responsabilidade pela informação é do aluno." in c00a.enunciado


def test_ac_c00_que_nao_confere_impede_o_avanco_da_coleta() -> None:
    c00 = RespostasCaso(respostas=(_resposta("CONFIRMACAO_MAPEAMENTO_DESPESAS", "VALOR_ERRADO"),))
    assert not coleta_pode_avancar(_REGISTROS, c00)


# --- B3.C02A/B3.C02B: compara com o resultado calculado ----------------------


def _caso_com(**valores: object) -> RespostasCaso:
    # a fixture traz uma sobra percebida; o teste decide a sua
    base = tuple(
        r for r in caso_completo().respostas.respostas if r.ID_PERGUNTA != "SOBRA_PERCEBIDA"
    )
    return RespostasCaso(
        respostas=base + tuple(_resposta_caso(k, v) for k, v in valores.items())
    )


def test_ac_sobra_informada_e_comparada_com_o_resultado_calculado() -> None:
    respostas = _caso_com(SOBRA_PERCEBIDA=_R("1.000,00"))
    calculado = fotografia_do_mes(respostas).SOBRA_ANTES_DAS_DIVIDAS
    assert isinstance(calculado, Decimal)
    comparacao = comparar_sobra_ou_falta(respostas)
    assert comparacao is not None
    assert (comparacao.sentido, comparacao.calculado) == ("SOBRA", calculado)
    assert comparacao.diferenca == Decimal("1000") - calculado


def test_ac_falta_informada_conta_como_negativa() -> None:
    respostas = _caso_com(FALTA_PERCEBIDA=_R("300,00"))
    calculado = fotografia_do_mes(respostas).SOBRA_ANTES_DAS_DIVIDAS
    comparacao = comparar_sobra_ou_falta(respostas)
    assert comparacao is not None and isinstance(calculado, Decimal)
    assert (comparacao.sentido, comparacao.diferenca) == ("FALTA", Decimal("-300") - calculado)


def test_ac_sem_sobra_nem_falta_nao_ha_comparacao() -> None:
    assert comparar_sobra_ou_falta(_caso_com()) is None


def test_ac_painel_da_c02c_mostra_a_diferenca_sem_tolerancia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente, respostas = _cliente(monkeypatch)
    respostas.gravar(_resposta("PERCEPCAO_FECHAMENTO_MES", "SOBRA"))
    respostas.gravar(_resposta("SOBRA_PERCEBIDA", _R("2.500,01")))  # 1 centavo acima de 2.500,00
    painel = cliente.get(f"/caso/{_CASO}/pergunta/B3.C02C").json()["pergunta"]["painel"]
    assert painel["comparacao"] == {
        "sentido": "SOBRA",
        "informado": "2500.01",
        "calculado": "2500.00",
        "diferenca": "0.01",
    }
    # a fotografia do mês vai junto, com os destinos de correção ("revisar")
    assert painel["despesas_por_item"][0]["corrigir"]["ID_PERGUNTA"] == "B3.DF01"


def test_ac_painel_da_c00_nao_leva_comparacao(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, _ = _cliente(monkeypatch)
    painel = cliente.get(f"/caso/{_CASO}/pergunta/B3.C00").json()["pergunta"]["painel"]
    assert painel["comparacao"] is None


def test_ac_c02c_aceitar_ou_revisar_nao_bloqueia_depois_de_escolher() -> None:
    sobra = (_resposta("PERCEPCAO_FECHAMENTO_MES", "SOBRA"), _resposta("SOBRA_PERCEBIDA", _R("9")))
    assert "B3.C02C" in _ids_pendentes(*sobra)
    for escolha in ("ACEITAR_DIFERENCA", "REVISAR"):
        escolhida = _resposta("CONFERENCIA_SOBRA_FALTA", escolha)
        assert "B3.C02C" not in _ids_pendentes(*sobra, escolhida)
    # quem diz que fecha no zero a zero não passa pela comparação
    assert "B3.C02C" not in _ids_pendentes(_resposta("PERCEPCAO_FECHAMENTO_MES", "ZERO"))


# --- B3.04A: soma à renda e o plano avisa ------------------------------------


def test_ac_contribuicao_familiar_soma_a_renda_da_montagem() -> None:
    sem = fotografia_do_mes(_caso_com()).RENDA_TOTAL
    com = fotografia_do_mes(_caso_com(CONTRIBUICAO_FAMILIAR=_R("700,00"))).RENDA_TOTAL
    assert isinstance(sem, Decimal) and isinstance(com, Decimal)
    assert com == sem + Decimal("700")


@pytest.mark.parametrize("resposta", [NAO_SEI, None])
def test_ac_contribuicao_familiar_nao_sei_ou_ausente_deixa_a_renda_igual(resposta: object) -> None:
    sem = fotografia_do_mes(_caso_com()).RENDA_TOTAL
    extras = {} if resposta is None else {"CONTRIBUICAO_FAMILIAR": resposta}
    assert fotografia_do_mes(_caso_com(**extras)).RENDA_TOTAL == sem


def test_ac_contribuicao_familiar_so_vale_com_b3_04_sim() -> None:
    base = _caso_com(CONTRIBUICAO_FAMILIAR=_R("700,00"), CONTRIBUICAO_FAMILIAR_EXISTE="NAO")
    filtradas = _respostas_do_calculo(_REGISTROS, base)
    assert fotografia_do_mes(filtradas).RENDA_TOTAL == fotografia_do_mes(_caso_com()).RENDA_TOTAL


def test_ac_plano_sem_b3_04a_e_identico_ao_de_antes() -> None:
    contexto, html = _plano()
    ponto = contexto.ponto_de_partida
    assert ponto is not None and ponto.contribuicao_familiar == ""
    assert "o que outra pessoa da família coloca" not in html


def test_ac_plano_com_b3_04a_mostra_a_renda_considerada_e_muda_a_renda() -> None:
    base, _ = _plano()
    contexto, html = _plano(
        (
            _resposta_caso("CONTRIBUICAO_FAMILIAR_EXISTE", "SIM"),
            _resposta_caso("CONTRIBUICAO_FAMILIAR", _R("700,00")),
        )
    )
    ponto, ponto_base = contexto.ponto_de_partida, base.ponto_de_partida
    assert ponto is not None and ponto_base is not None
    assert ponto.contribuicao_familiar == formatar_dinheiro_br(Decimal("700"))
    assert ponto.renda != ponto_base.renda
    assert "o que outra pessoa da família coloca" in html


def test_ac_post_da_c00_que_nao_confere_leva_a_c00a_e_so_depois_a_c01(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from collection.carga import ColecaoDeRegistros

    reais = {r.ID: r for r in _REGISTROS}
    trecho = ColecaoDeRegistros(
        QUESTIONARIO_VERSION="1.0.3",
        registros=(reais["B3.C00"], reais["B3.C00A"], reais["B3.C01"]),
    )
    cliente, _ = _cliente(monkeypatch, trecho)
    url = f"/caso/{_CASO}/resposta"

    primeira = cliente.post(url, data={"ID_PERGUNTA": "B3.C00", "valor": "VALOR_ERRADO"})
    assert primeira.status_code == 200, primeira.text
    assert primeira.json()["proxima"]["pergunta"]["ID"] == "B3.C00A"

    segunda = cliente.post(
        url, data={"ID_PERGUNTA": "B3.C00A", "valor": "O aluguel está com o valor antigo"}
    )
    assert segunda.status_code == 200, segunda.text
    assert segunda.json()["proxima"]["pergunta"]["ID"] == "B3.C01"
