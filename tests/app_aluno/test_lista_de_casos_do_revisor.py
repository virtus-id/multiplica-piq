"""Testes de `GET /api/revisao/casos` — a lista de casos do revisor
(`RF-501` a `RF-506`, `AC-501` a `AC-505`, `AC-507`, T-408).

`SnapshotOrdem` REAL (`executar_calculo`) e repositórios de arquivo para casos
e snapshots, como em `test_rotas_revisao.py`; trilha de eventos e revisões são
dublês em memória com datas controladas (os repositórios de arquivo não têm
revisões, e o executor grava eventos com a hora de agora).

Cenário (um caso por situação), horas contadas a partir de agora:

- `A` em revisão há 6 dias (atrasado) · `B` em revisão há 2 dias
- `C` entregue (chegou há 10 dias, decidido há 9) por `REV-1`
- `D` devolvido e reenviado: entrou há 20 dias, foi reprovado há 19, entrou de
  novo há 3 dias (a chegada vale a última) e é um recálculo
- `E` devolvido, de volta com o aluno em `COLETA_INICIAL`
- `F` em coleta, sem plano enviado (fora da lista)
- `G` com erro de cálculo e plano já enviado antes · `H` com erro de cálculo
  sem nunca ter chegado à revisão (fora)
- `I` em revisão sem evento de entrada (chegada aproximada)
- `K` em coleta porque o aluno retirou o plano (sem decisão: fora)

REGRAS: `RF-501`, `RF-503`, `RF-504`, `RF-505`, `RF-506`, `AC-501` a `AC-505`, `AC-507`
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.casos.maquina import ESTADO_CASO
from app.http.aplicacao import criar_aplicacao
from app.http.isolamento import exigir_papel_revisor, obter_repositorio_contas_para_papel
from app.http.rotas_api_plano import (
    obter_emails_dos_alunos,
    obter_repositorio_eventos_da_lista,
    obter_repositorio_revisoes_da_lista,
    obter_revisores,
)
from app.http.rotas_revisao import (
    obter_repositorio_casos_da_fila,
    obter_repositorio_snapshots_da_fila,
)
from app.http.sessao import iniciar_sessao_conta
from app.revisao.fila import (
    CLASSIFICACAO_ERRO,
    DECISAO_REVISAO,
    RegistroRevisao,
    montar_item_da_fila,
)
from app.revisao.lista_de_casos import (
    FiltrosDaLista,
    LinhaDoCaso,
    consultar_casos,
)
from persistencia.app_aluno.arquivo import RepositorioCasosArquivo, RepositorioEventosCasoArquivo
from persistencia.app_aluno.contas import ContaDoCaso
from persistencia.app_aluno.eventos import EventoCaso
from persistencia.arquivo.repositorio_snapshots import RepositorioSnapshotsArquivo
from tests.app_aluno.test_rotas_revisao import _calcular_snapshot, _criar_caso

_CHAVE_TESTE = "chave-de-teste-para-assinatura-de-sessao-nao-usar-em-producao"
_AGORA = datetime.now(UTC)
_CODIGO = re.compile(r"\b[A-Z]+(?:_[A-Z0-9]+)+\b")


def _h(horas: float) -> datetime:
    return _AGORA - timedelta(hours=horas)


def _dias(dias: int) -> datetime:
    return _h(24 * dias)


class _Eventos:
    def __init__(self) -> None:
        self.por_caso: dict[str, list[EventoCaso]] = {}
        self.consultas = 0

    def entrada(self, caso_id: str, quando: datetime) -> None:
        self.por_caso.setdefault(caso_id, []).append(
            EventoCaso(
                evento_id=f"EV-{caso_id}-{len(self.por_caso.get(caso_id, []))}",
                CASO_ID=caso_id,
                tipo_evento="snapshot_anexado",
                estado_de="CALCULANDO",
                estado_para="AGUARDANDO_REVISAO",
                detalhe=None,
                ocorrido_em=quando,
            )
        )

    def listar_dos_casos(self, caso_ids: tuple[str, ...]) -> dict[str, tuple[EventoCaso, ...]]:
        self.consultas += 1
        return {c: tuple(self.por_caso[c]) for c in caso_ids if c in self.por_caso}


class _Revisoes:
    def __init__(self) -> None:
        self.por_caso: dict[str, list[RegistroRevisao]] = {}
        self.consultas = 0

    def decisao(
        self, caso_id: str, decisao: DECISAO_REVISAO, autor: str, quando: datetime
    ) -> None:
        self.por_caso.setdefault(caso_id, []).append(
            RegistroRevisao(
                SNAPSHOT_ID="S",
                CASO_ID=caso_id,
                decisao=decisao,
                autor=autor,
                decidido_em=quando,
                classificacao_erro=(
                    CLASSIFICACAO_ERRO.DADO if decisao is DECISAO_REVISAO.REPROVADO else None
                ),
                observacao=None,
            )
        )

    def listar_dos_casos(
        self, caso_ids: tuple[str, ...]
    ) -> dict[str, tuple[RegistroRevisao, ...]]:
        self.consultas += 1
        return {c: tuple(self.por_caso[c]) for c in caso_ids if c in self.por_caso}


@dataclass
class _Cenario:
    casos: RepositorioCasosArquivo
    snapshots: RepositorioSnapshotsArquivo
    eventos: _Eventos
    revisoes: _Revisoes


_CONTAS = {
    "CASO-A": ContaDoCaso(email="ana@exemplo.invalido", e_revisor=False, nome="Ana Souza"),
    "CASO-B": ContaDoCaso(email="bruno@exemplo.invalido", e_revisor=False, nome="Bruno Lima"),
    "CASO-C": ContaDoCaso(email="carla@exemplo.invalido", e_revisor=False, nome=None),
    "CASO-D": ContaDoCaso(email="davi@exemplo.invalido", e_revisor=False, nome="Davi Alves"),
    "CASO-E": ContaDoCaso(email="elisa@exemplo.invalido", e_revisor=False, nome="Elisa Prado"),
    "CASO-G": ContaDoCaso(email="gil@exemplo.invalido", e_revisor=False, nome="Gil Rocha"),
    "CASO-I": ContaDoCaso(email="iara@exemplo.invalido", e_revisor=False, nome="Iara Reis"),
}


@pytest.fixture(scope="module")
def cenario(tmp_path_factory: pytest.TempPathFactory) -> _Cenario:
    pasta = tmp_path_factory.mktemp("lista-de-casos")
    casos = RepositorioCasosArquivo(pasta / "casos.jsonl")
    snapshots = RepositorioSnapshotsArquivo(pasta / "snapshots.jsonl")
    do_executor = RepositorioEventosCasoArquivo(pasta / "eventos.jsonl")
    eventos, revisoes = _Eventos(), _Revisoes()

    def calcular(caso_id: str, dia: int, **extra: Any) -> Any:
        return _calcular_snapshot(
            caso_id,
            casos,
            snapshots,
            do_executor,
            estado_anterior=ESTADO_CASO.COLETA_INICIAL,
            data_referencia=date(2026, 1, dia),
            **extra,
        )

    for dia, caso_id in enumerate("ABCDEGHIK", start=1):
        _criar_caso(casos, f"CASO-{caso_id}", f"conta-{caso_id}")
        primeiro = calcular(f"CASO-{caso_id}", dia)
        if caso_id == "D":
            casos.transicionar_estado("CASO-D", ESTADO_CASO.CALCULANDO)
            calcular("CASO-D", dia, anterior=primeiro)

    _criar_caso(casos, "CASO-F", "conta-F")

    eventos.entrada("CASO-A", _dias(6))
    eventos.entrada("CASO-B", _dias(2))
    eventos.entrada("CASO-C", _dias(10))
    eventos.entrada("CASO-D", _dias(20))
    eventos.entrada("CASO-D", _dias(3))
    eventos.entrada("CASO-E", _dias(8))
    eventos.entrada("CASO-G", _dias(30))
    eventos.entrada("CASO-K", _dias(5))

    revisoes.decisao("CASO-C", DECISAO_REVISAO.LIBERADO, "REV-1", _dias(9))
    revisoes.decisao("CASO-D", DECISAO_REVISAO.REPROVADO, "REV-2", _dias(19))
    revisoes.decisao("CASO-E", DECISAO_REVISAO.REPROVADO, "REV-1", _dias(7))

    casos.transicionar_estado("CASO-C", ESTADO_CASO.PLANO_LIBERADO)
    casos.transicionar_estado("CASO-E", ESTADO_CASO.COLETA_INICIAL)
    casos.transicionar_estado("CASO-G", ESTADO_CASO.ERRO_DE_CALCULO)
    casos.transicionar_estado("CASO-H", ESTADO_CASO.ERRO_DE_CALCULO)
    casos.transicionar_estado("CASO-K", ESTADO_CASO.COLETA_INICIAL)
    casos.transicionar_estado("CASO-I", ESTADO_CASO.AGUARDANDO_REVISAO, agora=_dias(1))
    return _Cenario(casos, snapshots, eventos, revisoes)


def _cliente(cenario: _Cenario, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CHAVE_ASSINATURA_SESSAO", _CHAVE_TESTE)
    app = criar_aplicacao()
    app.dependency_overrides[obter_repositorio_casos_da_fila] = lambda: cenario.casos
    app.dependency_overrides[obter_repositorio_snapshots_da_fila] = lambda: cenario.snapshots
    app.dependency_overrides[obter_repositorio_eventos_da_lista] = lambda: cenario.eventos
    app.dependency_overrides[obter_repositorio_revisoes_da_lista] = lambda: cenario.revisoes
    app.dependency_overrides[exigir_papel_revisor] = lambda: "REV-1"
    app.dependency_overrides[obter_emails_dos_alunos] = lambda: SimpleNamespace(
        emails_dos_casos=lambda _ids: {},
        contas_dos_casos=lambda ids: {c: _CONTAS[c] for c in ids if c in _CONTAS},
    )
    app.dependency_overrides[obter_revisores] = lambda: (
        lambda: {"REV-1": "rev1@exemplo.invalido", "REV-2": "rev2@exemplo.invalido"}
    )
    return TestClient(app, base_url="https://teste.local")


@pytest.fixture
def cliente(cenario: _Cenario, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    return _cliente(cenario, monkeypatch)


def _ids(corpo: dict[str, Any]) -> list[str]:
    return [i["CASO_ID"].removeprefix("CASO-") for i in corpo["itens"]]


# --------------------------------------------------------------------- AC-501


def _cliente_com_guarda_real(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CHAVE_ASSINATURA_SESSAO", _CHAVE_TESTE)
    app: FastAPI = criar_aplicacao()
    contas = {
        "ALUNO": SimpleNamespace(e_revisor=False),
        "REVISOR": SimpleNamespace(e_revisor=True),
    }
    app.dependency_overrides[obter_repositorio_contas_para_papel] = lambda: SimpleNamespace(
        buscar_por_id=lambda conta_id: contas.get(conta_id)
    )

    @app.post("/_teste/login")
    def login(request: Request, conta_id: str) -> dict[str, str]:
        iniciar_sessao_conta(request, conta_id=conta_id)
        return {"status": "ok"}

    return TestClient(app, base_url="https://teste.local")


def test_ac501_sem_sessao_recebe_401(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _cliente_com_guarda_real(monkeypatch).get("/api/revisao/casos").status_code == 401


def test_ac501_aluno_comum_recebe_403(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = _cliente_com_guarda_real(monkeypatch)
    cliente.post("/_teste/login", params={"conta_id": "ALUNO"})
    assert cliente.get("/api/revisao/casos").status_code == 403


def test_ac501_so_entram_casos_que_chegaram_a_revisao(cliente: TestClient) -> None:
    corpo = cliente.get("/api/revisao/casos", params={"aba": "todos"}).json()

    # F (coleta), H (erro sem plano enviado) e K (aluno retirou o plano) ficam de fora.
    assert sorted(_ids(corpo)) == ["A", "B", "C", "D", "E", "G", "I"]
    assert corpo["total"] == 7


# --------------------------------------------------------------------- AC-502


def test_ac502_item_traz_as_colunas_com_rotulos_humanos(cliente: TestClient) -> None:
    corpo = cliente.get("/api/revisao/casos", params={"aba": "todos"}).json()
    por_id = {i["CASO_ID"]: i for i in corpo["itens"]}
    a, c, d = por_id["CASO-A"], por_id["CASO-C"], por_id["CASO-D"]

    assert a["nome"] == "Ana Souza" and a["email_do_aluno"] == "ana@exemplo.invalido"
    assert por_id["CASO-C"]["nome"] is None  # sem nome: a tela mostra o e-mail
    assert a["status"] == "AGUARDANDO_REVISAO" and a["status_rotulo"] == "Em revisão"
    assert c["status_rotulo"] == "Entregue"
    assert por_id["CASO-E"]["status_rotulo"] == "Devolvido ao aluno"
    assert por_id["CASO-G"]["status_rotulo"] == "Erro no cálculo"
    assert a["tipo"] == "primeiro" and a["tipo_rotulo"] == "Primeiro plano"
    assert a["motivo_rotulo"] == "Primeiro cálculo, sem evento de recálculo"
    assert d["tipo"] == "recalculo" and d["tipo_rotulo"] == "Recálculo"
    assert a["situacao_mes_rotulo"] in ("Fecha positivo", "Mês no negativo")
    assert isinstance(a["dividas"], int) and a["dividas"] >= 1
    assert a["metodo"] and a["status_metodo"]
    assert isinstance(a["entra_por_politica"], bool) and isinstance(a["e_metodologico"], bool)
    assert a["revisor"] is None and a["decidido_em"] is None  # pendente não tem decisão
    assert c["revisor"] == "rev1@exemplo.invalido"
    assert c["decidido_em"] == _dias(9).isoformat()

    colunas = [
        "status_rotulo",
        "tipo_rotulo",
        "motivo_rotulo",
        "situacao_mes_rotulo",
        "metodo",
        "status_metodo",
        "revisor",
    ]
    textos = [i[k] for i in corpo["itens"] for k in colunas if i[k] is not None]
    assert [t for t in textos if _CODIGO.search(t)] == []


# --------------------------------------------------------------------- AC-503


def test_ac503_abas_e_contagens(cliente: TestClient) -> None:
    pendentes = cliente.get("/api/revisao/casos", params={"aba": "pendentes"}).json()
    entregues = cliente.get("/api/revisao/casos", params={"aba": "entregues"}).json()
    devolvidos = cliente.get("/api/revisao/casos", params={"aba": "devolvidos"}).json()

    assert sorted(_ids(pendentes)) == ["A", "B", "D", "I"]
    assert _ids(entregues) == ["C"]
    assert _ids(devolvidos) == ["E"]
    contagens = pendentes["contagens"]
    assert contagens == {"pendentes": 4, "entregues": 1, "devolvidos": 1, "todos": 7}
    for aba, resposta in (("pendentes", pendentes), ("entregues", entregues)):
        assert contagens[aba] == resposta["total"]


def test_ac503_filtros_se_combinam_e_contagens_acompanham(cliente: TestClient) -> None:
    corpo = cliente.get(
        "/api/revisao/casos", params={"aba": "todos", "q": "SOUZA", "tipo": "primeiro"}
    ).json()
    assert _ids(corpo) == ["A"]
    assert corpo["contagens"]["todos"] == 1

    por_email = cliente.get("/api/revisao/casos", params={"aba": "todos", "q": "ELISA@"}).json()
    assert _ids(por_email) == ["E"]

    recalculo = cliente.get("/api/revisao/casos", params={"aba": "todos", "tipo": "recalculo"})
    assert _ids(recalculo.json()) == ["D"]
    multiplo = cliente.get(
        "/api/revisao/casos",
        params=[("aba", "todos"), ("status", "PLANO_LIBERADO"), ("status", "ERRO_DE_CALCULO")],
    ).json()
    assert sorted(_ids(multiplo)) == ["C", "G"]
    do_rev_2 = cliente.get("/api/revisao/casos", params={"aba": "todos", "revisor": "REV-2"})
    assert _ids(do_rev_2.json()) == []  # a decisão de D já não vale: voltou à fila
    do_rev_1 = cliente.get("/api/revisao/casos", params={"aba": "todos", "revisor": "REV-1"})
    assert sorted(_ids(do_rev_1.json())) == ["C", "E"]

    periodo = cliente.get(
        "/api/revisao/casos",
        params={
            "aba": "todos",
            "de": _dias(11).date().isoformat(),
            "ate": _dias(7).date().isoformat(),
        },
    ).json()
    assert sorted(_ids(periodo)) == ["C", "E"]


def test_ac503_mes_negativo_metodo_e_motivo(cliente: TestClient) -> None:
    todos = cliente.get("/api/revisao/casos", params={"aba": "todos"}).json()
    negativo = todos["itens"][0]["mes_negativo"]
    oposto = "nao" if negativo else "sim"
    sim_ou_nao = {True: "sim", False: "nao"}

    mesmo = cliente.get(
        "/api/revisao/casos", params={"aba": "todos", "mes_negativo": sim_ou_nao[negativo]}
    ).json()
    outro = cliente.get(
        "/api/revisao/casos", params={"aba": "todos", "mes_negativo": oposto}
    ).json()
    assert mesmo["total"] + outro["total"] == todos["total"]

    opcoes = todos["opcoes"]
    metodo = opcoes["metodos"][0]
    assert metodo["rotulo"] and not _CODIGO.search(metodo["rotulo"])
    por_metodo = cliente.get(
        "/api/revisao/casos", params={"aba": "todos", "metodo": metodo["codigo"]}
    ).json()
    assert por_metodo["total"] >= 1
    sem_motivo = cliente.get(
        "/api/revisao/casos", params={"aba": "todos", "motivo": "NOVA_DIVIDA"}
    ).json()
    assert sem_motivo["total"] == 0
    assert {r["codigo"] for r in opcoes["revisores"]} == {"REV-1"}


def test_ac503_ordenacao_padrao_e_escolhida(cliente: TestClient) -> None:
    # Pendentes: mais antigo primeiro (D entrou há 3 dias, I há 1; A há 6, B há 2).
    assert _ids(cliente.get("/api/revisao/casos", params={"aba": "pendentes"}).json()) == [
        "A", "D", "B", "I"
    ]
    # Demais abas: mais recente primeiro.
    assert _ids(cliente.get("/api/revisao/casos", params={"aba": "todos"}).json()) == [
        "I", "B", "D", "A", "E", "C", "G"
    ]
    assert _ids(
        cliente.get(
            "/api/revisao/casos",
            params={"aba": "todos", "ordenar": "chegou_em", "direcao": "asc"},
        ).json()
    ) == ["G", "C", "E", "A", "D", "B", "I"]
    por_nome = cliente.get(
        "/api/revisao/casos", params={"aba": "todos", "ordenar": "aluno", "direcao": "asc"}
    ).json()
    # Sem nome, ordena pelo e-mail ("carla@..." entre Bruno e Davi).
    assert _ids(por_nome) == ["A", "B", "C", "D", "E", "G", "I"]
    # Dado ausente (decidido_em) vai sempre para o fim, em qualquer direção.
    for direcao in ("asc", "desc"):
        corpo = cliente.get(
            "/api/revisao/casos",
            params={"aba": "todos", "ordenar": "decidido_em", "direcao": direcao},
        ).json()
        assert sorted(_ids(corpo)[:2]) == ["C", "E"]


def test_ac503_paginacao() -> None:
    linhas = _linhas_sinteticas(7)
    filtros = FiltrosDaLista(aba="todos")

    pagina_2 = consultar_casos(linhas, filtros, "chegou_em", "asc", 2, 3)
    ultima = consultar_casos(linhas, filtros, "chegou_em", "asc", 3, 3)
    alem = consultar_casos(linhas, filtros, "chegou_em", "asc", 4, 3)

    assert [x.CASO_ID for x in pagina_2.linhas] == ["C3", "C4", "C5"]
    assert [x.CASO_ID for x in ultima.linhas] == ["C6"]
    assert alem.linhas == () and alem.total == 7


def test_ac503_parametros_invalidos_dao_422(cliente: TestClient) -> None:
    for params in (
        {"por_pagina": "10"},
        {"pagina": "0"},
        {"aba": "outra"},
        {"ordenar": "senha"},
        {"de": "ontem"},
        {"parado_horas": "-1"},
        {"status": "COLETA_INICIAL_X"},
    ):
        assert cliente.get("/api/revisao/casos", params=params).status_code == 422, params
    corpo = cliente.get("/api/revisao/casos", params={"aba": "todos", "por_pagina": "50"}).json()
    assert corpo["por_pagina"] == 50 and corpo["pagina"] == 1


def test_ac503_consultas_em_lote(cliente: TestClient, cenario: _Cenario) -> None:
    antes = (cenario.eventos.consultas, cenario.revisoes.consultas)
    cliente.get("/api/revisao/casos", params={"aba": "todos"})
    assert (cenario.eventos.consultas - antes[0], cenario.revisoes.consultas - antes[1]) == (1, 1)


# --------------------------------------------------------------------- AC-504


def test_ac504_chegada_do_caso_devolvido_e_reenviado_e_a_ultima(cliente: TestClient) -> None:
    corpo = cliente.get("/api/revisao/casos", params={"aba": "todos"}).json()
    d = next(i for i in corpo["itens"] if i["CASO_ID"] == "CASO-D")

    assert d["chegou_em"] == _dias(3).isoformat()
    assert d["chegada_aproximada"] is False
    assert d["tempo_na_fila_horas"] == 72
    assert d["revisor"] is None  # voltou à fila: a decisão antiga não é a vigente


def test_ac504_decidido_conta_ate_a_decisao_e_sem_evento_e_aproximado(
    cliente: TestClient,
) -> None:
    por_id = {
        i["CASO_ID"]: i
        for i in cliente.get("/api/revisao/casos", params={"aba": "todos"}).json()["itens"]
    }

    assert por_id["CASO-C"]["tempo_na_fila_horas"] == 24  # 10 dias -> 9 dias
    assert por_id["CASO-E"]["tempo_na_fila_horas"] == 24
    assert por_id["CASO-G"]["tempo_na_fila_horas"] is None
    i = por_id["CASO-I"]
    assert i["chegada_aproximada"] is True
    assert i["chegou_em"] == _dias(1).isoformat()
    assert all(
        v["chegada_aproximada"] is False for k, v in por_id.items() if k != "CASO-I"
    )


# --------------------------------------------------------------------- AC-505


def test_ac505_pendente_com_5_dias_e_destacado_e_menos_nao(cliente: TestClient) -> None:
    corpo = cliente.get("/api/revisao/casos", params={"aba": "todos"}).json()
    atrasado = {i["CASO_ID"]: i["atrasado"] for i in corpo["itens"]}

    assert atrasado["CASO-A"] is True  # 6 dias
    assert atrasado["CASO-B"] is False  # 2 dias
    assert atrasado["CASO-C"] is False  # decidido nunca é "atrasado"
    assert atrasado["CASO-G"] is False

    parados = cliente.get(
        "/api/revisao/casos", params={"aba": "pendentes", "parado_horas": "120"}
    ).json()
    assert _ids(parados) == ["A"]


# --------------------------------------------------------------------- AC-507


def test_ac507_rota_antiga_da_fila_segue_igual(cliente: TestClient) -> None:
    corpo = cliente.get("/api/revisao/fila").json()

    assert sorted(i["CASO_ID"] for i in corpo["itens"]) == ["CASO-A", "CASO-B", "CASO-D", "CASO-I"]
    assert set(corpo) == {"itens"}


# ------------------------------------------------------------------- apoio


def _linhas_sinteticas(quantas: int) -> tuple[LinhaDoCaso, ...]:
    """Linhas montadas à mão só para a paginação."""
    modelo = _modelo_de_snapshot()
    return tuple(
        LinhaDoCaso(
            CASO_ID=f"C{n}",
            nome=None,
            email=None,
            chegou_em=_dias(30 - n),
            chegada_aproximada=False,
            tempo_na_fila_horas=0,
            atrasado=False,
            status=ESTADO_CASO.AGUARDANDO_REVISAO,
            item=montar_item_da_fila(f"C{n}", modelo),
            e_recalculo=False,
            motivo="SEM_EVENTO_PRIMEIRO_CALCULO",
            mes_negativo=False,
            dividas=1,
            metodo="AVALANCHE",
            revisor=None,
            decidido_em=None,
        )
        for n in range(quantas)
    )


_MODELO: list[Any] = []


def _modelo_de_snapshot() -> Any:
    if not _MODELO:
        pasta = Path(tempfile.mkdtemp())
        casos = RepositorioCasosArquivo(pasta / "c.jsonl")
        _criar_caso(casos, "M", "conta-M")
        _MODELO.append(
            _calcular_snapshot(
                "M",
                casos,
                RepositorioSnapshotsArquivo(pasta / "s.jsonl"),
                RepositorioEventosCasoArquivo(pasta / "e.jsonl"),
                estado_anterior=ESTADO_CASO.COLETA_INICIAL,
            )
        )
    return _MODELO[0]
