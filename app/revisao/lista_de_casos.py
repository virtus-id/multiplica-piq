"""Lista unificada de casos que já chegaram ao revisor — `RF-501` a `RF-506`
(`AC-501` a `AC-505`, `AC-507`) · `plans/fila-do-revisor.plan.md` §2, §5 · T-408.

**Consulta, não tabela.** Monta a lista a partir de repositórios que já existem
(casos, contas, trilha de eventos, revisões, histórico de snapshots), sem
coluna nem tabela nova. Tudo em lote: uma consulta por fonte, nunca uma por
linha — a única exceção é `RepositorioSnapshots.historico`, que não tem versão
em lote (adaptador congelado) e roda em paralelo, como em `fila.py`.

**Quem entra (`RF-501`).** `AGUARDANDO_REVISAO`, `PLANO_LIBERADO`,
`REPROVADO_EM_REVISAO` e `ERRO_DE_CALCULO` com plano já enviado à revisão
(evento de entrada na trilha). Há um caso a mais, o do aluno que recebeu o
plano de volta: `reprovar` devolve o caso a `COLETA_INICIAL` no mesmo ato
(`RF-113`), então o estado `REPROVADO_EM_REVISAO` quase nunca persiste. Um caso
em `COLETA_INICIAL`/`CALCULANDO` cuja ÚLTIMA decisão é a reprovação, e que não
voltou à fila depois dela, aparece como devolvido. Coleta sem decisão
reprovada (inclusive o aluno que retirou o plano para editar) não aparece.

**Data de chegada (`RF-503`).** `ocorrido_em` do último evento com
`estado_para = AGUARDANDO_REVISAO`. Sem o evento (caso antigo), o snapshot não
guarda a data de criação — o port `RepositorioSnapshots` não a expõe e o
adaptador está congelado —, então vale `ultima_interacao_em` do caso (a entrada
na fila foi a última interação) para o pendente e `criado_em` para os demais, e
a linha sai com `chegada_aproximada`. O tempo na fila é a diferença entre
timestamps de eventos (`agora` só para o pendente); nenhum campo do snapshot
entra em conta.

**Contagens das abas.** Calculadas com todos os filtros menos a aba, para que o
número de cada aba seja o tamanho da lista ao clicar nela.

REGRAS: `RF-501`, `RF-502`, `RF-503`, `RF-504`, `RF-505`, `RF-506`
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Final, Literal, Protocol

from app.casos.maquina import ESTADO_CASO, Caso
from app.concorrencia import mapear_em_paralelo
from app.revisao.fila import (
    DECISAO_REVISAO,
    ItemFila,
    RegistroRevisao,
    RepositorioCasosDaFila,
    montar_item_da_fila,
)
from engine.portas import RepositorioSnapshots
from engine.snapshot import SnapshotOrdem
from persistencia.app_aluno.contas import ContaDoCaso
from persistencia.app_aluno.eventos import EventoCaso

REGRAS: Final[tuple[str, ...]] = ("RF-501", "RF-502", "RF-503", "RF-504", "RF-505", "RF-506")

#: `RF-505` — decisão do produto: pendente parado há 5 dias ou mais.
HORAS_PARA_ATRASO: Final[int] = 120

ABA = Literal["pendentes", "entregues", "devolvidos", "todos"]
CAMPO_DE_ORDEM = Literal[
    "aluno",
    "chegou_em",
    "tempo_na_fila",
    "status",
    "tipo",
    "situacao_mes",
    "dividas",
    "metodo",
    "decidido_em",
    "revisor",
]

_ESTADOS_DA_LISTA: Final[tuple[ESTADO_CASO, ...]] = (
    ESTADO_CASO.AGUARDANDO_REVISAO,
    ESTADO_CASO.PLANO_LIBERADO,
    ESTADO_CASO.REPROVADO_EM_REVISAO,
    ESTADO_CASO.ERRO_DE_CALCULO,
)
# Estados em que o aluno está de posse do caso depois de uma devolução.
_ESTADOS_COM_O_ALUNO: Final[tuple[ESTADO_CASO, ...]] = (
    ESTADO_CASO.COLETA_INICIAL,
    ESTADO_CASO.CALCULANDO,
)
_ESTADOS_DE_CADA_ABA: Final[dict[str, frozenset[ESTADO_CASO]]] = {
    "pendentes": frozenset({ESTADO_CASO.AGUARDANDO_REVISAO}),
    "entregues": frozenset({ESTADO_CASO.PLANO_LIBERADO}),
    "devolvidos": frozenset({ESTADO_CASO.REPROVADO_EM_REVISAO}),
}


class RepositorioEventosDaLista(Protocol):
    """Recorte da trilha: os eventos de vários casos numa consulta só."""

    def listar_dos_casos(self, caso_ids: tuple[str, ...]) -> dict[str, tuple[EventoCaso, ...]]: ...


class RepositorioRevisoesDaLista(Protocol):
    """Recorte das revisões: os registros de vários casos numa consulta só."""

    def listar_dos_casos(
        self, caso_ids: tuple[str, ...]
    ) -> dict[str, tuple[RegistroRevisao, ...]]: ...


@dataclass(frozen=True, slots=True)
class FiltrosDaLista:
    """Os filtros de `RF-504`; `None` ou vazio = sem filtro."""

    aba: ABA = "todos"
    q: str | None = None
    status: frozenset[ESTADO_CASO] = frozenset()
    de: date | None = None
    ate: date | None = None
    tipo: Literal["primeiro", "recalculo"] | None = None
    mes_negativo: bool | None = None
    metodo: str | None = None
    motivo: str | None = None
    revisor: str | None = None
    parado_horas: int | None = None


@dataclass(frozen=True, slots=True)
class LinhaDoCaso:
    """Uma linha da tabela, ainda com códigos — os rótulos humanos saem na
    serialização (`app/http/serializacao_plano.py`)."""

    CASO_ID: str
    nome: str | None
    email: str | None
    chegou_em: datetime
    chegada_aproximada: bool
    tempo_na_fila_horas: int | None
    atrasado: bool
    status: ESTADO_CASO
    item: ItemFila
    e_recalculo: bool
    motivo: str
    mes_negativo: bool
    dividas: int
    metodo: str
    revisor: str | None
    decidido_em: datetime | None


@dataclass(frozen=True, slots=True)
class ResultadoDaLista:
    linhas: tuple[LinhaDoCaso, ...]
    total: int
    contagens: dict[str, int]


def codigo_do_motivo(snapshot: SnapshotOrdem) -> str:
    """O código que `report.plano.rotulo_do_motivo_de_recalculo` rotula."""
    if snapshot.EVENTO_RECALCULO is not None:
        return snapshot.EVENTO_RECALCULO.value
    return "SEM_EVENTO_PRIMEIRO_CALCULO" if snapshot.versao == 1 else "SEM_EVENTO"


def _ultima_entrada(eventos: Sequence[EventoCaso]) -> datetime | None:
    entradas = [
        e.ocorrido_em for e in eventos if e.estado_para == ESTADO_CASO.AGUARDANDO_REVISAO.value
    ]
    return max(entradas) if entradas else None


def _ultima_decisao(registros: Sequence[RegistroRevisao]) -> RegistroRevisao | None:
    return max(registros, key=lambda r: r.decidido_em) if registros else None


def _horas_entre(inicio: datetime, fim: datetime) -> int:
    return max(0, int((fim - inicio).total_seconds() // 3600))


def _status_da_lista(
    caso: Caso,
    entrada: datetime | None,
    decisao: RegistroRevisao | None,
    tem_registro: bool,
) -> ESTADO_CASO | None:
    """`None` = o caso não aparece (`RF-501`)."""
    if caso.estado in (
        ESTADO_CASO.AGUARDANDO_REVISAO,
        ESTADO_CASO.PLANO_LIBERADO,
        ESTADO_CASO.REPROVADO_EM_REVISAO,
    ):
        return caso.estado
    if caso.estado is ESTADO_CASO.ERRO_DE_CALCULO:
        return caso.estado if entrada is not None or tem_registro else None
    if caso.estado in _ESTADOS_COM_O_ALUNO:
        devolvido = (
            decisao is not None
            and decisao.decisao is DECISAO_REVISAO.REPROVADO
            and (entrada is None or entrada <= decisao.decidido_em)
        )
        return ESTADO_CASO.REPROVADO_EM_REVISAO if devolvido else None
    return None


def montar_linhas(
    agora: datetime,
    repositorio_casos: RepositorioCasosDaFila,
    repositorio_snapshots: RepositorioSnapshots,
    repositorio_eventos: RepositorioEventosDaLista,
    repositorio_revisoes: RepositorioRevisoesDaLista,
    contas_dos_casos: Callable[[tuple[str, ...]], dict[str, ContaDoCaso]],
) -> tuple[LinhaDoCaso, ...]:
    """Todas as linhas elegíveis, sem filtro: uma consulta por fonte."""
    estados = _ESTADOS_DA_LISTA + _ESTADOS_COM_O_ALUNO
    por_estado = mapear_em_paralelo(repositorio_casos.listar_por_estado, estados)
    ids = tuple(dict.fromkeys(caso_id for grupo in por_estado for caso_id in grupo))
    casos = repositorio_casos.buscar_varios(ids)
    registros = repositorio_revisoes.listar_dos_casos(ids)
    eventos = repositorio_eventos.listar_dos_casos(ids)

    elegiveis: list[tuple[Caso, ESTADO_CASO, datetime | None, RegistroRevisao | None]] = []
    for caso_id in ids:
        caso = casos.get(caso_id)
        if caso is None or caso.snapshot_raiz_id is None:
            continue
        entrada = _ultima_entrada(eventos.get(caso_id, ()))
        decisao = _ultima_decisao(registros.get(caso_id, ()))
        status = _status_da_lista(caso, entrada, decisao, caso_id in registros)
        if status is not None:
            elegiveis.append((caso, status, entrada, decisao))

    historicos = mapear_em_paralelo(
        lambda e: repositorio_snapshots.historico(e[0].snapshot_raiz_id or ""), elegiveis
    )
    contas = contas_dos_casos(tuple(e[0].CASO_ID for e in elegiveis))

    linhas: list[LinhaDoCaso] = []
    for (caso, status, entrada, decisao), historico in zip(elegiveis, historicos, strict=True):
        if not historico:
            continue
        snapshot = historico[-1]
        pendente = status is ESTADO_CASO.AGUARDANDO_REVISAO
        decidido = status in (ESTADO_CASO.PLANO_LIBERADO, ESTADO_CASO.REPROVADO_EM_REVISAO)
        chegou_em = entrada or (caso.ultima_interacao_em if pendente else caso.criado_em)
        decisao_da_linha = decisao if decidido else None
        if pendente:
            tempo: int | None = _horas_entre(chegou_em, agora)
        elif decisao_da_linha is not None:
            tempo = _horas_entre(chegou_em, decisao_da_linha.decidido_em)
        else:
            tempo = None
        conta = contas.get(caso.CASO_ID)
        linhas.append(
            LinhaDoCaso(
                CASO_ID=caso.CASO_ID,
                nome=conta.nome if conta else None,
                email=conta.email if conta else None,
                chegou_em=chegou_em,
                chegada_aproximada=entrada is None,
                tempo_na_fila_horas=tempo,
                atrasado=pendente and tempo is not None and tempo >= HORAS_PARA_ATRASO,
                status=status,
                item=montar_item_da_fila(caso.CASO_ID, snapshot),
                e_recalculo=snapshot.versao > 1,
                motivo=codigo_do_motivo(snapshot),
                mes_negativo=snapshot.diagnostico.MODO_ESTABILIZACAO,
                dividas=len(snapshot.estado_inputs.dividas),
                metodo=snapshot.METODO_RECOMENDADO_PIQ.value,
                revisor=decisao_da_linha.autor if decisao_da_linha else None,
                decidido_em=decisao_da_linha.decidido_em if decisao_da_linha else None,
            )
        )
    return tuple(linhas)


def _passa(linha: LinhaDoCaso, f: FiltrosDaLista) -> bool:
    """Todos os filtros de `RF-504`, menos a aba."""
    if f.q:
        agulha = f.q.strip().lower()
        if agulha not in (linha.nome or "").lower() and agulha not in (linha.email or "").lower():
            return False
    if f.status and linha.status not in f.status:
        return False
    if f.de is not None and linha.chegou_em.date() < f.de:
        return False
    if f.ate is not None and linha.chegou_em.date() > f.ate:
        return False
    if f.tipo is not None and linha.e_recalculo != (f.tipo == "recalculo"):
        return False
    if f.mes_negativo is not None and linha.mes_negativo != f.mes_negativo:
        return False
    if f.metodo and linha.metodo != f.metodo:
        return False
    if f.motivo and linha.motivo != f.motivo:
        return False
    if f.revisor and linha.revisor != f.revisor:
        return False
    if f.parado_horas is not None:
        horas = linha.tempo_na_fila_horas
        if horas is None or horas < f.parado_horas:
            return False
    return True


def _na_aba(linha: LinhaDoCaso, aba: str) -> bool:
    return aba == "todos" or linha.status in _ESTADOS_DE_CADA_ABA[aba]


def _chave_de_ordem(campo: str, linha: LinhaDoCaso) -> object:
    """`None` quando a linha não tem o dado (vai sempre para o fim)."""
    match campo:
        case "aluno":
            return (linha.nome or linha.email or "").lower()
        case "chegou_em":
            return linha.chegou_em
        case "tempo_na_fila":
            return linha.tempo_na_fila_horas
        case "status":
            return linha.status.value
        case "tipo":
            return linha.e_recalculo
        case "situacao_mes":
            return linha.mes_negativo
        case "dividas":
            return linha.dividas
        case "metodo":
            return linha.metodo
        case "decidido_em":
            return linha.decidido_em
        case _:
            return (linha.revisor or "").lower() if linha.revisor else None


def consultar_casos(
    linhas: Sequence[LinhaDoCaso],
    filtros: FiltrosDaLista,
    ordenar: CAMPO_DE_ORDEM | None,
    direcao: Literal["asc", "desc"] | None,
    pagina: int,
    por_pagina: int,
) -> ResultadoDaLista:
    """Filtra, ordena e pagina. Padrão de ordem (`RF-505`): mais antigo
    primeiro nos pendentes, mais recente primeiro nas demais abas."""
    base = [linha for linha in linhas if _passa(linha, filtros)]
    contagens = {
        aba: sum(1 for linha in base if _na_aba(linha, aba))
        for aba in ("pendentes", "entregues", "devolvidos", "todos")
    }
    da_aba = sorted((x for x in base if _na_aba(x, filtros.aba)), key=lambda x: x.CASO_ID)

    campo = ordenar or "chegou_em"
    decrescente = (direcao or ("asc" if filtros.aba == "pendentes" else "desc")) == "desc"
    chaveadas = [(_chave_de_ordem(campo, x), x) for x in da_aba]
    com_dado = [par for par in chaveadas if par[0] is not None]
    com_dado.sort(key=lambda par: par[0], reverse=decrescente)  # type: ignore[arg-type,return-value]
    ordenadas = [x for _, x in com_dado] + [x for chave, x in chaveadas if chave is None]
    inicio = (pagina - 1) * por_pagina
    return ResultadoDaLista(
        linhas=tuple(ordenadas[inicio : inicio + por_pagina]),
        total=len(ordenadas),
        contagens=contagens,
    )
