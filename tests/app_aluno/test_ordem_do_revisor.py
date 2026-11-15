"""Leituras da ordem do revisor e o evento da trilha — `RF-546`, `RF-547`,
`RF-549` (`T-582`) · plano `R18.9`.

Snapshots REAIS de `calcular_plano` sobre as carteiras pequenas da suíte do
motor (`tests/regras/test_ordem_do_revisor.py`). Só o ramo da dívida que
recebe resíduo no mês em que quita usa um mês a mês trocado com
`dataclasses.replace`: nenhuma carteira conhecida o produz, e o que se testa
é a leitura do snapshot, não a simulação.

REGRAS: `RF-546`, `RF-547`, `RF-549`, `AC-568`, `AC-572`
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from app.casos.maquina import ESTADO_CASO
from app.revisao.fila import RegistroRevisao
from app.revisao.lista_de_casos import montar_linhas
from app.revisao.ordem_do_revisor import (
    TIPO_EVENTO_AJUSTE_DA_ORDEM,
    anterior_para_comparar,
    e_ajuste_da_ordem,
    ordem_vigente,
    registrar_ajuste_na_trilha,
)
from engine.motor import MOTIVO_AJUSTE_DA_ORDEM, calcular_plano
from engine.snapshot import SnapshotOrdem
from persistencia.app_aluno.arquivo import RepositorioCasosArquivo, RepositorioEventosCasoArquivo
from persistencia.app_aluno.eventos import EventoCaso
from persistencia.arquivo.repositorio_snapshots import RepositorioSnapshotsArquivo
from tests.app_aluno.test_rotas_revisao import _criar_caso
from tests.regras.test_ordem_do_revisor import (
    _LISTA,
    _estado,
    _estado_ac555,
    _estado_com_divida_bloqueada,
    _estado_ec80,
    _parametros,
)


def _ids(snapshot: SnapshotOrdem) -> tuple[str, ...]:
    return tuple(p.DIVIDA_ID for p in snapshot.ORDEM_QUITACAO)


# --- ordem_vigente: os quatro ramos (RF-546) ---


def test_ramo_1_a_lista_do_revisor_e_a_vigente_e_ajustada() -> None:
    com = calcular_plano(_estado_ac555(), _parametros(), ordem_do_revisor=_LISTA)

    assert ordem_vigente(com) == (_LISTA, True)


def test_ramo_2_com_estouro_vale_a_ordem_de_ataque_do_recomendado() -> None:
    sem = calcular_plano(
        _estado(
            "3000",
            ("D001", "3000", "0.02", "200"),
            ("D002", "5000", "0.03", "250"),
            ("D003", "8000", "0.01", "200"),
            ("D004", "300000", "0.005", "1600"),
        ),
        _parametros(),
    )
    cenario = sem.cenarios[sem.METODO_RECOMENDADO_PIQ]
    assert cenario.ESTOUROU_HORIZONTE

    assert ordem_vigente(sem) == (cenario.ORDEM_DE_ATAQUE, False)


def test_ramo_3_sem_estouro_as_dividas_da_vez_do_mes_a_mes() -> None:
    sem = calcular_plano(_estado_ac555(), _parametros())

    assert ordem_vigente(sem) == (("D001", "D002", "D003"), False)


def test_ramo_3_divida_que_termina_so_com_as_parcelas_vai_para_o_fim() -> None:
    """`D003` quita sozinha antes da vez: a ordem de ataque difere da
    `ORDEM_QUITACAO` publicada."""
    sem = calcular_plano(_estado_ec80(), _parametros())
    assert _ids(sem) == ("D001", "D003", "D002")

    assert ordem_vigente(sem) == (("D001", "D002", "D003"), False)


def test_ramo_3_divida_que_so_recebe_residuo_no_mes_em_que_quita_vai_para_o_fim() -> None:
    sem = calcular_plano(_estado_ac555(), _parametros())
    assert sem.prognostico is not None
    meses = sem.prognostico.MESES_DO_PLANO
    # `D002` quita no mesmo mês que `D001`, só com o resíduo: nunca é alvo.
    trocados = (
        replace(meses[0], DIVIDA_ALVO="D001", QUITACOES=()),
        replace(meses[1], DIVIDA_ALVO="D003", QUITACOES=("D001", "D002")),
        replace(meses[2], DIVIDA_ALVO=None, QUITACOES=("D003",)),
    )
    snapshot = replace(sem, prognostico=replace(sem.prognostico, MESES_DO_PLANO=trocados))

    assert ordem_vigente(snapshot) == (("D001", "D003", "D002"), False)


def test_ramo_3_fica_restrito_as_dividas_elegiveis() -> None:
    sem = calcular_plano(_estado_com_divida_bloqueada(), _parametros())
    assert "D004" not in _ids(sem)

    assert ordem_vigente(sem) == (("D001", "D002", "D003"), False)


def test_ramo_4_snapshot_sem_prognostico_le_a_ordem_quitacao() -> None:
    sem = calcular_plano(_estado_ec80(), _parametros())

    assert ordem_vigente(replace(sem, prognostico=None)) == (("D001", "D003", "D002"), False)


# --- e_ajuste_da_ordem (RF-549) ---


def test_e_ajuste_da_ordem_no_ajuste_e_na_volta_e_so_neles() -> None:
    estado, parametros = _estado_ac555(), _parametros()
    v1 = calcular_plano(estado, parametros)
    ajuste = calcular_plano(
        estado, parametros, anterior=v1, motivo=MOTIVO_AJUSTE_DA_ORDEM, ordem_do_revisor=_LISTA
    )
    volta = calcular_plano(estado, parametros, anterior=ajuste, motivo=MOTIVO_AJUSTE_DA_ORDEM)
    reenvio = calcular_plano(estado, parametros, anterior=volta, motivo="respostas atualizadas")

    assert volta.ORDEM_DO_REVISOR is None
    assert [e_ajuste_da_ordem(s) for s in (v1, ajuste, volta, reenvio)] == [
        False,
        True,
        True,
        False,
    ]


# --- anterior_para_comparar (AC-572, unitário) ---


def test_anterior_para_comparar_pula_os_ajustes() -> None:
    estado, parametros = _estado_ac555(), _parametros()
    v1 = calcular_plano(estado, parametros)
    v2 = calcular_plano(estado, parametros, anterior=v1)
    v3 = calcular_plano(
        estado, parametros, anterior=v2, motivo=MOTIVO_AJUSTE_DA_ORDEM, ordem_do_revisor=_LISTA
    )
    v4 = calcular_plano(estado, parametros, anterior=v3, motivo=MOTIVO_AJUSTE_DA_ORDEM)

    assert anterior_para_comparar((v1, v2)) is v1
    assert anterior_para_comparar((v1, v2, v3)) is v1
    assert anterior_para_comparar((v1, v2, v3, v4)) is v1


def test_anterior_para_comparar_none_com_menos_de_dois_envios() -> None:
    estado, parametros = _estado_ac555(), _parametros()
    v1 = calcular_plano(estado, parametros)
    v2 = calcular_plano(
        estado, parametros, anterior=v1, motivo=MOTIVO_AJUSTE_DA_ORDEM, ordem_do_revisor=_LISTA
    )

    assert anterior_para_comparar(()) is None
    assert anterior_para_comparar((v1,)) is None
    assert anterior_para_comparar((v1, v2)) is None


# --- registrar_ajuste_na_trilha (RF-547, AC-568) ---


def test_evento_do_ajuste_com_as_seis_chaves_e_sem_estados(tmp_path: Path) -> None:
    eventos = RepositorioEventosCasoArquivo(tmp_path / "eventos.jsonl")
    agora = datetime(2026, 11, 14, 12, tzinfo=UTC)

    registrar_ajuste_na_trilha(
        eventos,
        caso_id="CASO-1",
        autor="conta-revisor",
        motivo="Negativada primeiro",
        ordem_anterior=("D001", "D002", "D003"),
        ordem_nova=_LISTA,
        snapshot_anterior_id="S1",
        snapshot_novo_id="S2",
        agora=agora,
    )

    (evento,) = eventos.listar_do_caso("CASO-1")
    assert evento.tipo_evento == TIPO_EVENTO_AJUSTE_DA_ORDEM
    assert (evento.estado_de, evento.estado_para) == (None, None)
    assert evento.ocorrido_em == agora
    assert evento.detalhe is not None
    assert json.loads(evento.detalhe) == {
        "ordem_anterior": ["D001", "D002", "D003"],
        "ordem_nova": list(_LISTA),
        "motivo": "Negativada primeiro",
        "autor": "conta-revisor",
        "snapshot_anterior_id": "S1",
        "snapshot_novo_id": "S2",
    }


def test_volta_grava_o_evento_com_motivo_vazio(tmp_path: Path) -> None:
    eventos = RepositorioEventosCasoArquivo(tmp_path / "eventos.jsonl")

    registrar_ajuste_na_trilha(
        eventos,
        caso_id="CASO-1",
        autor="conta-revisor",
        motivo="",
        ordem_anterior=_LISTA,
        ordem_nova=("D001", "D002", "D003"),
        snapshot_anterior_id="S2",
        snapshot_novo_id="S3",
        agora=datetime(2026, 11, 14, tzinfo=UTC),
    )

    (evento,) = eventos.listar_do_caso("CASO-1")
    assert evento.detalhe is not None
    assert json.loads(evento.detalhe)["motivo"] == ""


class _SemRevisoes:
    def listar_dos_casos(
        self, caso_ids: tuple[str, ...]
    ) -> dict[str, tuple[RegistroRevisao, ...]]:
        return {}


def test_o_evento_nao_zera_o_parado_ha_da_lista_de_casos(tmp_path: Path) -> None:
    casos = RepositorioCasosArquivo(tmp_path / "casos.jsonl")
    snapshots = RepositorioSnapshotsArquivo(tmp_path / "snapshots.jsonl")
    eventos = RepositorioEventosCasoArquivo(tmp_path / "eventos.jsonl")
    snapshot = calcular_plano(_estado_ac555(), _parametros())
    snapshots.anexar(snapshot)
    _criar_caso(casos, "CASO-1", "conta-1")
    casos.registrar_snapshot_raiz("CASO-1", snapshot.SNAPSHOT_ID)
    casos.transicionar_estado("CASO-1", ESTADO_CASO.AGUARDANDO_REVISAO)
    envio = datetime(2026, 11, 10, 9, tzinfo=UTC)
    eventos.registrar(
        EventoCaso(
            evento_id="EVENTO_envio",
            CASO_ID="CASO-1",
            tipo_evento="snapshot_anexado",
            estado_de=ESTADO_CASO.CALCULANDO.value,
            estado_para=ESTADO_CASO.AGUARDANDO_REVISAO.value,
            detalhe=None,
            ocorrido_em=envio,
        )
    )
    registrar_ajuste_na_trilha(
        eventos,
        caso_id="CASO-1",
        autor="conta-revisor",
        motivo="Negativada primeiro",
        ordem_anterior=("D001", "D002", "D003"),
        ordem_nova=_LISTA,
        snapshot_anterior_id="S1",
        snapshot_novo_id="S2",
        agora=datetime(2026, 11, 14, 12, tzinfo=UTC),
    )

    (linha,) = montar_linhas(
        datetime(2026, 11, 14, 13, tzinfo=UTC),
        casos,
        snapshots,
        eventos,
        _SemRevisoes(),
        lambda _ids: {},
    )

    assert linha.chegou_em == envio
    assert linha.tempo_na_fila_horas == 100
