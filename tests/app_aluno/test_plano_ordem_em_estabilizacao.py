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

from app.http.serializacao_plano import serializar_plano
from engine.estado import TIPO_DIVIDA
from engine.motor import calcular_plano
from engine.parametros import Parametros
from engine.snapshot import SnapshotOrdem
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from report.pdf import renderizar_html_do_plano
from report.plano import (
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
