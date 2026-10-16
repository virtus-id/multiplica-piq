"""`T-352` a `T-354` — sobra zero, curso de entrada (Servidor Sem Dívidas) e
nota de incômodo no plano.

Os snapshots vêm do motor REAL (`calcular_plano` sobre os parâmetros de
`parameters/`), como em `test_plano_reserva_mobilizavel.py`: o contexto lê o
snapshot, e nenhuma regra de ordem muda (o motor não é tocado).

REGRAS: pedido do responsável do produto (2026-10-05); `GAB-04` (a palavra
"sobra" não aparece em plano de estabilização).
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

from app.montagem.conversao import converter_para_dinheiro
from app.montagem.estado import montar_divida, montar_estado_financeiro
from collection.respostas import RespostasCaso
from engine.motor import calcular_plano
from engine.snapshot import SnapshotOrdem
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from report.pdf import renderizar_html_do_plano
from report.plano import (
    ContextoPlano,
    VocabularioDoCaso,
    carregar_textos_canonicos,
    formatar_dinheiro_br,
    montar_contexto_plano,
)
from tests.app_aluno.fixtures.caso_completo import (
    DATA_REFERENCIA,
    caso_completo,
    montar_respostas_caso,
    sem_o_custo_da_divida,
)

_PARAMETROS_VERSAO = "1.0.1"
_ESTRUTURA_DO_CURSO = Path("docs/curso-ssd/estrutura.md")


def _snapshot(renda: Decimal | None = None, peso_b: int | None = None) -> SnapshotOrdem:
    """Duas dívidas (a segunda com a nota de incômodo pedida); `renda`
    sobrescreve `RENDA_PRINCIPAL`."""
    valores: dict[str, object] = {} if renda is None else {"RENDA_PRINCIPAL": renda}
    caso_a = caso_completo(
        DIVIDA_ID="D-A", valores_caso=valores, valores_divida={"TAXA_DIVIDA": Decimal("0.05")}
    )
    divida_b: dict[str, object] = {
        "TIPO_DIVIDA": "CONSIGNADO",
        "SALDO_DEVEDOR_ATUAL": converter_para_dinheiro("8.000,00"),
        "PAGAMENTO_MENSAL_EFETIVO": converter_para_dinheiro("400,00"),
    }
    if peso_b is not None:
        divida_b["PESO_EMOCIONAL"] = peso_b
    respostas_b = montar_respostas_caso(
        valores_caso=valores, valores_divida=divida_b, DIVIDA_ID="D-B"
    )
    # `T-393`: a segunda dívida sem o custo mantém o plano provisório ("O que
    # falta informar"); o rotativo (D-A, 5% a.m.) vem primeiro, pelo custo.
    respostas = sem_o_custo_da_divida(
        RespostasCaso(respostas=caso_a.respostas.respostas + respostas_b.respostas), "D-B"
    )
    estado = montar_estado_financeiro(
        respostas,
        DATA_REFERENCIA=DATA_REFERENCIA,
        dividas=(montar_divida(respostas, "D-A"), montar_divida(respostas, "D-B")),
        **caso_a.parametros_externos,  # type: ignore[arg-type]
    )
    return calcular_plano(estado, FonteParametrosArquivo().carregar(_PARAMETROS_VERSAO))


def _contexto(snapshot: SnapshotOrdem) -> ContextoPlano:
    return montar_contexto_plano(snapshot, carregar_textos_canonicos())


def _html(snapshot: SnapshotOrdem) -> str:
    textos = carregar_textos_canonicos()
    return renderizar_html_do_plano(montar_contexto_plano(snapshot, textos), textos)


def _renda_para_resultado(resultado_desejado: Decimal) -> Decimal:
    """A renda que faz o resultado do mês valer `resultado_desejado`: parte
    do resultado do caso-base e ajusta a renda pela diferença (preparação do
    TESTE, não código de produção)."""
    base = _snapshot()
    resultado = base.diagnostico.RESULTADO_MENSAL_ATUAL
    assert isinstance(resultado, Decimal)
    return Decimal("8000.00") + (resultado_desejado - resultado)


# ---------------------------------------------------------------- sobra zero


def test_sobra_exatamente_zero_gera_plano_normal_sem_valor_extra() -> None:
    snapshot = _snapshot(renda=_renda_para_resultado(Decimal("0")))
    assert snapshot.diagnostico.RESULTADO_MENSAL_ATUAL == Decimal("0")
    contexto = _contexto(snapshot)

    assert contexto.MODO_ESTABILIZACAO is False
    assert contexto.cenario.value == "NORMAL"
    assert contexto.aviso_sem_valor_extra
    assert contexto.aviso_sem_valor_extra in _html(snapshot)


def test_aviso_de_sem_valor_extra_nao_aparece_quando_ha_valor_extra() -> None:
    snapshot = _snapshot()
    assert _contexto(snapshot).aviso_sem_valor_extra == ""


def test_numeros_do_mes_no_negativo_fecham_entre_si() -> None:
    """RF-416/RF-419 — no mês negativo o resultado exibido é o estrutural
    (`RESULTADO_MENSAL_ATUAL`) e as parcelas exibidas são as devidas:
    renda − gastos − gastos ocasionais − parcelas = resultado, e o corte
    mostrado (`DEFICIT_MENSAL`) é o oposto desse resultado."""
    snapshot = _snapshot(renda=Decimal("1000.00"))
    d, e = snapshot.diagnostico, snapshot.estado_inputs
    assert d.RESULTADO_MENSAL_ATUAL < 0 and d.MODO_ESTABILIZACAO
    contexto = _contexto(snapshot)
    ponto = contexto.ponto_de_partida
    assert ponto is not None
    assert ponto.parcelas == formatar_dinheiro_br(d.PAGAMENTOS_MENSAIS_DEVIDOS_VIGENTES)
    assert d.RESULTADO_MENSAL_ATUAL == (
        e.RENDA_TOTAL_RECORRENTE
        - e.DESPESAS_OPERACIONAIS_ATUAIS
        - e.DESPESAS_NAO_MENSAIS_NORMALIZADAS
        - d.PAGAMENTOS_MENSAIS_DEVIDOS_VIGENTES
    )
    assert d.DEFICIT_MENSAL == -d.RESULTADO_MENSAL_ATUAL
    assert contexto.RESULTADO_CAIXA_OBSERVADO == formatar_dinheiro_br(d.RESULTADO_MENSAL_ATUAL)
    assert contexto.FALTA_CORTAR == formatar_dinheiro_br(d.DEFICIT_MENSAL)
    html = _html(snapshot)
    assert formatar_dinheiro_br(d.RESULTADO_MENSAL_ATUAL) in html
    assert formatar_dinheiro_br(d.DEFICIT_MENSAL) in html


def test_estabilizacao_mostra_avisos_de_atraso_e_garantia_com_responsabilidade() -> None:
    """RF-416 — mês no negativo não tem cartão por dívida, mas o aluno ainda
    vê o que declarou em `B5.E01` e `B5.F01`, sem cronograma."""
    snapshot = _snapshot(renda=Decimal("1000.00"))
    assert snapshot.diagnostico.MODO_ESTABILIZACAO
    vocabulario = VocabularioDoCaso(
        dividas_atrasadas=frozenset({"D-A"}), dividas_com_garantia=frozenset({"D-B"})
    )
    textos = carregar_textos_canonicos()
    contexto = montar_contexto_plano(snapshot, textos, vocabulario)
    responsabilidade = textos.avisos["responsabilidade"]
    atrasada = [a for a in contexto.avisos_gerais if textos.avisos["atrasada"] in a]
    garantia = [a for a in contexto.avisos_gerais if textos.avisos["garantia"] in a]
    assert len(atrasada) == 1 and len(garantia) == 1
    assert all(a.endswith(responsabilidade) for a in atrasada + garantia)
    html = renderizar_html_do_plano(contexto, textos)
    assert textos.avisos["atrasada"] in html and textos.avisos["garantia"] in html
    # fora da estabilização os avisos seguem no cartão da dívida, não aqui
    normal = montar_contexto_plano(_snapshot(), textos, vocabulario)
    assert normal.avisos_gerais == ()


# --------------------------------------------------------------------- curso


def test_toda_aula_do_quadro_existe_na_estrutura_do_curso() -> None:
    estrutura = _ESTRUTURA_DO_CURSO.read_text(encoding="utf-8")
    numeros_do_curso = set(re.findall(r"^(\d+)\. ", estrutura, flags=re.MULTILINE))
    bruto = carregar_textos_canonicos().curso_ssd
    aulas = {str(n) for n in bruto["aulas"]}
    usadas = {str(n) for quadro in bruto["quadro_por_cenario"].values() for n in quadro}
    assert aulas <= numeros_do_curso
    assert usadas <= aulas


def test_plano_normal_traz_introducao_e_aulas_dos_metodos() -> None:
    contexto = _contexto(_snapshot())
    curso = contexto.curso_ssd
    assert curso is not None
    assert "Servidor Sem Dívidas" in curso.introducao
    assert "12" in {numero for numero, _, _ in curso.aulas}
    html = _html(_snapshot())
    assert curso.introducao in html
    assert "Aula 12" in html


def test_plano_de_estabilizacao_indica_as_aulas_de_gastos_e_renda_sem_a_palavra_sobra() -> None:
    snapshot = _snapshot(renda=_renda_para_resultado(Decimal("-500")))
    contexto = _contexto(snapshot)
    assert contexto.MODO_ESTABILIZACAO is True
    assert contexto.curso_ssd is not None
    assert {numero for numero, _, _ in contexto.curso_ssd.aulas} == {"5", "6", "19"}
    assert "sobra" not in _html(snapshot).lower()


# ------------------------------------------------------------------ incômodo


def test_nota_alta_em_divida_fora_do_topo_recebe_a_linha_e_o_aviso() -> None:
    contexto = _contexto(_snapshot(peso_b=9))
    por_id = {posicao.DIVIDA_ID: posicao for posicao in contexto.ordem}
    divida_b = por_id["D-B"]
    assert divida_b.indice > 1  # o cartão rotativo vem primeiro, pelo custo
    assert "nota 9" in divida_b.incomodo
    assert divida_b.aviso_incomodo
    assert por_id["D-A"].aviso_incomodo == ""


def test_nota_baixa_nao_gera_aviso() -> None:
    contexto = _contexto(_snapshot(peso_b=5))
    assert all(posicao.aviso_incomodo == "" for posicao in contexto.ordem)
    assert any("nota 5" in posicao.incomodo for posicao in contexto.ordem)


# ------------------------------------------------------------- ordem dos capítulos


def test_capitulos_do_pdf_seguem_a_ordem_definida_pelo_produto() -> None:
    """Ordem do produto (2026-10-07): dívidas, ponto de partida, reserva, como
    funciona, plano em números (linhas, mês a mês e quando cada dívida termina),
    plano detalhado (mural), mês a mês em detalhe, pendências, curso e perguntas frequentes."""
    html = _html(_snapshot())
    titulos = re.findall(
        r'<span class="secao-numero">(\d+)</span>\s*<h2[^>]*>([^<]*)</h2>', html
    )
    assert titulos == [
        ("1", "Suas dívidas, uma a uma"),
        ("2", "Seu ponto de partida"),
        ("3", "Sua reserva"),
        ("4", "Como o seu plano funciona"),
        ("5", "Seu plano em números"),
        ("6", "Seu plano detalhado"),
        ("7", "Mês a mês, em detalhe"),
        ("8", "O que falta informar"),
        ("9", "O curso Servidor Sem Dívidas e o seu plano"),
        ("10", "Perguntas frequentes"),
    ]


def test_primeira_pagina_apresenta_o_plano_antes_do_primeiro_capitulo() -> None:
    html = _html(_snapshot())
    apresentacao = _contexto(_snapshot()).curso_ssd
    assert apresentacao is not None and apresentacao.apresentacao
    assert html.index(apresentacao.apresentacao_titulo) < html.index("Seu plano em números")
    assert all(paragrafo in html for paragrafo in apresentacao.apresentacao)


def test_ponto_de_partida_marca_entrada_e_saida_com_cor_e_sinal() -> None:
    html = _html(_snapshot())
    textos = carregar_textos_canonicos().ponto_de_partida
    marcadas = re.findall(
        r'<div class="linha (entrada|saida)"><span class="linha-rotulo">([^<]*)</span>', html
    )
    assert marcadas == [
        ("entrada", textos["renda"]),
        ("saida", textos["gastos"]),
        ("saida", textos["gastos_ocasionais"]),
        ("saida", textos["parcelas"]),
    ]
    assert html.count('class="linha-sinal"') == 4
    assert html.count(">+</span>") == 1 and html.count("&minus;</span>") == 3


def test_nenhum_texto_de_decisao_manda_o_aluno_acionar_a_equipe() -> None:
    """Pedido do produto (2026-10-06): as perguntas frequentes têm resposta
    fechada e o aluno decide o que fazer; nenhuma resposta, nem o aviso de
    incômodo, manda "avisar" ou "informar" a equipe."""
    textos = carregar_textos_canonicos()
    respostas = [resposta for _, resposta in textos.duvidas]
    outros = [textos.incomodo.get("aviso", ""), textos.sem_valor_extra]
    outros.append(str(textos.curso_ssd.get("melhorar_intro", "")))
    for texto in respostas + outros:
        assert "equipe" not in texto.lower()
