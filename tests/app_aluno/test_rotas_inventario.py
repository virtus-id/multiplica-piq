"""`GET /caso/{CASO_ID}/inventario` e a etapa do Início — `RF-86`,
`AC-133`, `AC-03` (`T-250`, `T-251`).

Mesmos dublês de `tests/app_aluno/test_rotas_inicio.py`, pela mesma
aplicação real e os mesmos pontos de injeção (`app.dependency_overrides`).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.casos.maquina import ESTADO_CASO
from app.http.aplicacao import criar_aplicacao
from app.http.isolamento import obter_repositorio_casos
from app.http.rotas_inventario import (
    obter_colecao_de_registros_do_inventario,
    obter_repositorio_itens_do_inventario,
    obter_repositorio_respostas_do_inventario,
)
from app.http.sessao import iniciar_sessao_conta
from collection.registro import EscopoRepeticao
from collection.respostas import Resposta
from persistencia.app_aluno.itens import ItemRepetido
from tests.app_aluno.test_rotas_inicio import (
    _CASO_ALHEIO,
    _CASO_ID,
    _CHAVE_TESTE,
    _CONTA_ALHEIA,
    _CONTA_DONA,
    _caso,
    _colecao_real,
    _RepositorioCasosDublê,
    _RepositorioItensDublê,
    _RepositorioRespostasDublê,
)


def _resposta(variavel: str, valor: object, item_id: str | None = None) -> Resposta:
    return Resposta(
        CASO_ID=_CASO_ID,
        ID_PERGUNTA=variavel,
        item_id=item_id,
        valor=valor,  # type: ignore[arg-type]
        QUESTIONARIO_VERSION="1.0.0",
        respondida_em=datetime(2026, 9, 30, tzinfo=UTC),
    )


def _cliente(
    monkeypatch: pytest.MonkeyPatch,
    respostas: tuple[Resposta, ...],
    itens: tuple[ItemRepetido, ...] = (),
    conta: str | None = _CONTA_DONA,
) -> TestClient:
    monkeypatch.setenv("CHAVE_ASSINATURA_SESSAO", _CHAVE_TESTE)
    aplicacao = criar_aplicacao()
    casos = (
        _caso(ESTADO_CASO.COLETA_INICIAL),
        _caso(ESTADO_CASO.COLETA_INICIAL, CASO_ID=_CASO_ALHEIO, conta_id=_CONTA_ALHEIA),
    )
    aplicacao.dependency_overrides[obter_repositorio_casos] = lambda: _RepositorioCasosDublê(casos)
    aplicacao.dependency_overrides[obter_colecao_de_registros_do_inventario] = _colecao_real
    aplicacao.dependency_overrides[obter_repositorio_respostas_do_inventario] = (
        lambda: _RepositorioRespostasDublê(respostas)
    )
    aplicacao.dependency_overrides[obter_repositorio_itens_do_inventario] = (
        lambda: _RepositorioItensDublê(itens)
    )

    @aplicacao.post("/_teste/abrir-sessao/{conta_id}")
    def abrir_sessao(conta_id: str, request: Request) -> dict[str, str]:
        iniciar_sessao_conta(request, conta_id=conta_id)
        return {"conta_id": conta_id}

    cliente = TestClient(aplicacao, base_url="https://teste.local")
    if conta is not None:
        cliente.post(f"/_teste/abrir-sessao/{conta}")
    return cliente


def _ficha(item_id: str) -> ItemRepetido:
    return ItemRepetido(
        item_id=item_id,
        CASO_ID=_CASO_ID,
        escopo=EscopoRepeticao.DIVIDA_ID,
        removido_em=None,
        criado_em=datetime(2026, 9, 30, tzinfo=UTC),
    )


def test_ac595_zero_fichas_devolve_sem_dividas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`AC-595`, `RF-559`: nenhuma ficha de `DIVIDA_ID` — só `SEM_DIVIDAS`,
    com `ID_PARA_CORRIGIR` nulo (não há mais pergunta de quantidade a
    corrigir) e mensagem sem menção a "quantidade"."""
    resposta = _cliente(monkeypatch, ()).get(f"/caso/{_CASO_ID}/inventario")

    assert resposta.status_code == 200
    (pendencia,) = resposta.json()["pendencias"]
    assert pendencia["tipo"] == "INVENTARIO"
    assert pendencia["codigo"] == "SEM_DIVIDAS"
    assert pendencia["ID_PARA_CORRIGIR"] is None
    assert pendencia["escopo"] == "DIVIDA_ID"
    assert "quantidade" not in pendencia["mensagem"]


def test_ac595_ficha_criada_e_vazia_nao_conta_como_cadastrada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ficha criada sem nenhuma resposta não "cadastra" — `SEM_DIVIDAS`
    persiste."""
    resposta = _cliente(monkeypatch, (), (_ficha("D001"),)).get(f"/caso/{_CASO_ID}/inventario")

    (pendencia,) = resposta.json()["pendencias"]
    assert pendencia["codigo"] == "SEM_DIVIDAS"


def test_ac596_inventario_completo_devolve_lista_vazia(monkeypatch: pytest.MonkeyPatch) -> None:
    """`AC-596`: uma ficha com ao menos uma resposta não bloqueia mais."""
    respostas = (_resposta("TIPO_DIVIDA", "PESSOAL", item_id="D001"),)

    resposta = _cliente(monkeypatch, respostas, (_ficha("D001"),)).get(
        f"/caso/{_CASO_ID}/inventario"
    )

    assert resposta.json() == {"pendencias": []}


def test_ec97_sem_nenhuma_ficha_o_calculo_fica_bloqueado(monkeypatch: pytest.MonkeyPatch) -> None:
    """`EC-97`: sem nenhuma ficha de dívida, o cálculo fica bloqueado por
    `SEM_DIVIDAS`; não há opção "não tenho dívida" na resposta — só a
    orientação de cadastrar uma ficha (`escopo`)."""
    (pendencia,) = _cliente(monkeypatch, ()).get(f"/caso/{_CASO_ID}/inventario").json()[
        "pendencias"
    ]

    assert pendencia["codigo"] == "SEM_DIVIDAS"
    assert pendencia["escopo"] == "DIVIDA_ID"
    assert "não há plano de quitação" in pendencia["mensagem"]


def test_t250_ac03_isolamento_por_caso(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _cliente(monkeypatch, (), conta=None).get(
        f"/caso/{_CASO_ID}/inventario"
    ).status_code == 401
    assert _cliente(monkeypatch, ()).get(f"/caso/{_CASO_ALHEIO}/inventario").status_code == 404


def test_t251_inicio_troca_montar_o_plano_pela_pendencia() -> None:
    """`/inicio` (`T-251`): coleta completa (sem `B5.00`, que saiu em
    `T-649`, não há mais o que perguntar) com inventário incompleto → a
    etapa é `inventario`; sem nenhuma ficha de dívida, `SEM_DIVIDAS` (`RF-
    559`) não aponta mais pergunta nenhuma (`ID_PERGUNTA` nulo — não há mais
    quantidade declarada a corrigir)."""
    from app.casos.fases import FASE_INICIO
    from app.http.rotas_inicio import DESTINO_DA_ETAPA, _proxima_etapa
    from collection.carga import ColecaoDeRegistros
    from collection.respostas import RespostasCaso

    colecao = ColecaoDeRegistros(QUESTIONARIO_VERSION="1.6.0", registros=())
    caso = _caso(ESTADO_CASO.COLETA_INICIAL)

    def etapa() -> tuple[DESTINO_DA_ETAPA, str | None]:
        proxima = _proxima_etapa(
            caso,
            FASE_INICIO.COLETA,
            colecao,
            RespostasCaso(respostas=()),
            {},
            _RepositorioItensDublê(()),
        )
        return proxima.destino, proxima.ID_PERGUNTA

    # Zero fichas: `SEM_DIVIDAS` (`RF-559`) bloqueia sem apontar pergunta —
    # não há mais quantidade declarada para divergir (`AC-597`).
    assert etapa() == (DESTINO_DA_ETAPA.INVENTARIO, None)
