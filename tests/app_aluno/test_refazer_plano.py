"""`AC-181`, `AC-182`, `AC-183` — o aluno pedia um plano novo depois da
liberação (`RF-118`, `RF-119`, `T-341`). DESLIGADO em `T-387` (`RF-401`, `RF-409`):
o plano entregue é definitivo; as rotas e o Início recusam/escondem o pedido.

Pelas rotas reais (a mesma montagem de `test_correcao_pedida.py`, `AC-175`):
depois da liberação, `refazer-plano` recusa com `409`,
o caso fica em `PLANO_LIBERADO` e a v1 segue intacta. A v2 continua
nascendo pelo caminho de antes da entrega (`retomar-edicao`), visto do lado do
revisor em `AC-192`.

REGRAS: `RF-118`, `RF-119`, `AC-181`, `AC-182`, `AC-183`, `RF-401`, `RF-409`

No fim: a conferência do revisor sobre o plano liberado e sobre a v2 (`AC-189`,
`AC-192`, `T-345`) — o mesmo cenário, visto do lado de quem confere.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.casos.maquina import ESTADO_CASO
from app.http.rotas_api_plano import obter_emails_dos_alunos
from app.http.rotas_calculo import (
    obter_colecao_de_registros as calculo_colecao,
)
from app.http.rotas_calculo import (
    obter_repositorio_eventos,
)
from app.http.rotas_calculo import (
    obter_repositorio_itens as calculo_itens,
)
from app.http.rotas_calculo import (
    obter_repositorio_respostas as calculo_respostas,
)
from app.http.rotas_coleta import (
    obter_colecao_de_registros as coleta_colecao,
)
from app.http.rotas_coleta import (
    obter_repositorio_itens as coleta_itens,
)
from app.http.rotas_coleta import (
    obter_repositorio_respostas as coleta_respostas,
)
from app.http.rotas_plano import obter_contas_dos_casos
from app.http.rotas_respostas import obter_repositorio_eventos_da_retomada
from app.montagem.conversao import converter_para_taxa
from app.revisao.fila import liberar
from engine.estado import Divida
from persistencia.app_aluno.arquivo import RepositorioCasosArquivo
from tests.app_aluno.fixtures.caso_completo import CASO_ID
from tests.app_aluno.test_correcao_pedida import (
    Cenario,
    _caso,
    _esperar_sair_de_calculando,
    cenario,  # noqa: F401 — fixture reutilizada
)

_MENSAGEM_PLANO_DEFINITIVO = "O plano entregue é definitivo."


class _SemContas:
    def contas_dos_casos(self, caso_ids: tuple[str, ...]) -> dict[str, Any]:
        return {}


@pytest.fixture(autouse=True)
def _trilha_da_retomada(cenario: Cenario) -> None:  # noqa: F811
    """A rota grava o evento pela dependência da retomada; aqui ela aponta para a
    MESMA trilha em arquivo que o resto do cenário usa."""
    aplicacao: Any = cenario[0].app
    sobrescritas = aplicacao.dependency_overrides
    sobrescritas[obter_repositorio_eventos_da_retomada] = sobrescritas[obter_repositorio_eventos]
    # `GET /respostas` lê pelas dependências de `rotas_coleta`; o cenário sobrescreve
    # as de `rotas_calculo` — as mesmas instâncias, com outro nome de injeção.
    # O plano chama o aluno pelo nome (conta); aqui não há banco — sem nome.
    sobrescritas[obter_contas_dos_casos] = lambda: _SemContas()
    sobrescritas[obter_emails_dos_alunos] = lambda: SimpleNamespace(
        emails_dos_casos=lambda _ids: {}, contas_dos_casos=lambda _ids: {}
    )
    for da_coleta, do_calculo in (
        (coleta_respostas, calculo_respostas),
        (coleta_itens, calculo_itens),
        (coleta_colecao, calculo_colecao),
    ):
        sobrescritas[da_coleta] = sobrescritas[do_calculo]


def _liberar_v1(cliente: Any, casos: RepositorioCasosArquivo, cenario_: Cenario) -> None:
    """Calcula a v1 e a libera pela função de domínio (sem pendência de homologação:
    o que se prova aqui é o fluxo do aluno, não a homologação — `T-264`)."""
    _, _, snapshots, _, revisoes = cenario_
    aplicacao: Any = cliente.app
    assert cliente.post(f"/caso/{CASO_ID}/calculo").status_code == 200
    caso = _esperar_sair_de_calculando(casos)
    assert caso.snapshot_raiz_id is not None
    (v1,) = snapshots.historico(caso.snapshot_raiz_id)
    liberar(
        revisao_id="REVISAO-T341",
        caso_id=CASO_ID,
        snapshot=v1,
        autor="revisor-t341",
        decidido_em=datetime(2026, 10, 5, tzinfo=UTC),
        repositorio_revisoes=revisoes,
        repositorio_casos=casos,
        repositorio_eventos=aplicacao.dependency_overrides[obter_repositorio_eventos](),
        pendencias_homologacao=(),
    )


def _taxa_da_divida(snapshot: Any, divida_id: str) -> Any:
    divida: Divida = next(d for d in snapshot.estado_inputs.dividas if d.DIVIDA_ID == divida_id)
    return divida.TAXA_EFETIVA_MENSAL_NORMALIZADA


def test_ac181_plano_entregue_e_definitivo_nao_se_pede_plano_novo(
    cenario: Cenario,  # noqa: F811
) -> None:
    """`RF-409` (T-387) — antes (`AC-181`/`AC-183`) o pedido levava a
    `COLETA_INICIAL` e a v2 nascia encadeada; agora é `409` e nada muda."""
    cliente, casos, snapshots, respostas, _ = cenario
    with cliente:
        _liberar_v1(cliente, casos, cenario)
        liberado = _caso(casos)
        assert liberado.estado is ESTADO_CASO.PLANO_LIBERADO
        raiz = liberado.snapshot_raiz_id
        assert raiz is not None
        (v1,) = snapshots.historico(raiz)


        # O dado muda depois da liberação: o plano não.
        respostas.corrigir_no_item(
            "D001",
            {
                "TAXA_DIVIDA": converter_para_taxa("8"),
                "PERIODICIDADE_TAXA_DIVIDA": "MENSAL",
            },
        )

        pedido = cliente.post(f"/caso/{CASO_ID}/refazer-plano")

        assert pedido.status_code == 409
        assert pedido.json()["erro"] == _MENSAGEM_PLANO_DEFINITIVO
        assert _caso(casos) == liberado, "o caso não mudou"
        assert snapshots.historico(raiz) == (v1,), "nenhum plano novo"
        inicio = cliente.get(f"/caso/{CASO_ID}/inicio").json()
        assert inicio["plano_liberado"] is True
        assert inicio["fase"] == "plano"
        assert cliente.get(f"/caso/{CASO_ID}/api/plano").status_code == 200


@pytest.mark.parametrize(
    "estado", [ESTADO_CASO.COLETA_INICIAL, ESTADO_CASO.CALCULANDO, ESTADO_CASO.AGUARDANDO_REVISAO]
)
def test_ac182_antes_da_liberacao_pedir_plano_novo_e_recusado(
    cenario: Cenario,  # noqa: F811
    estado: ESTADO_CASO,
) -> None:
    cliente, casos, _, _, _ = cenario
    with cliente:
        if estado is not ESTADO_CASO.COLETA_INICIAL:
            casos.transicionar_estado(CASO_ID, ESTADO_CASO.CALCULANDO)
            if estado is ESTADO_CASO.AGUARDANDO_REVISAO:
                casos.transicionar_estado(CASO_ID, ESTADO_CASO.AGUARDANDO_REVISAO)

        resposta = cliente.post(f"/caso/{CASO_ID}/refazer-plano")

        assert resposta.status_code == 409
        assert resposta.json()["erro"] == _MENSAGEM_PLANO_DEFINITIVO
        assert _caso(casos).estado is estado


def test_etapas_pos_plano_nao_existem_mais(cenario: Cenario) -> None:  # noqa: F811
    """`RF-401`, `RF-409` (T-387, T-390) — depois da entrega não há rota de
    abertura de etapa nem do Bloco 10: o caso fica em `PLANO_LIBERADO`."""
    cliente, casos, _, _, _ = cenario
    with cliente:
        _liberar_v1(cliente, casos, cenario)
        for rota in ("etapas/blocos-7-8", "etapas/bloco-10", "etapas/bloco-11"):
            assert cliente.post(f"/caso/{CASO_ID}/{rota}").status_code in (404, 405), rota
        assert cliente.get(f"/caso/{CASO_ID}/bloco-10").status_code == 404
        assert cliente.get(f"/caso/{CASO_ID}/etapas").status_code == 404
        assert _caso(casos).estado is ESTADO_CASO.PLANO_LIBERADO


# --------------------------------------------------------------------------- AC-185 · AC-188


def test_ac185_plano_entregue_nao_afirma_mudanca_nem_oferece_plano_novo(
    cenario: Cenario,  # noqa: F811
) -> None:
    """`RF-409` (T-387) — com o plano definitivo não há plano novo a oferecer, e
    a comparação "respostas mudaram desde o plano" (`AC-185`) deixa de ser
    feita (`T-390` removeu o campo `respostas_atualizadas`) mesmo se a
    resposta mudar."""
    cliente, casos, _, respostas, _ = cenario
    with cliente:
        _liberar_v1(cliente, casos, cenario)

        inicio = cliente.get(f"/caso/{CASO_ID}/inicio").json()
        assert inicio["pode_retomar_edicao"] is False
        assert "respostas_atualizadas" not in inicio

        respostas.corrigir_no_item(
            "D001",
            {
                "TAXA_DIVIDA": converter_para_taxa("8"),
                "PERIODICIDADE_TAXA_DIVIDA": "MENSAL",
            },
        )
        inicio = cliente.get(f"/caso/{CASO_ID}/inicio").json()
        assert "respostas_atualizadas" not in inicio


def test_ac185_fora_do_plano_liberado_nao_afirma_nada(cenario: Cenario) -> None:  # noqa: F811
    cliente, casos, _, _, _ = cenario
    with cliente:
        inicio = cliente.get(f"/caso/{CASO_ID}/inicio").json()  # COLETA_INICIAL, sem plano
        assert "respostas_atualizadas" not in inicio
        assert inicio["pode_retomar_edicao"] is False

        casos.transicionar_estado(CASO_ID, ESTADO_CASO.CALCULANDO)
        casos.transicionar_estado(CASO_ID, ESTADO_CASO.AGUARDANDO_REVISAO)
        inicio = cliente.get(f"/caso/{CASO_ID}/inicio").json()
        assert inicio["pode_retomar_edicao"] is True  # `AC-187`
        assert "respostas_atualizadas" not in inicio


def test_ac188_se_a_comparacao_e_impossivel_o_inicio_responde_e_nao_afirma_mudanca(
    cenario: Cenario,  # noqa: F811
) -> None:
    cliente, casos, _, respostas, _ = cenario
    with cliente:
        _liberar_v1(cliente, casos, cenario)
        # Uma resposta sem a qual a montagem do cálculo recusa.
        respostas.respostas = [r for r in respostas.respostas if r.ID_PERGUNTA != "RENDA_PRINCIPAL"]

        resposta = cliente.get(f"/caso/{CASO_ID}/inicio")

        assert resposta.status_code == 200, "a falha da comparação nunca derruba o Início"
        corpo = resposta.json()
        assert "respostas_atualizadas" not in corpo


# --------------------------------------------------------------------------- AC-189 · AC-192


def _sem_extras_do_revisor(plano: dict[str, Any]) -> dict[str, Any]:
    """O plano do revisor sem o que só ele recebe (`para_revisor=True`)."""
    limpo = dict(plano)
    limpo["ordem"] = [
        {
            k: v
            for k, v in posicao.items()
            if k not in {"JUSTIFICATIVA_POSICAO", "fatos_de_risco"}
        }
        for posicao in plano["ordem"]
    ]
    limpo["acoes"] = [{k: v for k, v in a.items() if k != "motivo"} for a in plano["acoes"]]
    if plano["cenario_adicional"] is not None:
        itens = [
            {k: v for k, v in item.items() if k != "ITEM_ID"}
            for item in plano["cenario_adicional"]["itens"]
        ]
        limpo["cenario_adicional"] = {**plano["cenario_adicional"], "itens": itens}
    return limpo


def test_ac189_o_plano_do_revisor_e_o_do_aluno_mais_os_extras_dele(
    cenario: Cenario,  # noqa: F811
) -> None:
    cliente, casos, _, _, _ = cenario
    with cliente:
        _liberar_v1(cliente, casos, cenario)

        do_aluno = cliente.get(f"/caso/{CASO_ID}/api/plano").json()["plano"]
        do_revisor = cliente.get(f"/api/revisao/caso/{CASO_ID}").json()["plano"]

        # Os textos fixos que os componentes visuais do aluno precisam chegam ao revisor.
        textos_fixos = (
            "secoes",
            "resumo_textos",
            "grade_meses_textos",
            "duvidas",
            "sobre_este_plano",
        )
        for chave in textos_fixos:
            assert chave in do_revisor, chave
        # Campos comuns idênticos: nenhuma segunda redação.
        assert _sem_extras_do_revisor(do_revisor) == do_aluno
        # O que é só do revisor, só ele recebe.
        assert all("JUSTIFICATIVA_POSICAO" in p for p in do_revisor["ordem"])
        assert all("JUSTIFICATIVA_POSICAO" not in p for p in do_aluno["ordem"])


def test_ac192_o_revisor_ve_o_que_mudou_desde_a_versao_anterior(
    cenario: Cenario,  # noqa: F811
) -> None:
    cliente, casos, snapshots, respostas, _ = cenario
    with cliente:
        # v1 em conferência (`RF-409`: depois da entrega não há v2; a v2 nasce
        # quando o aluno retira o plano da conferência, `RF-115`).
        assert cliente.post(f"/caso/{CASO_ID}/calculo").status_code == 200
        assert _esperar_sair_de_calculando(casos).estado is ESTADO_CASO.AGUARDANDO_REVISAO
        # v1: nada com que comparar.
        assert cliente.get(f"/api/revisao/caso/{CASO_ID}").json()["mudancas"] is None

        respostas.corrigir_no_item(
            "D001",
            {
                "TAXA_DIVIDA": converter_para_taxa("8"),
                "PERIODICIDADE_TAXA_DIVIDA": "MENSAL",
            },
        )
        assert cliente.post(f"/caso/{CASO_ID}/retomar-edicao").status_code == 200
        assert cliente.post(f"/caso/{CASO_ID}/calculo").status_code == 200
        assert _esperar_sair_de_calculando(casos).estado is ESTADO_CASO.AGUARDANDO_REVISAO

        corpo = cliente.get(f"/api/revisao/caso/{CASO_ID}").json()
        mudancas = corpo["mudancas"]
        assert mudancas, "a taxa mudou: a lista não pode vir vazia"
        taxas = [m for m in mudancas if m["situacao"] == "alterado" and "axa" in m["nome"]]
        assert taxas, f"a taxa nova precisa aparecer: {mudancas}"
        assert all(m["de"] != m["para"] for m in mudancas if m["situacao"] == "alterado")
        # Campo igual não aparece: o número de mudanças é bem menor que o de campos.
        total_de_campos = len(corpo["estado_inputs"]["campos"]) + sum(
            len(d["campos"]) for d in corpo["estado_inputs"]["dividas"]
        )
        assert len(mudancas) < total_de_campos


# --------------------------------------------------------------------------- AC-193


def test_ac193_o_revisor_abre_a_previa_do_pdf_antes_da_liberacao(
    cenario: Cenario,  # noqa: F811
) -> None:
    cliente, casos, _, _, _ = cenario
    with cliente:
        assert cliente.post(f"/caso/{CASO_ID}/calculo").status_code == 200
        assert _esperar_sair_de_calculando(casos).estado is ESTADO_CASO.AGUARDANDO_REVISAO

        previa = cliente.get(f"/revisao/caso/{CASO_ID}/plano/pdf")
        assert previa.status_code == 200
        assert previa.headers["content-type"] == "application/pdf"
        assert previa.content.startswith(b"%PDF")

        # O PDF do ALUNO continua só do plano liberado (`AC-25`).
        assert cliente.get(f"/caso/{CASO_ID}/plano/pdf").status_code == 404


def test_ac193_a_faixa_de_previa_so_existe_no_html_da_previa(cenario: Cenario) -> None:  # noqa: F811
    from report.pdf import gerar_html_da_previa
    from report.plano import carregar_textos_canonicos

    cliente, casos, snapshots, _, _ = cenario
    with cliente:
        assert cliente.post(f"/caso/{CASO_ID}/calculo").status_code == 200
        caso = _esperar_sair_de_calculando(casos)
        assert caso.snapshot_raiz_id is not None
        (v1,) = snapshots.historico(caso.snapshot_raiz_id)

        html = gerar_html_da_previa(v1, carregar_textos_canonicos())

        assert "Prévia — ainda não liberado" in html
        assert html.index("Prévia — ainda não liberado") < html.index(v1.ENGINE_VERSION)

        # A montagem do plano liberado (o que o aluno recebe) nunca leva a faixa.
        from report.pdf import renderizar_html_do_plano
        from report.plano import montar_contexto_plano

        textos = carregar_textos_canonicos()
        do_aluno = renderizar_html_do_plano(montar_contexto_plano(v1, textos), textos)
        assert "Prévia — ainda não liberado" not in do_aluno


def test_ac193_sem_sessao_a_previa_nao_abre(cenario: Cenario) -> None:  # noqa: F811
    """A guarda de papel é a das outras rotas da equipe: sem sessão, `401`."""
    from fastapi.testclient import TestClient

    from app.http.aplicacao import criar_aplicacao

    anonimo = TestClient(criar_aplicacao(), base_url="https://teste.local")
    assert anonimo.get(f"/revisao/caso/{CASO_ID}/plano/pdf").status_code == 401


def test_ac193_caso_sem_snapshot_responde_404(cenario: Cenario) -> None:  # noqa: F811
    cliente, _, _, _, _ = cenario
    with cliente:
        assert cliente.get(f"/revisao/caso/{CASO_ID}/plano/pdf").status_code == 404
