"""Todo plano novo descarta a ordem do revisor — `RF-550`, `AC-573` (`T-592`)
· plano `R18.5` (Plano novo).

`RF-550` não tem código: o reenvio do aluno chama o cálculo de sempre, sem a
lista. Estes testes provam isso nos caminhos de reenvio, partindo de um caso
cuja última versão é ajustada, pelo fluxo de `test_rotas_ordem_do_revisor.py`.

O terceiro caminho de `AC-573`, o plano novo depois da liberação (`RF-118`),
foi desligado por `RF-409` (`enxugamento-questionario`, o plano entregue é
definitivo): o pedido é recusado e a ordem ajustada liberada fica como está.

REGRAS: `RF-550`, `AC-573`, `EC-81`
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from app.casos.maquina import ESTADO_CASO
from app.revisao.ordem_do_revisor import ordem_vigente
from engine.snapshot import SnapshotOrdem
from tests.app_aluno.fixtures.caso_completo import CASO_ID
from tests.app_aluno.test_rotas_ordem_do_revisor import (
    DIVIDAS,
    MOTIVO,
    Cenario,
    cenario,  # noqa: F401 — fixture do fluxo de ajuste da ordem
)

_LISTA = ["D003", "D001", "D002"]


def _ids(snapshot: SnapshotOrdem) -> tuple[str, ...]:
    return tuple(p.DIVIDA_ID for p in snapshot.ORDEM_QUITACAO)


def _pedir_correcao(cenario: Cenario) -> None:  # noqa: F811
    resposta = cenario.decidir("decisao=REPROVAR&mensagem_aluno=Confira+o+saldo")
    assert resposta.status_code == 200


def _retirar_da_conferencia(cenario: Cenario) -> None:  # noqa: F811
    assert cenario.aluno.post(f"/caso/{CASO_ID}/retomar-edicao").status_code == 200


@pytest.mark.parametrize(
    "devolver",
    [
        pytest.param(_pedir_correcao, id="pedir-correcao-RF-113"),
        pytest.param(_retirar_da_conferencia, id="quero-editar-RF-115"),
    ],
)
def test_ac573_reenvio_depois_do_ajuste_volta_a_ordem_do_metodo(
    cenario: Cenario,  # noqa: F811
    devolver: Callable[[Cenario], None],
) -> None:
    v1 = cenario.enviar()
    assert cenario.ajustar(_LISTA).status_code == 200
    ajustada = cenario.historico()[-1]
    assert ajustada.ORDEM_DO_REVISOR == tuple(_LISTA)
    devolver(cenario)
    assert cenario.caso().estado is ESTADO_CASO.COLETA_INICIAL

    nova = cenario.enviar()

    assert nova.snapshot_anterior_id == ajustada.SNAPSHOT_ID
    assert nova.ORDEM_DO_REVISOR is None
    assert ordem_vigente(nova) == (DIVIDAS, False)
    assert _ids(nova) == _ids(v1)
    assert cenario.caso().estado is ESTADO_CASO.AGUARDANDO_REVISAO
    fila = cenario.revisor.get("/api/revisao/fila").json()["itens"]
    assert [item["CASO_ID"] for item in fila] == [CASO_ID]
    # O aluno não lê nada sobre a ordem nem sobre o ajuste.
    for rota in ("inicio", "calculo/progresso"):
        resposta = cenario.aluno.get(f"/caso/{CASO_ID}/{rota}")
        assert resposta.status_code == 200, rota
        texto = resposta.text
        assert MOTIVO not in texto, rota
        assert "revisor" not in texto.lower(), rota
        assert "ajust" not in texto.lower(), rota


def test_ac573_plano_ajustado_liberado_e_definitivo(cenario: Cenario) -> None:  # noqa: F811
    """`RF-118` desligado por `RF-409`: depois da liberação não há plano novo,
    e a versão liberada continua a ajustada."""
    cenario.enviar()
    assert cenario.ajustar(_LISTA).status_code == 200
    assert cenario.decidir("decisao=LIBERAR").status_code == 200
    historico = cenario.historico()

    assert cenario.aluno.post(f"/caso/{CASO_ID}/refazer-plano").status_code == 409

    assert cenario.historico() == historico
    assert cenario.caso().estado is ESTADO_CASO.PLANO_LIBERADO
    assert cenario.caso().snapshot_liberado_id == historico[-1].SNAPSHOT_ID
