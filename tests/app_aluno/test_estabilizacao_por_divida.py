"""Mês positivo, mas a parcela de alguma dívida não cobre os juros — `RF-480` (`T-462`).

O motor classifica (`MOTIVO_ESTABILIZACAO = DIVIDA_QUE_CRESCE`, `RF-79`); o
relatório só lê e formata. O snapshot parte do caso comum e troca o diagnóstico
pelos números do `aluno.teste3` (valor livre 475; faltas 500 e 398).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from engine.diagnostico import DividaQueCresce
from engine.precisao import dinheiro
from engine.snapshot import SnapshotOrdem
from engine.tipos import MOTIVO_ESTABILIZACAO
from report.pdf import renderizar_html_do_plano
from report.plano import (
    carregar_textos_canonicos,
    montar_contexto_plano,
)
from tests.app_aluno.test_curso_e_incomodo import _snapshot


def _com_divida_que_cresce(snapshot: SnapshotOrdem) -> SnapshotOrdem:
    d1, d2 = (d.DIVIDA_ID for d in snapshot.estado_inputs.dividas)
    diagnostico = replace(
        snapshot.diagnostico,
        MODO_ESTABILIZACAO=True,
        MOTIVO_ESTABILIZACAO=MOTIVO_ESTABILIZACAO.DIVIDA_QUE_CRESCE,
        RESULTADO_MENSAL_ATUAL=dinheiro("475"),
        DEFICIT_MENSAL=dinheiro("0"),
        FALTA_TOTAL_DE_JUROS=dinheiro("898"),
        DIVIDAS_QUE_CRESCEM=(
            DividaQueCresce(d1, dinheiro("1000"), dinheiro("500"), dinheiro("500")),
            DividaQueCresce(d2, dinheiro("1898"), dinheiro("1500"), dinheiro("398")),
        ),
    )
    return replace(snapshot, diagnostico=diagnostico)


def test_rf_480_mensagem_propria_sem_dizer_que_o_aluno_esta_no_deficit() -> None:
    textos = carregar_textos_canonicos()
    contexto = montar_contexto_plano(_com_divida_que_cresce(_snapshot()), textos)
    assert contexto.MODO_ESTABILIZACAO and contexto.ESTABILIZACAO_POR_DIVIDA
    assert contexto.FALTA_TOTAL_DE_JUROS == "R$ 898,00"
    assert [(p, j, f) for _, p, j, f in contexto.dividas_que_crescem] == [
        ("R$ 500,00", "R$ 1.000,00", "R$ 500,00"),
        ("R$ 1.500,00", "R$ 1.898,00", "R$ 398,00"),
    ]

    html = renderizar_html_do_plano(contexto, textos).replace("&#39;", "'")
    assert "Seu mês fecha positivo, mas suas dívidas estão crescendo" in html
    assert "R$ 475,00 livres por mês" in html and "R$ 898,00 por mês" in html
    assert "O saldo aumenta R$ 500,00 por mês" in html
    # nenhuma frase do deficitário
    assert "entra menos do que sai" not in html
    assert "faltam cortar" not in html
    assert not any("sobra" in v.lower() for v in textos.estabilizacao_por_divida.values())


def test_oq71_orientacao_em_dois_passos_na_ordem_e_aulas_do_curso() -> None:
    """`OQ-71` (`T-472`): reduzir gastos e depois renegociar, a mesma orientação
    em todos os casos; o quadro de aulas é o da dívida que cresce, só do curso."""
    textos = carregar_textos_canonicos()
    contexto = montar_contexto_plano(_com_divida_que_cresce(_snapshot()), textos)
    contexto = replace(contexto, maiores_gastos=(("Aluguel", "R$ 2.500,00"),))
    html = renderizar_html_do_plano(contexto, textos).replace("&#39;", "'")

    passo_1 = textos.estabilizacao_por_divida["passo_1"]
    passo_2 = textos.estabilizacao_por_divida["passo_2"]
    assert "O que fazer agora" in html
    assert 0 < html.index(passo_1) < html.index(passo_2)
    assert "aula 5" in passo_1 and "aulas 10 e 11" in passo_2
    assert "Onde olhar nos seus gastos" in html
    assert contexto.curso_ssd is not None
    assert [n for n, _, _ in contexto.curso_ssd.aulas] == ["5", "10", "14", "11"]


def test_oq71_deficit_continua_com_o_quadro_e_os_passos_do_deficitario() -> None:
    textos = carregar_textos_canonicos()
    contexto = montar_contexto_plano(_snapshot(renda=Decimal("1000.00")), textos)
    assert contexto.curso_ssd is not None
    assert [n for n, _, _ in contexto.curso_ssd.aulas] == ["5", "14", "24"]
    assert "Renegocie a dívida que mais cresce" not in renderizar_html_do_plano(contexto, textos)


def test_rf_480_resultado_negativo_continua_com_a_mensagem_do_deficitario() -> None:
    textos = carregar_textos_canonicos()
    snapshot = _snapshot(renda=Decimal("1000.00"))
    assert snapshot.diagnostico.MODO_ESTABILIZACAO
    contexto = montar_contexto_plano(snapshot, textos)
    assert contexto.ESTABILIZACAO_POR_DIVIDA is False
    assert contexto.dividas_que_crescem == ()
    assert "Primeiro, estancar o problema" in renderizar_html_do_plano(contexto, textos)


def test_rf_480_sem_estabilizacao_nada_muda() -> None:
    textos = carregar_textos_canonicos()
    contexto = montar_contexto_plano(_snapshot(), textos)
    assert contexto.ESTABILIZACAO_POR_DIVIDA is False
    assert contexto.FALTA_TOTAL_DE_JUROS == ""


def test_rf_79_fila_do_revisor_nao_chama_de_mes_negativo_o_mes_positivo() -> None:
    from app.revisao.lista_de_casos import _mes_negativo

    assert _mes_negativo(_com_divida_que_cresce(_snapshot())) is False
    assert _mes_negativo(_snapshot(renda=Decimal("1000.00"))) is True
    assert _mes_negativo(_snapshot()) is False


def test_rf_480_corpo_e_duvida_nao_falam_em_mes_negativo() -> None:
    textos = carregar_textos_canonicos()
    contexto = montar_contexto_plano(_com_divida_que_cresce(_snapshot()), textos)
    html = renderizar_html_do_plano(contexto, textos)
    assert "deixar de fechar no negativo" not in html
    assert "fechar com saldo positivo" not in html
    assert "cobrir o crescimento das dívidas" in contexto.corpo
    assert "cobrir o crescimento das dívidas" in contexto.duvidas[0][1]


def test_rf_481_ordem_do_relatorio_traz_as_quatro_dividas_e_marca_as_que_nao_quitam() -> None:
    from engine.motor import calcular_plano
    from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
    from tests.regras.test_ordem_com_todas_as_dividas import _caso_teste3

    snapshot = calcular_plano(_caso_teste3(), FonteParametrosArquivo().carregar("1.0.1"))
    textos = carregar_textos_canonicos()
    contexto = montar_contexto_plano(snapshot, textos)
    assert contexto.ESTABILIZACAO_POR_DIVIDA
    rotulo = textos.textos_das_dividas["fora_do_horizonte"]
    assert len(contexto.ordem) == 4
    assert [bool(p.fora_do_horizonte) for p in contexto.ordem] == [True, True, False, False]
    assert all(p.mes_de_quitacao is None for p in contexto.ordem[:2])
    html = renderizar_html_do_plano(contexto, textos)
    assert html.count(rotulo) == 2
