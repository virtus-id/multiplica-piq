"""Ordem provisória do plano deficitário — `RF-555`, `RF-556` (Rodada 17).

Na seção 3 do plano de quem fecha o mês no negativo (`MOTIVO_ESTABILIZACAO =
DEFICIT`), cada dívida traz a frase do `MOTIVO_POSICAO` que o motor publicou e
quando ela termina só com as parcelas (`sem_acao.QUITACOES_SO_PARCELAS`). A
aplicação só LÊ os dois campos (`AC-42`). Na estabilização por dívida que
cresce e no plano normal, nada muda (emenda de 2026-11-16, `EC-93`, `AC-591`).

Snapshots REAIS do motor: o caso do Rodrigo (`_estado_rodrigo`, de
`tests/regras/test_ordem_em_estabilizacao.py`), com os tipos das dívidas
definidos aqui para os nomes de `AC-586`.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from app.http.serializacao_plano import serializar_plano
from engine.estado import TIPO_DIVIDA
from engine.motor import calcular_plano
from engine.parametros import Parametros
from engine.snapshot import SnapshotOrdem
from engine.tipos import MOTIVO_POSICAO
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from report.pdf import renderizar_html_do_plano
from report.plano import (
    _MES_BASE,
    ContextoPlano,
    carregar_textos_canonicos,
    montar_contexto_plano,
    rotulo_do_mes,
)
from tests.regras.test_ordem_em_estabilizacao import _estado_rodrigo

_TEXTOS = carregar_textos_canonicos()
_E = _TEXTOS.estabilizacao
_NAO_SERA_QUITADA = _TEXTOS.textos_das_dividas["fora_do_horizonte"]
_RECEBE_EXTRA = _TEXTOS.textos_das_dividas["recebe_extra_rotulo"]


def _parametros() -> Parametros:
    return FonteParametrosArquivo().carregar("1.0.1")


def _rodrigo() -> SnapshotOrdem:
    """`AC-586`: o caso do Rodrigo, com financiamento imobiliário (D001) e
    consignado (D002) — os tipos não mexem na simulação (o digest de
    `RF-552` é o mesmo)."""
    estado = _estado_rodrigo()
    imobiliario, consignado = estado.dividas
    return calcular_plano(
        replace(
            estado,
            dividas=(
                replace(imobiliario, TIPO_DIVIDA=TIPO_DIVIDA.FIN_IMOBILIARIO),
                replace(consignado, TIPO_DIVIDA=TIPO_DIVIDA.CONSIGNADO),
            ),
        ),
        _parametros(),
    )


def _secao_3(html: str) -> str:
    """O trecho do HTML da "A ordem de quitação, por enquanto provisória"."""
    inicio = html.index(_E["ordem_titulo"])
    return html[inicio : html.index("</section>", inicio)]


def _html(contexto: ContextoPlano, *, previa: bool = False) -> str:
    return renderizar_html_do_plano(contexto, _TEXTOS, previa=previa).replace("&#39;", "'")


# --- T-628: AC-586 -----------------------------------------------------------


def test_ac586_caso_do_rodrigo_na_tela_no_pdf_e_na_previa() -> None:
    snapshot = _rodrigo()
    assert snapshot.prognostico is not None
    so_parcelas = dict(snapshot.prognostico.sem_acao.QUITACOES_SO_PARCELAS or ())
    # o mês de D001 é o do motor (`T-616`, `AC-585`)
    assert so_parcelas == {"D001": 118, "D002": 24}
    contexto = montar_contexto_plano(snapshot, _TEXTOS)
    esperado = [
        (
            "Financiamento imobiliário",
            _E["motivo_MAIOR_BENEFICIO_MARGINAL"],
            f"Termina em {rotulo_do_mes(118)}, se você mantiver as parcelas em dia.",
        ),
        (
            "Empréstimo consignado",
            _E["motivo_ULTIMA_RESTANTE"],
            f"Termina em {rotulo_do_mes(24)}, se você mantiver as parcelas em dia.",
        ),
    ]
    proibidas = (
        _E["motivo_PREFERENCIA_QUITACAO"],
        _E["motivo_DESEMPATE_PESO_EMOCIONAL"],
        _RECEBE_EXTRA,
        _NAO_SERA_QUITADA,
    )

    assert [(p.nome, p.motivo_da_posicao, p.previsao_so_parcelas) for p in contexto.ordem] == (
        esperado
    )
    assert all(p.fora_do_horizonte == "" for p in contexto.ordem)
    assert all(_RECEBE_EXTRA not in dict(p.fatos) for p in contexto.ordem)

    # tela do aluno e plano do aluno na conferência (`RF-121`)
    for para_revisor in (False, True):
        ordem = serializar_plano(contexto, textos=_TEXTOS, para_revisor=para_revisor)["ordem"]
        assert [
            (p["nome"], p["motivo_da_posicao"], p["previsao_so_parcelas"]) for p in ordem
        ] == esperado
        assert not any(frase in str(ordem) for frase in proibidas)

    # PDF liberado e prévia: mesma linha, nome → motivo → previsão
    for previa in (False, True):
        secao = _secao_3(_html(contexto, previa=previa))
        posicoes = [secao.index(texto) for linha in esperado for texto in linha]
        assert posicoes == sorted(posicoes)
        assert secao.count('<tr') == 3  # cabeçalho + duas dívidas
        assert not any(frase in secao for frase in proibidas)


# --- T-629: AC-588, AC-589, EC-92 --------------------------------------------


def _com_motivo(snapshot: SnapshotOrdem, motivo: MOTIVO_POSICAO) -> SnapshotOrdem:
    primeira, *demais = snapshot.ORDEM_QUITACAO
    return replace(snapshot, ORDEM_QUITACAO=(replace(primeira, MOTIVO_POSICAO=motivo), *demais))


@pytest.mark.parametrize("motivo", list(MOTIVO_POSICAO), ids=lambda m: m.value)
def test_ac588_cada_motivo_traz_exatamente_a_sua_frase(motivo: MOTIVO_POSICAO) -> None:
    frase = _E[f"motivo_{motivo.value}"]
    contexto = montar_contexto_plano(_com_motivo(_rodrigo(), motivo), _TEXTOS)

    assert contexto.ordem[0].motivo_da_posicao == frase
    assert frase in _secao_3(_html(contexto))


def test_ac588_todo_motivo_tem_frase_e_nenhuma_diz_sobra() -> None:
    chaves = {f"motivo_{m.value}" for m in MOTIVO_POSICAO}
    assert chaves <= set(_E)
    novas = [_E[c] for c in (*chaves, "previsao_termina", "previsao_nao_termina")]
    assert not any("sobra" in frase.lower() for frase in novas)


def test_ac588_preferencia_e_incomodo_so_aparecem_quando_decidiram() -> None:
    """D002 tem `PREFERENCIA_QUITACAO` e nota 10 de incômodo, mas o motivo da
    posição é outro: as frases de preferência e de incômodo não aparecem."""
    estado = _estado_rodrigo()
    imobiliario, consignado = estado.dividas
    snapshot = calcular_plano(
        replace(estado, dividas=(imobiliario, replace(consignado, PESO_EMOCIONAL=10))),
        _parametros(),
    )
    assert consignado.PREFERENCIA_QUITACAO
    assert [p.MOTIVO_POSICAO for p in snapshot.ORDEM_QUITACAO] == [
        MOTIVO_POSICAO.MAIOR_BENEFICIO_MARGINAL,
        MOTIVO_POSICAO.ULTIMA_RESTANTE,
    ]
    secao = _secao_3(_html(montar_contexto_plano(snapshot, _TEXTOS)))

    assert _E["motivo_PREFERENCIA_QUITACAO"] not in secao
    assert _E["motivo_DESEMPATE_PESO_EMOCIONAL"] not in secao
    assert _E["motivo_ULTIMA_RESTANTE"] in secao


def test_ac589_divida_fora_da_lista_nao_termina_e_nao_traz_mes() -> None:
    snapshot = _rodrigo()
    assert snapshot.prognostico is not None
    sem_acao = replace(snapshot.prognostico.sem_acao, QUITACOES_SO_PARCELAS=(("D002", 24),))
    snapshot = replace(snapshot, prognostico=replace(snapshot.prognostico, sem_acao=sem_acao))
    base = date(2026, 11, 16)

    imobiliario, consignado = montar_contexto_plano(snapshot, _TEXTOS, data_base=base).ordem

    assert imobiliario.previsao_so_parcelas == "Só com as parcelas de hoje, ela não termina."
    assert "Mês" not in imobiliario.previsao_so_parcelas
    assert not any(ch.isdigit() for ch in imobiliario.previsao_so_parcelas)
    # o mesmo rótulo do "Termina em" do plano normal, com a mesma data-base
    token = _MES_BASE.set(base)
    try:
        rotulo = rotulo_do_mes(24)
    finally:
        _MES_BASE.reset(token)
    assert consignado.previsao_so_parcelas == (
        f"Termina em {rotulo}, se você mantiver as parcelas em dia."
    )


def test_ec92_motivo_sem_frase_mostra_o_codigo() -> None:
    sem_a_frase = {
        k: v for k, v in _E.items() if k != "motivo_MAIOR_BENEFICIO_MARGINAL"
    }
    textos = replace(_TEXTOS, estabilizacao=sem_a_frase)

    contexto = montar_contexto_plano(_rodrigo(), textos)

    assert contexto.ordem[0].motivo_da_posicao == "MAIOR_BENEFICIO_MARGINAL"
    assert contexto.ordem[1].motivo_da_posicao == _E["motivo_ULTIMA_RESTANTE"]
