"""`POST /api/revisao/caso/{CASO_ID_REVISAO}/ordem` — o revisor ajusta a ordem
de ataque na conferência (`RF-546`, `RF-547`, `RF-548`, `RF-549`; `T-586`,
`T-587`, `T-590`) · plano `R18.9`.

O fluxo pelas rotas reais, com a coleção real e dublês de arquivo/memória
(padrão de `test_rotas_revisao_decisao.py` e `test_correcao_pedida.py`): o
aluno envia (`POST /caso/{id}/calculo`), o revisor ajusta, confere e decide.
Perfil T02 de `test_plano_ponta_a_ponta.py` com uma terceira dívida. Sessões
reais nas duas pontas: a guarda de papel não é sobrescrita, só o repositório
de contas que ela consulta.

REGRAS: `RF-546`, `RF-547`, `RF-548`, `RF-549`, `AC-563`–`AC-570`, `AC-572`,
`EC-80`–`EC-82`, `EC-84`
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.casos.maquina import ESTADO_CASO, Caso
from app.http import rotas_api_plano, rotas_plano
from app.http.aplicacao import criar_aplicacao
from app.http.edicao import MENSAGEM_FORA_DA_CONFERENCIA
from app.http.isolamento import obter_repositorio_casos, obter_repositorio_contas_para_papel
from app.http.rotas_api_plano import obter_emails_dos_alunos
from app.http.rotas_calculo import (
    obter_colecao_de_registros,
    obter_fonte_parametros,
    obter_parametros_externos_do_bloco6,
    obter_repositorio_eventos,
    obter_repositorio_itens,
    obter_repositorio_respostas,
    obter_repositorio_snapshots,
)
from app.http.rotas_coleta import obter_colecao_de_registros as obter_colecao_da_coleta
from app.http.rotas_coleta import obter_repositorio_itens as obter_repositorio_itens_da_coleta
from app.http.rotas_coleta import (
    obter_repositorio_respostas as obter_repositorio_respostas_da_coleta,
)
from app.http.rotas_inicio import (
    obter_colecao_de_registros_do_inicio,
    obter_repositorio_itens_do_inicio,
    obter_repositorio_respostas_do_inicio,
    obter_repositorio_revisoes_do_inicio,
)
from app.http.rotas_plano import obter_contas_dos_casos
from app.http.rotas_plano import obter_repositorio_snapshots as obter_repositorio_snapshots_do_aluno
from app.http.rotas_respostas import obter_repositorio_eventos_da_retomada
from app.http.rotas_revisao import (
    obter_colecao_de_registros_da_revisao,
    obter_repositorio_casos_da_fila,
    obter_repositorio_eventos_da_decisao,
    obter_repositorio_itens_da_revisao,
    obter_repositorio_respostas_da_revisao,
    obter_repositorio_revisoes_da_decisao,
    obter_repositorio_snapshots_da_fila,
)
from app.http.sessao import iniciar_sessao_conta
from app.montagem.conversao import converter_para_dinheiro, converter_para_taxa
from app.motor import executor
from app.notificacao.email import obter_enviador
from app.revisao.fila import RegistroRevisao
from app.revisao.ordem_do_revisor import TIPO_EVENTO_AJUSTE_DA_ORDEM, ordem_vigente
from collection.carga import carregar_registros
from collection.respostas import Resposta, ValorResposta
from engine.ciclo_mensal import ErroInvariante
from engine.estado import EstadoFinanceiro
from engine.motor import calcular_plano
from engine.parametros import ErroParametros, Parametros
from engine.snapshot import SnapshotOrdem
from persistencia.app_aluno.arquivo import RepositorioCasosArquivo, RepositorioEventosCasoArquivo
from persistencia.app_aluno.contas import Conta
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from persistencia.arquivo.repositorio_snapshots import RepositorioSnapshotsArquivo
from report.pdf import gerar_html_do_plano_liberado
from tests.app_aluno.fixtures.caso_completo import CASO_ID, DATA_REFERENCIA, montar_respostas_caso
from tests.app_aluno.test_plano_ponta_a_ponta import _T02_CASO, _T02_D001, _T02_D002, _itens
from tests.app_aluno.test_rotas_calculo import (
    _ParametrosExternosFabricados,
    _RepositorioItensDublê,
)
from tests.invariantes.test_gab04_estabilizacao import _estado_gab04
from tests.regras.test_ordem_do_revisor import (
    _estado,
    _estado_ac555,
    _estado_com_divida_bloqueada,
    _estado_ec80,
)

_CHAVE_TESTE = "chave-de-teste-para-assinatura-de-sessao-nao-usar-em-producao"
CONTA_ALUNO = "CONTA-ALUNO-ORDEM"
CONTA_REVISOR = "CONTA-REVISOR-ORDEM"
MOTIVO = "MOTIVO-INTERNO-negativada-primeiro"
DIVIDAS = ("D001", "D002", "D003")
_D003: dict[str, object] = {
    **_T02_D002,
    "SALDO_DEVEDOR_ATUAL": converter_para_dinheiro("3.000,00"),
    "TAXA_DIVIDA": converter_para_taxa("4"),
}


def respostas_com_tres_dividas() -> list[Resposta]:
    """T02 (cartão rotativo e empréstimo pessoal) mais um segundo pessoal."""
    fichas = {"D002": _T02_D002, "D003": _D003}
    base = montar_respostas_caso(
        valores_caso={**_T02_CASO, "QUANTIDADE_DIVIDAS_DECLARADA_INICIAL": len(DIVIDAS)},
        valores_divida=_T02_D001,
        valores_item_despesa={"VALOR_DESPESA": converter_para_dinheiro("3.500,00")},
        valores_despesa_nao_mensal={
            "VALOR_DESPESA_NAO_MENSAL": converter_para_dinheiro("1.200,00")
        },
        DIVIDA_ID="D001",
    ).respostas
    outras = tuple(
        r
        for divida_id, valores in fichas.items()
        for r in montar_respostas_caso(valores_divida=valores, DIVIDA_ID=divida_id).respostas
        if r.item_id == divida_id
    )
    return [*base, *outras]


class Respostas:
    """Dublê mutável de respostas: o teste troca a lista entre envios."""

    def __init__(self, respostas: list[Resposta]) -> None:
        self.respostas = respostas

    def listar_do_caso(self, caso_id: str) -> tuple[Resposta, ...]:
        return tuple(self.respostas)

    def trocar(self, item_id: str, valores: dict[str, ValorResposta]) -> None:
        """O aluno muda respostas da ficha `item_id` (`RF-69`)."""
        modelo = next(r for r in self.respostas if r.item_id == item_id)
        self.respostas = [
            r for r in self.respostas if not (r.item_id == item_id and r.ID_PERGUNTA in valores)
        ] + [
            replace(modelo, ID_PERGUNTA=variavel, valor=valor)
            for variavel, valor in valores.items()
        ]


class Revisoes:
    """Dublê em memória de `RepositorioRevisoes`, append-only."""

    def __init__(self) -> None:
        self.registros: list[RegistroRevisao] = []

    def gravar(self, revisao_id: str, registro: RegistroRevisao) -> None:
        self.registros.append(registro)

    def listar_do_caso(self, caso_id: str) -> tuple[RegistroRevisao, ...]:
        return tuple(r for r in self.registros if r.CASO_ID == caso_id)


class FonteQueRegistra:
    """`AC-563`: guarda a versão de parâmetros que cada carga pediu."""

    def __init__(self) -> None:
        self.versoes: list[str] = []

    def carregar(self, versao: str) -> Parametros:
        self.versoes.append(versao)
        return FonteParametrosArquivo().carregar(versao)


class Contas:
    """O recorte de `RepositorioContas` que a guarda de papel e o aviso de
    liberação usam."""

    def buscar_por_id(self, conta_id: str) -> Conta | None:
        if conta_id not in (CONTA_ALUNO, CONTA_REVISOR):
            return None
        return Conta(
            conta_id=conta_id,
            email=f"{conta_id}@teste.invalido",
            senha_hash="nao-usado",
            criado_em=datetime(2026, 1, 1, tzinfo=UTC),
            e_revisor=conta_id == CONTA_REVISOR,
        )


@dataclass
class Cenario:
    aplicacao: FastAPI
    aluno: TestClient
    revisor: TestClient
    casos: RepositorioCasosArquivo
    snapshots: RepositorioSnapshotsArquivo
    eventos: RepositorioEventosCasoArquivo
    respostas: Respostas
    revisoes: Revisoes
    fonte: FonteQueRegistra
    dividas: list[str] = field(default_factory=lambda: list(DIVIDAS))

    def caso(self) -> Caso:
        caso = self.casos.buscar(CASO_ID)
        assert caso is not None
        return caso

    def historico(self) -> tuple[SnapshotOrdem, ...]:
        raiz = self.caso().snapshot_raiz_id
        return () if raiz is None else tuple(self.snapshots.historico(raiz))

    def enviar(self) -> SnapshotOrdem:
        """O aluno envia para a conferência e espera o cálculo."""
        with self.aluno:  # mantém o loop vivo para a asyncio.Task do cálculo
            assert self.aluno.post(f"/caso/{CASO_ID}/calculo").status_code == 200
            # ponytail: polling — o cálculo roda numa asyncio.Task do TestClient.
            prazo = time.monotonic() + 30
            while self.caso().estado is ESTADO_CASO.CALCULANDO:
                assert time.monotonic() < prazo, "caso ficou em CALCULANDO"
                time.sleep(0.05)
        assert self.caso().estado is ESTADO_CASO.AGUARDANDO_REVISAO
        return self.historico()[-1]

    def instalar(self, snapshot: SnapshotOrdem) -> SnapshotOrdem:
        """Põe na conferência um snapshot calculado direto pelo motor — para as
        carteiras da suíte do motor que a coleta não monta (`EC-80`, `EC-84`).
        A rota de ajuste só lê o snapshot, nunca as respostas."""
        self.snapshots.anexar(snapshot)
        self.casos.registrar_snapshot_raiz(CASO_ID, snapshot.SNAPSHOT_ID)
        self.casos.transicionar_estado(CASO_ID, ESTADO_CASO.AGUARDANDO_REVISAO)
        return snapshot

    def ajustar(self, ordem: list[str], motivo: str = MOTIVO) -> Any:
        return self.revisor.post(
            f"/api/revisao/caso/{CASO_ID}/ordem", json={"ordem": ordem, "motivo": motivo}
        )

    def decidir(self, corpo: str) -> Any:
        return self.revisor.post(
            f"/revisao/caso/{CASO_ID}/decisao",
            content=corpo,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

    def eventos_de_ajuste(self) -> list[dict[str, Any]]:
        return [
            json.loads(e.detalhe or "{}")
            for e in self.eventos.listar_do_caso(CASO_ID)
            if e.tipo_evento == TIPO_EVENTO_AJUSTE_DA_ORDEM
        ]


def _cliente(aplicacao: FastAPI, conta_id: str | None) -> TestClient:
    cliente = TestClient(aplicacao, base_url="https://teste.local")
    if conta_id is not None:
        cliente.post(f"/_teste/abrir-sessao/{conta_id}")
    return cliente


@pytest.fixture
def cenario(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Cenario:
    monkeypatch.setenv("CHAVE_ASSINATURA_SESSAO", _CHAVE_TESTE)
    monkeypatch.setenv("PARAMETROS_VERSION_VIGENTE", "1.0.1")
    # Sem banco: a data da liberação cai no "sem dado". Trocada direto porque,
    # com um pool já aberto por outra suíte, a leitura esperaria a conexão.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for modulo in (rotas_api_plano, rotas_plano):
        monkeypatch.setattr(modulo, "data_da_liberacao", lambda *_args: None)
    casos = RepositorioCasosArquivo(tmp_path / "casos.jsonl")
    agora = datetime(2026, 1, 1, tzinfo=UTC)
    casos.criar(
        Caso(
            CASO_ID=CASO_ID,
            conta_id=CONTA_ALUNO,
            estado=ESTADO_CASO.COLETA_INICIAL,
            DATA_REFERENCIA=DATA_REFERENCIA,
            QUESTIONARIO_VERSION="1.0.0",
            snapshot_raiz_id=None,
            snapshot_liberado_id=None,
            ultima_interacao_em=agora,
            criado_em=agora,
        )
    )
    snapshots = RepositorioSnapshotsArquivo(tmp_path / "snapshots.jsonl")
    eventos = RepositorioEventosCasoArquivo(tmp_path / "eventos.jsonl")
    respostas = Respostas(respostas_com_tres_dividas())
    revisoes = Revisoes()
    fonte = FonteQueRegistra()
    colecao = carregar_registros()
    sem_contas = SimpleNamespace(
        emails_dos_casos=lambda _ids: {}, contas_dos_casos=lambda _ids: {}
    )

    dividas = list(DIVIDAS)

    def itens() -> _RepositorioItensDublê:
        return _RepositorioItensDublê(_itens(tuple(dividas)))

    aplicacao = criar_aplicacao()
    sobrescritas: dict[Callable[..., Any], Callable[..., Any]] = {
        obter_repositorio_casos: lambda: casos,
        obter_repositorio_casos_da_fila: lambda: casos,
        obter_colecao_de_registros: lambda: colecao,
        obter_colecao_de_registros_do_inicio: lambda: colecao,
        obter_colecao_de_registros_da_revisao: lambda: colecao,
        obter_colecao_da_coleta: lambda: colecao,
        obter_repositorio_respostas: lambda: respostas,
        obter_repositorio_respostas_do_inicio: lambda: respostas,
        obter_repositorio_respostas_da_revisao: lambda: respostas,
        obter_repositorio_respostas_da_coleta: lambda: respostas,
        obter_repositorio_itens: itens,
        obter_repositorio_itens_do_inicio: itens,
        obter_repositorio_itens_da_revisao: itens,
        obter_repositorio_itens_da_coleta: itens,
        obter_repositorio_snapshots: lambda: snapshots,
        obter_repositorio_snapshots_do_aluno: lambda: snapshots,
        obter_repositorio_snapshots_da_fila: lambda: snapshots,
        obter_repositorio_eventos: lambda: eventos,
        obter_repositorio_eventos_da_decisao: lambda: eventos,
        obter_repositorio_eventos_da_retomada: lambda: eventos,
        obter_repositorio_revisoes_da_decisao: lambda: revisoes,
        obter_repositorio_revisoes_do_inicio: lambda: revisoes,
        obter_fonte_parametros: lambda: fonte,
        obter_parametros_externos_do_bloco6: _ParametrosExternosFabricados,
        obter_repositorio_contas_para_papel: Contas,
        obter_emails_dos_alunos: lambda: sem_contas,
        obter_contas_dos_casos: lambda: sem_contas,
        obter_enviador: lambda: SimpleNamespace(enviar=lambda *_args: None),
    }
    aplicacao.dependency_overrides.update(sobrescritas)

    @aplicacao.post("/_teste/abrir-sessao/{conta_id}")
    def abrir_sessao(request: Request, conta_id: str) -> dict[str, str]:
        iniciar_sessao_conta(request, conta_id=conta_id)
        return {"ok": "ok"}

    return Cenario(
        aplicacao=aplicacao,
        aluno=_cliente(aplicacao, CONTA_ALUNO),
        revisor=_cliente(aplicacao, CONTA_REVISOR),
        casos=casos,
        snapshots=snapshots,
        eventos=eventos,
        respostas=respostas,
        revisoes=revisoes,
        fonte=fonte,
        dividas=dividas,
    )


def _ids(snapshot: SnapshotOrdem) -> tuple[str, ...]:
    return tuple(p.DIVIDA_ID for p in snapshot.ORDEM_QUITACAO)


def _custo_na_homologacao(cenario: Cenario) -> dict[str, Any]:
    """O item da homologação, como a tela de decisão o mostra — sobre o
    snapshot mais recente."""
    corpo = cenario.revisor.get(f"/revisao/caso/{CASO_ID}/decisao").json()
    item = corpo["homologacao"]["itens"]["custo_total_de_juros"]
    return {"valor": item["valor"], "motivo": item["motivo"]}


def _prazo(snapshot: SnapshotOrdem) -> dict[str, object]:
    cenario = snapshot.cenarios[snapshot.METODO_RECOMENDADO_PIQ]
    return {"meses": cenario.PRAZO_TOTAL, "estourou_horizonte": cenario.ESTOUROU_HORIZONTE}


_LISTA = ["D003", "D001", "D002"]
_NADA_A_RECALCULAR = "Esta já é a ordem vigente. Nada a recalcular."


# --- T-586: ajuste aceito, volta e trilha ---


def test_ac563_ajuste_aceito_encadeia_v2_com_a_lista_e_os_dados_da_v1(
    cenario: Cenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    v1 = cenario.enviar()
    assert ordem_vigente(v1) == (DIVIDAS, False)
    custo_v1 = _custo_na_homologacao(cenario)
    # `OQ-100`: outra versão vigente não entra no ajuste.
    monkeypatch.setenv("PARAMETROS_VERSION_VIGENTE", "1.0.2")
    cenario.fonte.versoes.clear()

    resposta = cenario.ajustar(_LISTA)

    assert resposta.status_code == 200
    v1_gravada, v2 = cenario.historico()
    assert v1_gravada == v1
    assert v2.snapshot_anterior_id == v1.SNAPSHOT_ID
    assert v2.versao == 2
    assert v2.estado_inputs == v1.estado_inputs
    assert v2.PARAMETROS_VERSION == v1.PARAMETROS_VERSION == "1.0.1"
    assert cenario.fonte.versoes == ["1.0.1"]
    assert v2.ORDEM_DO_REVISOR == tuple(_LISTA)
    assert cenario.caso().estado is ESTADO_CASO.AGUARDANDO_REVISAO
    fila = cenario.revisor.get("/api/revisao/fila").json()["itens"]
    assert [item["CASO_ID"] for item in fila] == [CASO_ID]
    corpo = resposta.json()
    assert corpo == {
        "CASO_ID": CASO_ID,
        "SNAPSHOT_ID": v2.SNAPSHOT_ID,
        "versao": 2,
        "ordem_vigente": _LISTA,
        "ajustada": True,
        "antes": {
            "SNAPSHOT_ID": v1.SNAPSHOT_ID,
            "prazo": _prazo(v1),
            "custo_total_de_juros": custo_v1,
        },
        "depois": {
            "SNAPSHOT_ID": v2.SNAPSHOT_ID,
            "prazo": _prazo(v2),
            "custo_total_de_juros": _custo_na_homologacao(cenario),
        },
    }
    assert corpo["antes"]["custo_total_de_juros"] != corpo["depois"]["custo_total_de_juros"]


def test_ac564_lista_vazia_sem_motivo_volta_a_ordem_do_metodo(cenario: Cenario) -> None:
    v1 = cenario.enviar()
    ajuste = cenario.ajustar(_LISTA).json()

    resposta = cenario.ajustar([], motivo="")

    assert resposta.status_code == 200
    *_, v3 = cenario.historico()
    assert v3.versao == 3
    assert v3.ORDEM_DO_REVISOR is None
    assert _ids(v3) == _ids(v1)
    corpo = resposta.json()
    assert (corpo["ordem_vigente"], corpo["ajustada"]) == (list(DIVIDAS), False)
    assert corpo["depois"]["prazo"] == ajuste["antes"]["prazo"]
    assert corpo["depois"]["custo_total_de_juros"] == ajuste["antes"]["custo_total_de_juros"]
    assert cenario.caso().estado is ESTADO_CASO.AGUARDANDO_REVISAO


def test_ac568_o_ajuste_fica_na_trilha_sem_mudar_o_estado(cenario: Cenario) -> None:
    v1 = cenario.enviar()
    antes = datetime.now(UTC)

    assert cenario.ajustar(_LISTA).status_code == 200

    v2 = cenario.historico()[-1]
    (evento,) = [
        e
        for e in cenario.eventos.listar_do_caso(CASO_ID)
        if e.tipo_evento == TIPO_EVENTO_AJUSTE_DA_ORDEM
    ]
    assert (evento.estado_de, evento.estado_para) == (None, None)
    assert antes <= evento.ocorrido_em <= datetime.now(UTC)
    assert cenario.eventos_de_ajuste() == [
        {
            "ordem_anterior": list(DIVIDAS),
            "ordem_nova": _LISTA,
            "motivo": MOTIVO,
            "autor": CONTA_REVISOR,
            "snapshot_anterior_id": v1.SNAPSHOT_ID,
            "snapshot_novo_id": v2.SNAPSHOT_ID,
        }
    ]
    assert cenario.caso().estado is ESTADO_CASO.AGUARDANDO_REVISAO


def test_ac568_a_volta_registra_a_ordem_do_metodo_e_motivo_vazio(cenario: Cenario) -> None:
    cenario.enviar()
    cenario.ajustar(_LISTA)

    cenario.ajustar([], motivo="")

    volta = cenario.eventos_de_ajuste()[-1]
    assert (volta["ordem_anterior"], volta["ordem_nova"], volta["motivo"]) == (
        _LISTA,
        list(DIVIDAS),
        "",
    )


def test_ac568_o_motivo_nao_vai_para_log_nem_para_rota_de_aluno(
    cenario: Cenario, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    cenario.enviar()
    with caplog.at_level(logging.DEBUG):
        assert cenario.ajustar(_LISTA).status_code == 200
        assert cenario.decidir("decisao=LIBERAR").status_code == 200
    assert caplog.records
    assert all(MOTIVO not in str(registro.__dict__) for registro in caplog.records)
    # O PDF do aluno pelo HTML que ele imprime (`OQ-09`: a mesma montagem).
    monkeypatch.setattr(
        rotas_plano,
        "gerar_pdf_do_plano",
        lambda *args: gerar_html_do_plano_liberado(*args).encode(),
    )

    for rota in ("api/plano", "inicio", "plano/pdf"):
        resposta = cenario.aluno.get(f"/caso/{CASO_ID}/{rota}")
        assert resposta.status_code == 200, rota
        assert MOTIVO not in resposta.text, rota
    plano = cenario.aluno.get(f"/caso/{CASO_ID}/api/plano").json()["plano"]
    assert [p["DIVIDA_ID"] for p in plano["ordem"]] == list(_ids(cenario.historico()[-1]))


# --- T-587: recusas — nada anexado, nada gravado, estado como estava ---


def _nada_mudou(
    cenario: Cenario, historico: tuple[SnapshotOrdem, ...], estado: ESTADO_CASO
) -> None:
    assert cenario.historico() == historico
    assert cenario.eventos_de_ajuste() == []
    assert cenario.caso().estado is estado


@pytest.mark.parametrize(
    "estado", [e for e in ESTADO_CASO if e is not ESTADO_CASO.AGUARDANDO_REVISAO], ids=str
)
def test_ac565_fora_da_conferencia_responde_409(cenario: Cenario, estado: ESTADO_CASO) -> None:
    """`AC-565` cita `ACOMPANHAMENTO`, que a máquina de estados não tem mais:
    todo estado diferente de `AGUARDANDO_REVISAO` é recusado."""
    cenario.enviar()
    cenario.casos.transicionar_estado(CASO_ID, estado)
    historico = cenario.historico()

    resposta = cenario.ajustar(_LISTA)

    assert resposta.status_code == 409
    if estado is ESTADO_CASO.COLETA_INICIAL:
        assert resposta.json()["detail"] == MENSAGEM_FORA_DA_CONFERENCIA
    _nada_mudou(cenario, historico, estado)


@pytest.mark.parametrize(
    ("ordem", "motivo"),
    [
        pytest.param(list(DIVIDAS), MOTIVO, id="a-propria-vigente"),
        pytest.param([], "", id="lista-vazia-na-ordem-do-metodo"),
    ],
)
def test_ac565_nada_a_recalcular_na_v1(cenario: Cenario, ordem: list[str], motivo: str) -> None:
    cenario.enviar()
    historico = cenario.historico()

    resposta = cenario.ajustar(ordem, motivo)

    assert (resposta.status_code, resposta.json()["detail"]) == (409, _NADA_A_RECALCULAR)
    _nada_mudou(cenario, historico, ESTADO_CASO.AGUARDANDO_REVISAO)


def test_ac565_nada_a_recalcular_com_a_mesma_lista_na_v2(cenario: Cenario) -> None:
    cenario.enviar()
    cenario.ajustar(_LISTA)
    historico = cenario.historico()
    eventos = cenario.eventos_de_ajuste()

    resposta = cenario.ajustar(_LISTA)

    assert (resposta.status_code, resposta.json()["detail"]) == (409, _NADA_A_RECALCULAR)
    assert cenario.historico() == historico
    assert cenario.eventos_de_ajuste() == eventos


@pytest.mark.parametrize(
    ("ordem", "causa"),
    [
        pytest.param(["D001", "D001", "D002", "D003"], "repetida", id="repetida"),
        pytest.param(["D001", "D002"], "faltando", id="faltando"),
        pytest.param(["D001", "D002", "D003", "D009"], "D009", id="inexistente"),
    ],
)
def test_ac566_lista_que_nao_e_permutacao_responde_422_com_a_causa(
    cenario: Cenario, ordem: list[str], causa: str
) -> None:
    cenario.enviar()
    historico = cenario.historico()

    resposta = cenario.ajustar(ordem)

    assert resposta.status_code == 422
    assert causa in resposta.json()["detail"]
    _nada_mudou(cenario, historico, ESTADO_CASO.AGUARDANDO_REVISAO)


def test_ac566_divida_bloqueada_por_gate_responde_422(cenario: Cenario) -> None:
    """`D004` sem saldo, bloqueada pelo Gate 1. Pela coleta a dívida pendente
    nem chega ao motor (`T-499`), então o snapshot vem da carteira do motor."""
    v1 = cenario.instalar(
        calcular_plano(_estado_com_divida_bloqueada(), FonteParametrosArquivo().carregar("1.0.1"))
    )
    assert "D004" in {d.DIVIDA_ID for d in v1.estado_inputs.dividas}
    assert "D004" not in _ids(v1)

    resposta = cenario.ajustar([*_ids(v1), "D004"])

    assert resposta.status_code == 422
    assert "D004" in resposta.json()["detail"]
    _nada_mudou(cenario, (v1,), ESTADO_CASO.AGUARDANDO_REVISAO)


def test_ac566_lista_nao_vazia_sem_motivo_responde_422(cenario: Cenario) -> None:
    cenario.enviar()
    historico = cenario.historico()

    resposta = cenario.ajustar(_LISTA, motivo="   ")

    assert (resposta.status_code, resposta.json()["detail"]) == (422, "Escreva o motivo interno.")
    _nada_mudou(cenario, historico, ESTADO_CASO.AGUARDANDO_REVISAO)


def test_ac567_sem_sessao_401_e_sessao_de_aluno_403(cenario: Cenario) -> None:
    cenario.enviar()
    historico = cenario.historico()
    corpo = {"ordem": _LISTA, "motivo": MOTIVO}
    rota = f"/api/revisao/caso/{CASO_ID}/ordem"

    assert _cliente(cenario.aplicacao, None).post(rota, json=corpo).status_code == 401
    # Inclusive o dono do caso.
    assert cenario.aluno.post(rota, json=corpo).status_code == 403
    _nada_mudou(cenario, historico, ESTADO_CASO.AGUARDANDO_REVISAO)


def test_ac567_caso_inexistente_ou_sem_snapshot_404(cenario: Cenario) -> None:
    corpo = {"ordem": _LISTA, "motivo": MOTIVO}

    assert cenario.revisor.post("/api/revisao/caso/NAO-EXISTE/ordem", json=corpo).status_code == 404
    assert cenario.ajustar(_LISTA).status_code == 404
    _nada_mudou(cenario, (), ESTADO_CASO.COLETA_INICIAL)


@pytest.mark.parametrize(
    ("estado", "esperada"),
    [
        pytest.param(_estado_ac555, ("D001", "D002", "D003"), id="tres-dividas"),
        # ordem de ataque diferente da ORDEM_QUITACAO publicada
        pytest.param(_estado_ec80, ("D001", "D002", "D003"), id="ataque-diferente-da-quitacao"),
        pytest.param(
            lambda: _estado("4800", ("D001", "2000", "0.02", "200")), ("D001",), id="uma-divida"
        ),
    ],
)
def test_ec80_ec84_lista_igual_a_ordem_de_ataque_vigente_responde_409(
    cenario: Cenario, estado: Callable[[], EstadoFinanceiro], esperada: tuple[str, ...]
) -> None:
    v1 = cenario.instalar(calcular_plano(estado(), FonteParametrosArquivo().carregar("1.0.1")))
    assert ordem_vigente(v1) == (esperada, False)

    resposta = cenario.ajustar(list(esperada))

    assert (resposta.status_code, resposta.json()["detail"]) == (409, _NADA_A_RECALCULAR)
    _nada_mudou(cenario, (v1,), ESTADO_CASO.AGUARDANDO_REVISAO)


class _CasosQueOAlunoRetiraNoMeio:
    """`EC-81`: entre a 1ª e a 2ª leitura o aluno retira o plano (`RF-115`)."""

    def __init__(self, casos: RepositorioCasosArquivo) -> None:
        self._casos = casos
        self._leituras = 0

    def buscar(self, caso_id: str) -> Caso | None:
        self._leituras += 1
        if self._leituras == 2:
            self._casos.transicionar_estado(caso_id, ESTADO_CASO.COLETA_INICIAL)
        return self._casos.buscar(caso_id)


def test_ec81_aluno_retira_o_plano_durante_o_calculo_responde_409(cenario: Cenario) -> None:
    cenario.enviar()
    historico = cenario.historico()
    cenario.aplicacao.dependency_overrides[obter_repositorio_casos_da_fila] = (
        lambda: _CasosQueOAlunoRetiraNoMeio(cenario.casos)
    )

    resposta = cenario.ajustar(_LISTA)

    assert (resposta.status_code, resposta.json()["detail"]) == (
        409,
        MENSAGEM_FORA_DA_CONFERENCIA,
    )
    _nada_mudou(cenario, historico, ESTADO_CASO.COLETA_INICIAL)


class _FonteQueFalha:
    def carregar(self, versao: str) -> Parametros:
        raise ErroParametros(f"versão {versao} recusada")


def _invariante_quebrada(*_args: object, **_kwargs: object) -> SnapshotOrdem:
    raise ErroInvariante("conservação do ataque não fecha")


@pytest.mark.parametrize("falha", ["parametros", "invariante"])
def test_ec82_falha_do_motor_responde_500_e_o_plano_nao_muda(
    cenario: Cenario, monkeypatch: pytest.MonkeyPatch, falha: str
) -> None:
    cenario.enviar()
    historico = cenario.historico()
    if falha == "parametros":
        cenario.aplicacao.dependency_overrides[obter_fonte_parametros] = _FonteQueFalha
    else:
        monkeypatch.setattr(executor, "calcular_plano", _invariante_quebrada)

    resposta = cenario.ajustar(_LISTA)

    assert (resposta.status_code, resposta.json()["detail"]) == (
        500,
        "Não foi possível recalcular. O plano não mudou.",
    )
    _nada_mudou(cenario, historico, ESTADO_CASO.AGUARDANDO_REVISAO)


# --- T-590: a conferência depois do ajuste ---


def _ordem_na_conferencia(cenario: Cenario) -> dict[str, Any]:
    resposta = cenario.revisor.get(f"/api/revisao/caso/{CASO_ID}")
    assert resposta.status_code == 200
    ordem: dict[str, Any] = resposta.json()["ordem_do_revisor"]
    return ordem


def test_ac569_ordem_vigente_pelo_nome_do_plano_editavel_na_conferencia(
    cenario: Cenario,
) -> None:
    cenario.enviar()
    corpo = cenario.revisor.get(f"/api/revisao/caso/{CASO_ID}").json()
    nomes = {p["DIVIDA_ID"]: p["nome"] for p in corpo["plano"]["ordem"]}
    assert all(nome != divida_id for divida_id, nome in nomes.items())

    assert corpo["ordem_do_revisor"] == {
        "vigente": [{"DIVIDA_ID": d, "nome": nomes[d]} for d in DIVIDAS],
        "ajustada": False,
        "editavel": True,
    }

    cenario.ajustar(_LISTA)
    ordem = _ordem_na_conferencia(cenario)
    assert [p["DIVIDA_ID"] for p in ordem["vigente"]] == _LISTA
    assert [p["nome"] for p in ordem["vigente"]] == [nomes[d] for d in _LISTA]
    assert (ordem["ajustada"], ordem["editavel"]) == (True, True)


def test_ac569_sem_edicao_fora_da_conferencia(cenario: Cenario) -> None:
    cenario.enviar()
    assert cenario.decidir("decisao=LIBERAR").status_code == 200

    ordem = _ordem_na_conferencia(cenario)

    assert cenario.caso().estado is ESTADO_CASO.PLANO_LIBERADO
    assert ordem["editavel"] is False


@pytest.mark.parametrize(
    "estado",
    [
        pytest.param(_estado_gab04, id="estabilizacao"),
        pytest.param(lambda: _estado("4800", ("D001", "2000", "0.02", "200")), id="uma-divida"),
    ],
)
def test_ac569_sem_edicao_em_estabilizacao_e_com_uma_divida(
    cenario: Cenario, estado: Callable[[], EstadoFinanceiro]
) -> None:
    cenario.instalar(calcular_plano(estado(), FonteParametrosArquivo().carregar("1.0.1")))

    assert _ordem_na_conferencia(cenario)["editavel"] is False


def test_ac570_conferencia_homologacao_e_previa_recebem_a_v2(
    cenario: Cenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    previas: list[SnapshotOrdem] = []

    def previa(snapshot: SnapshotOrdem, *_args: object) -> bytes:
        previas.append(snapshot)
        return b"%PDF-previa"

    monkeypatch.setattr(rotas_api_plano, "gerar_pdf_de_previa", previa)
    cenario.enviar()

    assert cenario.ajustar(_LISTA).status_code == 200

    v2 = cenario.historico()[-1]
    plano = cenario.revisor.get(f"/api/revisao/caso/{CASO_ID}").json()["plano"]
    assert [p["DIVIDA_ID"] for p in plano["ordem"]] == list(_ids(v2))
    # A dívida da vez no Mês 01 é a primeira da lista.
    primeira = next(p for p in plano["ordem"] if p["DIVIDA_ID"] == _LISTA[0])
    recebe = next(f["valor"] for f in primeira["fatos"] if f["rotulo"] == "Recebe o valor extra")
    assert recebe == f"A partir de {plano['prognostico']['eixo_inicio']}"
    decisao = cenario.revisor.get(f"/revisao/caso/{CASO_ID}/decisao").json()
    assert decisao["SNAPSHOT_ID"] == v2.SNAPSHOT_ID
    assert cenario.revisor.get(f"/revisao/caso/{CASO_ID}/plano/pdf").status_code == 200
    (na_previa,) = previas
    assert na_previa == v2
    assert v2.prognostico is not None
    assert v2.prognostico.MESES_DO_PLANO[0].DIVIDA_ALVO == _LISTA[0]


def test_ac572_o_que_mudou_compara_os_envios_e_pula_o_ajuste(cenario: Cenario) -> None:
    """`AC-572` parte de um plano liberado que o aluno refez; desde `RF-409`
    (`enxugamento-questionario`) o plano entregue é definitivo e a v2 nasce
    quando o aluno retira o plano da conferência (`RF-115`) — o mesmo caminho
    de `test_ac192`."""
    cenario.enviar()
    cenario.respostas.trocar("D003", {"TAXA_DIVIDA": converter_para_taxa("8")})
    assert cenario.aluno.post(f"/caso/{CASO_ID}/retomar-edicao").status_code == 200
    cenario.enviar()
    assert cenario.ajustar(_LISTA).status_code == 200
    assert [s.versao for s in cenario.historico()] == [1, 2, 3]

    mudancas = cenario.revisor.get(f"/api/revisao/caso/{CASO_ID}").json()["mudancas"]

    assert mudancas is not None
    (taxa,) = [m for m in mudancas if m["situacao"] == "alterado"]
    assert "axa" in taxa["nome"]
    assert "4" in taxa["de"] and "8" in taxa["para"]
