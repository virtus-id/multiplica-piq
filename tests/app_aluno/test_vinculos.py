"""Vínculos e margem por vínculo — `RF-89`, `RF-90` (`T-255`, `T-260`,
`T-282`, `T-389`).

`AC-136`, `AC-139`, `EC-35`, `DE-05`, sobre os registros
REAIS e a aplicação real com repositórios de arquivo (mesmos auxiliares de
`test_ficha_repetivel.py`). `T-282` (`DE-04`): sem vínculo cadastrado, a
dívida consignada não trava a coleta — a pendência vai para o inventário e
só o cálculo final bloqueia.

`T-389`: a conferência da renda dos vínculos (`T-258`, `AC-156`, `EC-41`)
saiu junto com `B3.S04L`.

REGRAS: `RF-89`, `RF-90`, `AC-136`, `AC-139`, `EC-35`
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.casos.inventario import (
    TIPO_PENDENCIA_INVENTARIO,
    mensagem_da_pendencia,
    pendencias_de_inventario,
)
from app.http.rotas_inventario import (
    obter_colecao_de_registros_do_inventario,
    obter_repositorio_itens_do_inventario,
    obter_repositorio_respostas_do_inventario,
)
from collection.carga import carregar_registros
from collection.registro import EscopoRepeticao, RegistroPergunta
from collection.respostas import Resposta, RespostasCaso
from persistencia.app_aluno.arquivo import RepositorioItensArquivo, RepositorioRespostasArquivo
from tests.app_aluno.test_ficha_repetivel import (
    _CASO_ID,
    _cliente_real,
    _criar_em,
    _fichas,
    _responder,
)


@cache
def _registros() -> tuple[RegistroPergunta, ...]:
    return carregar_registros().registros


def _registro(ID: str) -> RegistroPergunta:
    (registro,) = [r for r in _registros() if r.ID == ID]
    return registro


def _resposta(variavel: str, valor: object, item_id: str | None = None) -> Resposta:
    return Resposta(
        CASO_ID="CASO-VINCULOS",
        ID_PERGUNTA=variavel,
        item_id=item_id,
        valor=valor,  # type: ignore[arg-type]
        QUESTIONARIO_VERSION="1.0.3",
        respondida_em=datetime(2026, 9, 30, tzinfo=UTC),
    )


def _cliente_com_inventario(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    cliente = _cliente_real(monkeypatch, tmp_path)
    aplicacao: Any = cliente.app
    aplicacao.dependency_overrides[obter_colecao_de_registros_do_inventario] = (
        carregar_registros
    )
    aplicacao.dependency_overrides[obter_repositorio_respostas_do_inventario] = lambda: (
        RepositorioRespostasArquivo(caminho_arquivo=tmp_path / "respostas.jsonl")
    )
    aplicacao.dependency_overrides[obter_repositorio_itens_do_inventario] = lambda: (
        RepositorioItensArquivo(caminho_arquivo=tmp_path / "itens.jsonl")
    )
    return cliente


def _proxima_do_item(cliente: TestClient, item_id: str) -> str:
    corpo = cliente.get(f"/caso/{_CASO_ID}/pergunta", params={"item_id": item_id}).json()
    ID: str = corpo["pergunta"]["ID"]
    return ID


def _campos(cliente: TestClient, escopo: str, item_id: str) -> list[str]:
    (ficha,) = [f for f in _fichas(cliente, escopo) if f["item_id"] == item_id]
    return [c["ID"] for c in ficha["campos"]]


# ---------------------------------------------------------------------------
# T-389 — as perguntas de renda e consignação por vínculo saíram (RF-402).
# ---------------------------------------------------------------------------


def test_t389_so_o_nome_do_vinculo_fica_na_ficha(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ids = {r.ID for r in _registros()}
    assert not {"B3.S04", "B3.S04L", "B3.S05", "B3.S05C"} & ids

    cliente = _cliente_real(monkeypatch, tmp_path)
    _responder(cliente, "B3.S01", "SIM")
    vinculo = _criar_em(cliente, "VINCULO_ID").json()["ficha"]["item_id"]
    assert _campos(cliente, "VINCULO_ID", vinculo) == ["B3.S03"]


# ---------------------------------------------------------------------------
# T-260 — independência (AC-136), pertença (AC-137), EC-35.
# ---------------------------------------------------------------------------


def test_ac136_dois_vinculos_independentes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cliente = _cliente_real(monkeypatch, tmp_path)
    _responder(cliente, "B3.S01", "SIM")
    v1 = _fichas(cliente, "VINCULO_ID")[0]["item_id"]  # `T-311`: nasce com o "Sim"
    v2 = _criar_em(cliente, "VINCULO_ID").json()["ficha"]["item_id"]
    assert v1 != v2
    for ID, valor in (("B3.S03", "Prefeitura"),):
        assert _responder(cliente, ID, valor, v1).status_code == 200
    gravadas = RepositorioRespostasArquivo(tmp_path / "respostas.jsonl")
    antes = {r for r in gravadas.listar_do_caso(_CASO_ID) if r.item_id == v1}

    for ID, valor in (("B3.S03", "Estado"),):
        assert _responder(cliente, ID, valor, v2).status_code == 200

    assert {r for r in gravadas.listar_do_caso(_CASO_ID) if r.item_id == v1} == antes
    assert [f["item_id"] for f in _fichas(cliente, "VINCULO_ID")] == [v1, v2]


def test_ec35_remover_vinculo_deixa_consignado_em_aberto(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Com outro vínculo ainda ativo, a dívida que apontava o removido volta
    a pedir o vínculo (`AC-139`). `T-389`: a margem por vínculo (`AC-137`,
    `B3.S06*`) saiu do questionário."""
    cliente = _cliente_real(monkeypatch, tmp_path)
    _responder(cliente, "B3.S01", "SIM")
    removido = _criar_em(cliente, "VINCULO_ID").json()["ficha"]["item_id"]
    _criar_em(cliente, "VINCULO_ID")
    divida = _criar_em(cliente, "DIVIDA_ID").json()["ficha"]["item_id"]
    _responder(cliente, "B5.A01", "Banco", divida)
    _responder(cliente, "B5.A02", "CONSIGNADO", divida)
    _responder(cliente, "B5.A02V", removido, divida)
    assert _proxima_do_item(cliente, divida) != "B5.A02V"

    cliente.delete(f"/caso/{_CASO_ID}/fichas/VINCULO_ID/{removido}")

    assert _proxima_do_item(cliente, divida) == "B5.A02V"


# ---------------------------------------------------------------------------
# T-282 — consignado sem vínculo: não trava a ficha; pendência de inventário.
# ---------------------------------------------------------------------------


def test_t282_sem_vinculo_a_pergunta_do_vinculo_nao_aparece_e_a_ficha_segue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cliente = _cliente_com_inventario(monkeypatch, tmp_path)
    divida = _criar_em(cliente, "DIVIDA_ID").json()["ficha"]["item_id"]
    _responder(cliente, "B5.A01", "Banco", divida)
    _responder(cliente, "B5.A02", "CONSIGNADO", divida)

    assert _proxima_do_item(cliente, divida) != "B5.A02V"
    assert "B5.A02V" not in _campos(cliente, "DIVIDA_ID", divida)
    direta = cliente.get(f"/caso/{_CASO_ID}/pergunta/B5.A02V", params={"item_id": divida})
    assert direta.status_code == 404

    (pendencia,) = cliente.get(f"/caso/{_CASO_ID}/inventario").json()["pendencias"]
    assert pendencia["codigo"] == "CONSIGNADO_SEM_VINCULO"
    assert pendencia["escopo"] == "VINCULO_ID"
    assert pendencia["ID_PARA_CORRIGIR"] == "B3.S01"

    _criar_em(cliente, "VINCULO_ID")
    assert _proxima_do_item(cliente, divida) == "B5.A02V"
    assert cliente.get(f"/caso/{_CASO_ID}/inventario").json()["pendencias"] == []


def test_t282_pendencia_so_para_consignado_e_some_com_vinculo() -> None:
    consignado = (_resposta("TIPO_DIVIDA", "CONSIGNADO", item_id="D001"),)
    pessoal = (_resposta("TIPO_DIVIDA", "PESSOAL", item_id="D001"),)
    dividas = {EscopoRepeticao.DIVIDA_ID: ("D001",)}

    (pendencia,) = pendencias_de_inventario(
        _registros(), RespostasCaso(respostas=consignado), dividas
    )
    assert pendencia.tipo is TIPO_PENDENCIA_INVENTARIO.CONSIGNADO_SEM_VINCULO
    assert "consignad" in mensagem_da_pendencia(pendencia)
    assert pendencias_de_inventario(_registros(), RespostasCaso(respostas=pessoal), dividas) == ()
    com_vinculo = dividas | {EscopoRepeticao.VINCULO_ID: ("V001",)}
    assert (
        pendencias_de_inventario(_registros(), RespostasCaso(respostas=consignado), com_vinculo)
        == ()
    )
