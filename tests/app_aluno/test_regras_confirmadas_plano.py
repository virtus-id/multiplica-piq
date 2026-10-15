"""`T-399` parte A (`RF-412`) — avisos de atraso, garantia e fichas faltando,
fixo × variável, resultado mensal, e o vínculo da dívida no plano.

O snapshot vem do motor REAL; as respostas extras só chegam ao
`VocabularioDoCaso` (a ordem e o motor não as leem — critério "sem mudar a
ordem").

REGRAS: `RF-412`
"""

from __future__ import annotations

from decimal import Decimal

from app.http.serializacao_plano import serializar_plano, vocabulario_do_caso
from app.montagem.conversao import converter_para_dinheiro
from app.montagem.entrada import fotografia_do_mes
from app.montagem.estado import montar_divida, montar_estado_financeiro
from collection.respostas import RespostasCaso
from engine.motor import calcular_plano
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from report.pdf import renderizar_html_do_plano
from report.plano import (
    ContextoPlano,
    carregar_textos_canonicos,
    formatar_dinheiro_br,
    montar_contexto_plano,
)
from tests.app_aluno.fixtures.caso_completo import (
    DATA_REFERENCIA,
    DIVIDA_ID_UNICA,
    _resposta_caso,
    _resposta_item,
    caso_completo,
)

_RESPONSABILIDADE = "A responsabilidade pela informação é do aluno."
_ATRASADA = (
    "Esta dívida está atrasada. Procure o credor para negociar antes de qualquer outra coisa."
)


def _plano(
    extras: tuple[object, ...] = (), *, valores_item_despesa: dict[str, object] | None = None
) -> tuple[ContextoPlano, str]:
    caso = caso_completo(valores_item_despesa=valores_item_despesa)
    respostas = RespostasCaso(respostas=caso.respostas.respostas + extras)  # type: ignore[operator]
    estado = montar_estado_financeiro(
        respostas,
        DATA_REFERENCIA=DATA_REFERENCIA,
        dividas=(montar_divida(respostas, DIVIDA_ID_UNICA),),
        **caso.parametros_externos,  # type: ignore[arg-type]
    )
    snapshot = calcular_plano(estado, FonteParametrosArquivo().carregar("1.0.1"))
    vocabulario = vocabulario_do_caso((), respostas, (DIVIDA_ID_UNICA,))
    textos = carregar_textos_canonicos()
    contexto = montar_contexto_plano(snapshot, textos, vocabulario)
    return contexto, renderizar_html_do_plano(contexto, textos)


def _item(variavel: str, valor: object, item: str = DIVIDA_ID_UNICA) -> object:
    return _resposta_item(variavel, item, valor)


def test_ac_divida_atrasada_avisa_com_a_responsabilidade_e_nao_muda_a_ordem() -> None:
    base, _ = _plano()
    contexto, html = _plano((_item("DIVIDA_EM_DIA / DIVIDA_ATRASADA", "VENCIDO"),))
    assert contexto.ordem[0].avisos == (f"{_ATRASADA} {_RESPONSABILIDADE}",)
    assert _ATRASADA in html and _RESPONSABILIDADE in html
    assert [p.DIVIDA_ID for p in contexto.ordem] == [p.DIVIDA_ID for p in base.ordem]
    assert base.ordem[0].avisos == ()


def test_ac_em_dia_nao_avisa() -> None:
    contexto, _ = _plano((_item("DIVIDA_EM_DIA / DIVIDA_ATRASADA", "EM_DIA"),))
    assert contexto.ordem[0].avisos == ()


def test_ac_divida_com_garantia_avisa_com_a_responsabilidade() -> None:
    contexto, html = _plano((_item("POSSUI_GARANTIA", "SIM"),))
    (aviso,) = contexto.ordem[0].avisos
    assert "garantia" in aviso and aviso.endswith(_RESPONSABILIDADE)
    assert aviso in html.replace("&#39;", "'")


def test_ac_fichas_declaradas_faltando_avisa_sem_bloquear() -> None:
    contexto, html = _plano((_resposta_caso("QUANTIDADE_DIVIDAS_DECLARADA_INICIAL", 3),))
    (aviso,) = contexto.avisos_gerais
    assert aviso.endswith(_RESPONSABILIDADE)
    assert contexto.ordem  # o plano segue existindo
    assert aviso in html
    sem_falta, _ = _plano()
    assert sem_falta.avisos_gerais == ()


def test_ac_payload_do_aluno_leva_os_avisos() -> None:
    contexto, _ = _plano((_item("POSSUI_GARANTIA", "SIM"),))
    payload = serializar_plano(contexto, textos=carregar_textos_canonicos())
    assert payload["ordem"][0]["avisos"] == list(contexto.ordem[0].avisos)
    assert payload["avisos_gerais"] == []


def test_ac_fixo_variavel_e_despesas_mensais_totais() -> None:
    extra = (
        _item("VALOR_DESPESA", converter_para_dinheiro("1.000,00"), "DESP-2"),
        _item("CLASSIFICACAO_FIXA_VARIAVEL", "VARIAVEL", "DESP-2"),
    )
    contexto, html = _plano(
        extra, valores_item_despesa={"CLASSIFICACAO_FIXA_VARIAVEL": "FIXA"}
    )
    ponto = contexto.ponto_de_partida
    assert ponto is not None
    assert ponto.despesas_tipo_fixo == formatar_dinheiro_br(Decimal("6500"))
    assert ponto.despesas_tipo_variavel == formatar_dinheiro_br(Decimal("1000"))
    assert ponto.despesas_nao_classificadas == ""
    caso = caso_completo(valores_item_despesa={"CLASSIFICACAO_FIXA_VARIAVEL": "FIXA"})
    todas = RespostasCaso(respostas=caso.respostas.respostas + extra)  # type: ignore[operator]
    sobra = fotografia_do_mes(todas).SOBRA_ANTES_DAS_DIVIDAS
    assert isinstance(sobra, Decimal)
    assert ponto.despesas_mensais_totais == formatar_dinheiro_br(sobra)
    assert "Despesas mensais totais (receitas totais − despesas totais)" in html
    payload = serializar_plano(contexto, textos=carregar_textos_canonicos())
    assert payload["ponto_de_partida"]["despesas_tipo_fixo"] == ponto.despesas_tipo_fixo


def test_ac_despesa_sem_classificacao_aparece_a_parte() -> None:
    contexto, _ = _plano()
    ponto = contexto.ponto_de_partida
    assert ponto is not None
    assert ponto.despesas_tipo_fixo == formatar_dinheiro_br(Decimal(0))
    assert ponto.despesas_nao_classificadas == formatar_dinheiro_br(Decimal("6500"))


def test_ac_vinculo_da_divida_aparece_como_fato() -> None:
    extras = (
        _item("VINCULO_DA_DIVIDA", "V-1"),
        _item("ORGAO_FONTE_PAGADORA", "Prefeitura de Teste", "V-1"),
    )
    contexto, _ = _plano(extras)
    assert ("Vínculo em que é descontada", "Prefeitura de Teste") in contexto.ordem[0].fatos
    sem, _ = _plano()
    assert all(rotulo != "Vínculo em que é descontada" for rotulo, _ in sem.ordem[0].fatos)


def test_ac_sem_vocabulario_nada_muda() -> None:
    caso = caso_completo()
    estado = montar_estado_financeiro(
        caso.respostas,
        DATA_REFERENCIA=DATA_REFERENCIA,
        dividas=(montar_divida(caso.respostas, DIVIDA_ID_UNICA),),
        **caso.parametros_externos,  # type: ignore[arg-type]
    )
    snapshot = calcular_plano(estado, FonteParametrosArquivo().carregar("1.0.1"))
    contexto = montar_contexto_plano(snapshot, carregar_textos_canonicos())
    assert contexto.avisos_gerais == () and contexto.ordem[0].avisos == ()
    assert contexto.ponto_de_partida is not None
    assert contexto.ponto_de_partida.despesas_tipo_fixo == ""
