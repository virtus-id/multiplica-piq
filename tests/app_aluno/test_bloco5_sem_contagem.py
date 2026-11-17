"""Ponta a ponta — Bloco 5 sem a pergunta de quantidade (`RF-557`–`RF-560`,
Rodada 18, `T-656`).

Sobre a coleção real e a aplicação real, mesmo arranjo de
`test_coleta_fichas_de_divida.py` (dublês em memória, sem banco). Reusa os
helpers já escritos nas tarefas anteriores desta rodada — este arquivo prova
o conjunto, não reimplementa nenhum mecanismo.

REGRAS: `RF-557`, `RF-558`, `RF-559`, `RF-560`
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.casos.maquina import ESTADO_CASO
from collection.carga import ColecaoDeRegistros
from collection.registro import EscopoRepeticao
from collection.respostas import Resposta
from persistencia.app_aluno.itens import ItemRepetido
from tests.app_aluno.fixtures.caso_completo import DIVIDA_ID_UNICA, caso_completo
from tests.app_aluno.test_coleta_fichas_de_divida import (
    _CASO,
    _cliente,
    _resposta,
    _respostas_da_ficha_exceto_a_ultima,
    _respostas_quase_completas,
)
from tests.app_aluno.test_rotas_calculo import (
    _caso_com_fichas,
    _caso_fabricado,
    _montar_aplicacao_de_teste,
    _RepositorioCasosDublê,
)
from tests.app_aluno.test_rotas_inicio import _caso, _montar_cliente, _no_caso_id

# ---------------------------------------------------------------------------
# `AC-592` (`RF-557`) — zero fichas, o Bloco 5 abre em `B5.A01`, nenhuma
# pergunta de quantidade antes.
# ---------------------------------------------------------------------------


def test_ac592_zero_fichas_bloco_5_abre_em_b5_a01(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, _ = _cliente(monkeypatch, _respostas_quase_completas())

    gravada = cliente.post(
        f"/caso/{_CASO}/resposta", data={"ID_PERGUNTA": "B3.C02", "valor": "NAO"}
    )

    assert gravada.status_code == 200, gravada.text
    assert gravada.json()["proxima"]["pergunta"]["ID"] == "B5.A01"
    assert "DIVIDA_ID" not in gravada.json()["abrir_fichas"]


# ---------------------------------------------------------------------------
# `AC-593`, `AC-594` (`RF-558`) — fechar a única ficha devolve a lista, nunca
# `B5.FIM02` isolada, nos três pontos de entrada.
# ---------------------------------------------------------------------------


def test_ac593_ac594_post_resposta_fecha_a_ficha_e_devolve_a_lista(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item_id = "D001"
    cliente, _ = _cliente(
        monkeypatch, _respostas_da_ficha_exceto_a_ultima(item_id), (item_id,)
    )

    gravada = cliente.post(
        f"/caso/{_CASO}/resposta",
        data={"ID_PERGUNTA": "B5.H04", "item_id": item_id, "valor": "NAO"},
    )

    assert gravada.status_code == 200, gravada.text
    assert gravada.json()["abrir_fichas"] == ["DIVIDA_ID"]
    assert gravada.json()["proxima"]["pergunta"]["ID"] != "B5.FIM02"


def test_ac594_get_pergunta_sem_id_nunca_serve_fim02(monkeypatch: pytest.MonkeyPatch) -> None:
    item_id = "D001"
    respostas = (
        *_respostas_quase_completas(),
        _resposta("DESEJA_PLANO_ACELERADO", "NAO"),
        *_respostas_da_ficha_exceto_a_ultima(item_id),
        _resposta("PREFERENCIA_QUITACAO", "NAO", item_id),
    )
    cliente, _ = _cliente(monkeypatch, respostas, (item_id,))

    corpo = cliente.get(f"/caso/{_CASO}/pergunta").json()

    assert corpo["pergunta"] is None
    assert corpo["abrir_fichas"] == ["DIVIDA_ID"]


def test_ac594_get_inicio_nunca_serve_fim02(monkeypatch: pytest.MonkeyPatch) -> None:
    item = ItemRepetido(
        item_id="D001",
        CASO_ID="CASO-INICIO-1",
        escopo=EscopoRepeticao.DIVIDA_ID,
        removido_em=None,
        criado_em=datetime(2026, 1, 1, tzinfo=UTC),
    )
    respostas = (
        *_no_caso_id(_respostas_quase_completas()),
        *_no_caso_id((_resposta("DESEJA_PLANO_ACELERADO", "NAO"),)),
        *_no_caso_id(_respostas_da_ficha_exceto_a_ultima("D001")),
        *_no_caso_id((_resposta("PREFERENCIA_QUITACAO", "NAO", "D001"),)),
    )
    cliente = _montar_cliente(
        monkeypatch,
        casos=(_caso(ESTADO_CASO.COLETA_INICIAL),),
        respostas=respostas,
        itens=(item,),
    )

    etapa = cliente.get("/caso/CASO-INICIO-1/inicio").json()["proxima_etapa"]

    assert etapa["ID_PERGUNTA"] != "B5.FIM02"
    assert etapa["abrir_fichas"] == ["DIVIDA_ID"]


# ---------------------------------------------------------------------------
# `AC-595`, `AC-596`, `EC-97` (`RF-559`) — `SEM_DIVIDAS` só pela existência de
# ficha com resposta.
# ---------------------------------------------------------------------------


def test_ac595_ec97_zero_fichas_bloqueia_sem_opcao_de_nao_tenho_divida(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente, _, _snapshots, _eventos = _caso_com_fichas(monkeypatch, com_ficha=False)

    resposta = cliente.post("/caso/CASO-CALCULO-1/calculo")

    assert resposta.status_code == 400
    (pendencia,) = resposta.json()["pendencias"]
    assert pendencia["codigo"] == "SEM_DIVIDAS"
    # `EC-97`: nenhuma opção "não tenho dívida" — só a orientação de
    # cadastrar uma ficha (`escopo`).
    assert pendencia["escopo"] == "DIVIDA_ID"


def test_ac596_uma_ficha_com_resposta_libera_o_calculo(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, repositorio_casos, *_ = _caso_com_fichas(monkeypatch, com_ficha=True)

    resposta = cliente.post("/caso/CASO-CALCULO-1/calculo")

    assert resposta.status_code not in (400, 422)
    assert repositorio_casos.chamadas_transicionar_estado_se == [
        (ESTADO_CASO.COLETA_INICIAL, ESTADO_CASO.CALCULANDO)
    ]


# ---------------------------------------------------------------------------
# `AC-597`, `EC-95` (`RF-560`) — resposta antiga de `B5.00` no histórico não
# afeta o bloqueio, nem bloqueia por divergência.
# ---------------------------------------------------------------------------


def test_ac597_ec95_resposta_antiga_de_b5_00_nao_afeta_o_bloqueio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caso antigo: declarou 5 em `B5.00` (`QUANTIDADE_DIVIDAS_DECLARADA_
    INICIAL`, variável que não corresponde mais a nenhum registro —
    `T-649`) e cadastrou 2 fichas com resposta. A divergência 5×2 não bloqueia
    mais — essa comparação não existe (`RF-559`); duas fichas com resposta
    bastam."""
    agora = datetime(2026, 1, 1, tzinfo=UTC)
    b5_00 = Resposta(
        CASO_ID="CASO-CALCULO-1",
        ID_PERGUNTA="QUANTIDADE_DIVIDAS_DECLARADA_INICIAL",
        item_id=None,
        valor=5,
        QUESTIONARIO_VERSION="1.0.0",
        respondida_em=agora,
    )
    itens = tuple(
        ItemRepetido(
            item_id=item_id,
            CASO_ID="CASO-CALCULO-1",
            escopo=EscopoRepeticao.DIVIDA_ID,
            removido_em=None,
            criado_em=agora,
        )
        for item_id in ("D001", "D002")
    )
    # Todas as respostas de `caso_completo()` (Blocos 1 a 4 incluídos — sem
    # elas a montagem do `EstadoFinanceiro` falharia por outro motivo, não
    # pela dívida) com a ÚNICA ficha duplicada em D001/D002: as duas
    # precisam da mesma resolução financeira completa, senão `dividas_
    # pendentes` (`RF-527`) as marcaria pendentes e a rota devolveria `422`
    # antes de chegar à checagem de `SEM_DIVIDAS` que este teste prova.
    caso = caso_completo()
    respostas = (
        b5_00,
        *(r for r in caso.respostas.respostas if r.item_id != DIVIDA_ID_UNICA),
        *(
            replace(r, item_id=item_id)
            for item_id in ("D001", "D002")
            for r in caso.respostas.respostas
            if r.item_id == DIVIDA_ID_UNICA
        ),
    )
    repositorio_casos = _RepositorioCasosDublê(
        _caso_fabricado(ESTADO_CASO.COLETA_INICIAL), conta_id_da_sessao="CONTA-1"
    )
    cliente, _snapshots = _montar_aplicacao_de_teste(
        monkeypatch,
        repositorio_casos=repositorio_casos,
        colecao=ColecaoDeRegistros(QUESTIONARIO_VERSION="1.0.0", registros=()),
        respostas=respostas,
        itens=itens,
    )

    resposta = cliente.post("/caso/CASO-CALCULO-1/calculo")

    assert resposta.status_code not in (400, 422)


# ---------------------------------------------------------------------------
# `EC-98` — `B5.FIM02 = SIM` com zero fichas é aceito pela gravação, mas não
# desbloqueia o cálculo.
# ---------------------------------------------------------------------------


def test_ec98_fim02_sim_e_aceito_pela_gravacao(monkeypatch: pytest.MonkeyPatch) -> None:
    """A gravação de `B5.FIM02 = SIM` com zero fichas é aceita como qualquer
    resposta — o botão não aparece nessa condição pela interface (`RF-558`),
    mas a rota não distingue."""
    cliente, repositorio = _cliente(monkeypatch, ())

    gravada = cliente.post(
        f"/caso/{_CASO}/resposta", data={"ID_PERGUNTA": "B5.FIM02", "valor": "SIM"}
    )

    assert gravada.status_code == 200, gravada.text
    assert any(r.ID_PERGUNTA == "CONFIRMACAO_FIM_CADASTRO" for r in repositorio.respostas)


def test_ec98_fim02_sim_nao_desbloqueia_o_calculo_com_zero_fichas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`SEM_DIVIDAS` (`RF-559`) depende só da existência de ficha — nunca de
    `CONFIRMACAO_FIM_CADASTRO`. Mesmo com `B5.FIM02 = SIM` gravada, zero
    fichas continua bloqueando."""
    agora = datetime(2026, 1, 1, tzinfo=UTC)
    repositorio_casos = _RepositorioCasosDublê(
        _caso_fabricado(ESTADO_CASO.COLETA_INICIAL), conta_id_da_sessao="CONTA-1"
    )
    fim02 = Resposta(
        CASO_ID="CASO-CALCULO-1",
        ID_PERGUNTA="CONFIRMACAO_FIM_CADASTRO",
        item_id=None,
        valor="SIM",
        QUESTIONARIO_VERSION="1.0.0",
        respondida_em=agora,
    )
    cliente, _snapshots = _montar_aplicacao_de_teste(
        monkeypatch,
        repositorio_casos=repositorio_casos,
        colecao=ColecaoDeRegistros(QUESTIONARIO_VERSION="1.0.0", registros=()),
        respostas=(fim02,),
        itens=(),
    )

    resposta = cliente.post("/caso/CASO-CALCULO-1/calculo")

    assert resposta.status_code == 400
    (pendencia,) = resposta.json()["pendencias"]
    assert pendencia["codigo"] == "SEM_DIVIDAS"
