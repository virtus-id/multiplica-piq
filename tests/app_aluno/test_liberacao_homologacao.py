"""Liberação recusada por pendência de homologação — `RF-92`, `RF-93`,
`RF-97` (`T-265`).

`AC-141`, `AC-142`, `AC-149`, `EC-40` pela rota REAL `POST /revisao/caso/
{id}/decisao` (a única rota de liberação) e pela função de domínio
`liberar`, com repositórios de arquivo (`T-24`) e snapshot REAL — mesmo
arranjo de `test_rotas_revisao_decisao.py`. As pendências são derivadas das
respostas gravadas, nunca fabricadas.

`T-266`: o contexto de `GET .../decisao` (fontes, divergências e
pendências), pela mesma rota.

`T-591`: liberar e homologar com a ordem ajustada pelo revisor (`RF-549`,
`AC-571`, `EC-83`), no fluxo de `test_rotas_ordem_do_revisor.py`.

REGRAS: `RF-92`, `RF-93`, `RF-97`, `AC-141`, `AC-142`, `AC-149`, `EC-40`,
`RF-549`, `AC-571`, `EC-83`
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.casos.maquina import ESTADO_CASO
from app.casos.progresso import pendencias_obrigatorias
from app.http.aplicacao import criar_aplicacao
from app.http.isolamento import exigir_papel_revisor
from app.http.rotas_revisao import (
    obter_repositorio_casos_da_fila,
    obter_repositorio_eventos_da_decisao,
    obter_repositorio_itens_da_revisao,
    obter_repositorio_respostas_da_revisao,
    obter_repositorio_revisoes_da_decisao,
    obter_repositorio_snapshots_da_fila,
)
from app.revisao.comprovacao import PendenciaHomologacao
from app.revisao.fila import ErroHomologacaoBloqueada, liberar
from collection.carga import carregar_registros
from collection.registro import EscopoRepeticao
from collection.respostas import NAO_SEI, Resposta, RespostasCaso
from persistencia.app_aluno.arquivo import (
    RepositorioCasosArquivo,
    RepositorioEventosCasoArquivo,
    RepositorioItensArquivo,
    RepositorioRespostasArquivo,
)
from persistencia.arquivo.repositorio_snapshots import RepositorioSnapshotsArquivo
from tests.app_aluno.fixtures.caso_completo import CASO_ID
from tests.app_aluno.test_rotas_ordem_do_revisor import (
    Cenario,
    cenario,  # noqa: F401 — fixture do fluxo de ajuste da ordem
)
from tests.app_aluno.test_rotas_revisao_decisao import (
    _calcular_snapshot,
    _criar_caso,
    _RepositorioRevisoesDublê,
)

_CASO = "CASO-HOMOLOGACAO"
_AGORA = datetime(2026, 9, 30, tzinfo=UTC)

# Os quatro dados que o motor lê, respondidos.
_DIVIDA_COMPLETA: dict[str, object] = {
    "SALDO_DEVEDOR_ATUAL": "5000",
    "PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)": "300",
    "PERIODICIDADE_TAXA_DIVIDA": "MENSAL",
    "TAXA_DIVIDA": "0.02",
}


class _Ambiente:
    def __init__(self, tmp_path: Path) -> None:
        self.casos = RepositorioCasosArquivo(tmp_path / "casos.jsonl")
        self.snapshots = RepositorioSnapshotsArquivo(tmp_path / "snapshots.jsonl")
        self.eventos = RepositorioEventosCasoArquivo(tmp_path / "eventos.jsonl")
        self.itens = RepositorioItensArquivo(tmp_path / "itens.jsonl")
        self.respostas = RepositorioRespostasArquivo(tmp_path / "respostas.jsonl")
        self.revisoes = _RepositorioRevisoesDublê()
        _criar_caso(self.casos, _CASO, "conta-aluno-homologacao")
        self.snapshot = _calcular_snapshot(_CASO, self.casos, self.snapshots, self.eventos)
        self.divida = self.itens.proximo_identificador(_CASO, EscopoRepeticao.DIVIDA_ID)
        self.responder("RENDA_PRINCIPAL", Decimal("8000"))

    def responder(self, variavel: str, valor: object, item_id: str | None = None) -> None:
        self.respostas.gravar(
            Resposta(
                CASO_ID=_CASO,
                ID_PERGUNTA=variavel,
                item_id=item_id,
                valor=valor,  # type: ignore[arg-type]
                QUESTIONARIO_VERSION="1.0.3",
                respondida_em=_AGORA,
            )
        )

    def responder_divida(self, **mudancas: object) -> None:
        for variavel, valor in {**_DIVIDA_COMPLETA, **mudancas}.items():
            if valor is not None:  # `None` em `mudancas`: a resposta não é dada
                self.responder(variavel, valor, self.divida)

    def cliente(self, monkeypatch: pytest.MonkeyPatch) -> TestClient:
        monkeypatch.setenv("CHAVE_ASSINATURA_SESSAO", "chave-de-teste-t265-nao-usar-em-producao")
        aplicacao = criar_aplicacao()
        sobrescritas: dict[Callable[..., object], object] = {
            obter_repositorio_casos_da_fila: self.casos,
            obter_repositorio_snapshots_da_fila: self.snapshots,
            obter_repositorio_revisoes_da_decisao: self.revisoes,
            obter_repositorio_eventos_da_decisao: self.eventos,
            obter_repositorio_respostas_da_revisao: self.respostas,
            obter_repositorio_itens_da_revisao: self.itens,
            exigir_papel_revisor: "conta-revisor-t265",
        }
        for dependencia, valor in sobrescritas.items():
            aplicacao.dependency_overrides[dependencia] = _constante(valor)
        return TestClient(aplicacao, base_url="https://teste.local")

    def liberar_pela_rota(self, monkeypatch: pytest.MonkeyPatch) -> tuple[int, dict[str, object]]:
        resposta = self.cliente(monkeypatch).post(
            f"/revisao/caso/{_CASO}/decisao",
            content="decisao=LIBERAR",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        return resposta.status_code, resposta.json()


def _constante(valor: object) -> Callable[[], object]:
    """Sem parâmetro: o FastAPI leria `lambda v=valor` como query e copiaria
    o padrão."""
    return lambda: valor


@pytest.fixture
def ambiente(tmp_path: Path) -> _Ambiente:
    return _Ambiente(tmp_path)


def _assert_nada_gravado(ambiente: _Ambiente, eventos_antes: int) -> None:
    caso = ambiente.casos.buscar(_CASO)
    assert caso is not None
    assert caso.estado is ESTADO_CASO.AGUARDANDO_REVISAO
    assert caso.snapshot_liberado_id is None
    assert ambiente.revisoes.registros == {}
    assert len(ambiente.eventos.listar_do_caso(_CASO)) == eventos_antes
    historico = ambiente.snapshots.historico(ambiente.snapshot.SNAPSHOT_ID)
    assert [s.SNAPSHOT_ID for s in historico] == [ambiente.snapshot.SNAPSHOT_ID]


def test_ac142_ec40_funcao_de_dominio_recusa_antes_de_gravar(ambiente: _Ambiente) -> None:
    eventos_antes = len(ambiente.eventos.listar_do_caso(_CASO))
    pendencia = PendenciaHomologacao(ambiente.divida, "B5.B03", "PENDENTE_DE_CONFIRMACAO")

    with pytest.raises(ErroHomologacaoBloqueada) as erro:
        liberar(
            revisao_id="REVISAO_T265",
            caso_id=_CASO,
            snapshot=ambiente.snapshot,
            autor="conta-revisor-t265",
            decidido_em=_AGORA,
            repositorio_revisoes=ambiente.revisoes,
            repositorio_casos=ambiente.casos,
            repositorio_eventos=ambiente.eventos,
            pendencias_homologacao=(pendencia,),
        )

    assert erro.value.pendencias == (pendencia,)
    _assert_nada_gravado(ambiente, eventos_antes)


def test_reprovar_continua_possivel_com_pendencia(
    ambiente: _Ambiente, monkeypatch: pytest.MonkeyPatch
) -> None:
    ambiente.responder_divida(SALDO_DEVEDOR_ATUAL=NAO_SEI)

    resposta = ambiente.cliente(monkeypatch).post(
        f"/revisao/caso/{_CASO}/decisao",
        content="decisao=REPROVAR&mensagem_aluno=Confira",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert resposta.status_code == 200


def test_ac149_saldo_nao_sei_calculo_roda_e_plano_parcial_e_liberado(
    ambiente: _Ambiente, monkeypatch: pytest.MonkeyPatch
) -> None:
    ambiente.responder_divida(SALDO_DEVEDOR_ATUAL=NAO_SEI)
    registros = carregar_registros().registros
    respostas = RespostasCaso(respostas=ambiente.respostas.listar_do_caso(_CASO))
    itens = {EscopoRepeticao.DIVIDA_ID: (ambiente.divida,)}

    # O cálculo não é barrado: "não sei" é resposta (RF-11), nenhuma
    # pendência obrigatória nasce do saldo desconhecido.
    assert not any(p.ID == "B5.B03" for p in pendencias_obrigatorias(registros, respostas, itens))

    # `OQ-89` (especialista, 2026-11-06): a dívida com saldo "não sei" fica
    # fora do plano e é apontada ao aluno; o plano parcial é liberado.
    status, _ = ambiente.liberar_pela_rota(monkeypatch)

    assert status == 200


def test_t393_sem_o_custo_da_divida_o_calculo_bloqueia_e_a_liberacao_tambem(
    ambiente: _Ambiente, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`T-393`: `B5.D06` é `OBR` + `REP` e indispensável. Sem resposta, a
    varredura do Bloco 6 (`pendencias_obrigatorias`) a lista, impedindo o
    cálculo; a liberação também recusa (`AUSENTE`). Respondida, libera."""
    ambiente.responder_divida(PERIODICIDADE_TAXA_DIVIDA=None)
    registros = carregar_registros().registros
    respostas = RespostasCaso(respostas=ambiente.respostas.listar_do_caso(_CASO))
    itens = {EscopoRepeticao.DIVIDA_ID: (ambiente.divida,)}

    assert [
        (p.ID, p.item_id)
        for p in pendencias_obrigatorias(registros, respostas, itens)
        if p.ID == "B5.D06"
    ] == [("B5.D06", ambiente.divida)]
    status, corpo = ambiente.liberar_pela_rota(monkeypatch)
    assert status == 409
    assert [(p["ID_PERGUNTA"], p["motivo"]) for p in corpo["pendencias_homologacao"]] == [  # type: ignore[attr-defined]
        ("B5.D06", "AUSENTE")
    ]

    ambiente.responder("PERIODICIDADE_TAXA_DIVIDA", "MENSAL", ambiente.divida)

    assert ambiente.liberar_pela_rota(monkeypatch)[0] == 200


# --------------------------------------------------------------------------
# `T-591` (`RF-549`) — liberar e homologar com a ordem ajustada pelo revisor.
# O fluxo pelas rotas reais de `test_rotas_ordem_do_revisor.py`.
# --------------------------------------------------------------------------

_LISTA = ["D003", "D001", "D002"]


def _caminho(plano: dict[str, Any], cor: str) -> dict[str, Any]:
    caminho: dict[str, Any] = next(
        c for c in plano["prognostico"]["caminhos"] if c["cor"] == cor
    )
    return caminho


def _homologacao(no_cenario: Cenario) -> dict[str, Any]:
    corpo: dict[str, Any] = no_cenario.revisor.get(f"/revisao/caso/{CASO_ID}/decisao").json()
    return corpo


def test_ac571_liberar_a_v2_ajustada_entrega_ao_aluno_a_ordem_do_revisor(
    cenario: Cenario,  # noqa: F811
) -> None:
    v1 = cenario.enviar()
    plano_v1 = cenario.revisor.get(f"/api/revisao/caso/{CASO_ID}").json()["plano"]
    nomes = {p["DIVIDA_ID"]: p["nome"] for p in plano_v1["ordem"]}
    assert cenario.ajustar(_LISTA).status_code == 200
    v2 = cenario.historico()[-1]
    itens = _homologacao(cenario)["homologacao"]["itens"]
    assert itens["ordem_final_de_ataque"]["valor"] == [
        f"{i}º {nomes[p.DIVIDA_ID]}" for i, p in enumerate(v2.ORDEM_QUITACAO, start=1)
    ]

    assert cenario.decidir("decisao=LIBERAR").status_code == 200

    assert cenario.caso().snapshot_liberado_id == v2.SNAPSHOT_ID
    plano = cenario.aluno.get(f"/caso/{CASO_ID}/api/plano").json()["plano"]
    cenario_v2 = v2.cenarios[v2.METODO_RECOMENDADO_PIQ]
    assert [p["DIVIDA_ID"] for p in plano["ordem"]] == [p.DIVIDA_ID for p in v2.ORDEM_QUITACAO]
    assert {nomes[p["DIVIDA_ID"]]: p["mes_de_quitacao"] for p in plano["ordem"]} == itens[
        "mes_de_quitacao_por_divida"
    ]["valor"]
    assert plano["PRAZO_TOTAL_INT"] == cenario_v2.PRAZO_TOTAL
    assert v2.prognostico is not None and v1.prognostico is not None
    assert v2.prognostico.MESES_DO_PLANO[0].DIVIDA_ALVO == _LISTA[0]
    assert _caminho(plano, "azul")["mes_fim"] == cenario_v2.PRAZO_TOTAL
    assert (v2.prognostico.com_extra is None) == (v1.prognostico.com_extra is None)
    # "Se nada mudar" é o da v1: o ajuste não muda o vermelho.
    assert v2.prognostico.sem_acao == v1.prognostico.sem_acao
    vermelho_v1, vermelho = _caminho(plano_v1, "vermelho"), _caminho(plano, "vermelho")
    assert (vermelho["mes_fim"], vermelho["destaques"][0]) == (
        vermelho_v1["mes_fim"],
        vermelho_v1["destaques"][0],
    )


def test_rf549_pendencias_de_homologacao_nao_mudam_com_o_ajuste(
    cenario: Cenario,  # noqa: F811
) -> None:
    """As pendências saem das respostas (`RF-93`, `RF-97`), que o ajuste não
    toca; a homologação passa a recair sobre o snapshot ajustado."""
    v1 = cenario.enviar()
    antes = _homologacao(cenario)
    assert antes["SNAPSHOT_ID"] == v1.SNAPSHOT_ID

    assert cenario.ajustar(_LISTA).status_code == 200

    depois = _homologacao(cenario)
    assert depois["SNAPSHOT_ID"] == cenario.historico()[-1].SNAPSHOT_ID
    assert depois["pendencias_homologacao"] == antes["pendencias_homologacao"]
    assert depois["homologacao"]["homologavel"] == antes["homologacao"]["homologavel"]


def test_ec83_liberar_depois_do_ajuste_libera_o_mais_recente(
    cenario: Cenario,  # noqa: F811
) -> None:
    v1 = cenario.enviar()
    # A outra aba ainda mostra a v1.
    assert _homologacao(cenario)["SNAPSHOT_ID"] == v1.SNAPSHOT_ID
    assert cenario.ajustar(_LISTA).status_code == 200

    assert cenario.decidir("decisao=LIBERAR").status_code == 200

    v2 = cenario.historico()[-1]
    assert v2.ORDEM_DO_REVISOR == tuple(_LISTA)
    assert cenario.caso().snapshot_liberado_id == v2.SNAPSHOT_ID
    assert (cenario.revisoes.registros[-1].SNAPSHOT_ID) == v2.SNAPSHOT_ID
