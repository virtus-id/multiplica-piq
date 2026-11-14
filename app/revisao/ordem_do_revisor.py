"""Ordem de quitação definida pelo revisor — `RF-546`, `RF-547`, `RF-549`
(`T-580`, `T-581`) · `plans/app-aluno.plan.md` `R18.3`, `R18.4`.

Um módulo só porque o `GET` da conferência, o `POST` do ajuste e "O que
mudou" usam as mesmas regras. Tudo aqui é LEITURA do snapshot, sem conta
(`AC-42`) e sem passar por `report/plano.py` — menos
`registrar_ajuste_na_trilha`, que grava o fato na trilha do caso.

**A lista é a ordem de ATAQUE** (decisão técnica de 2026-11-14): a sequência
em que as dívidas recebem o valor extra, nunca a de quitação. Sem estouro do
horizonte, `ORDEM_QUITACAO` é a ordem em que a simulação quitou — uma dívida
que termina só com as parcelas aparece antes da sua vez, e mexer nela
mandaria o extra para quem não precisa (`R18.10`).

REGRAS: `RF-546`, `RF-547`, `RF-549`, `AC-565`, `AC-568`, `AC-572`, `EC-84`
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Final

from engine.motor import MOTIVO_AJUSTE_DA_ORDEM
from engine.snapshot import SnapshotOrdem
from persistencia.app_aluno.eventos import EventoCaso, RepositorioEventosCaso

REGRAS: Final[tuple[str, ...]] = (
    "RF-546",
    "RF-547",
    "RF-549",
    "AC-565",
    "AC-568",
    "AC-572",
    "EC-84",
)

# `RF-547`: o ajuste fica na trilha sem ser transição de estado.
TIPO_EVENTO_AJUSTE_DA_ORDEM: Final[str] = "ajuste_da_ordem_pelo_revisor"


def ordem_vigente(snapshot: SnapshotOrdem) -> tuple[tuple[str, ...], bool]:
    """`(ordem de ataque vigente, ajustada)` — a lista que a tela mostra e
    edita e a base de `OQ-101`. Os quatro ramos de `R18.4`:

    1. `ORDEM_DO_REVISOR`, quando houver (`ajustada = True`);
    2. senão `cenarios[recomendado].ORDEM_DE_ATAQUE`, quando houver (estouro);
    3. senão os `DIVIDA_ALVO` distintos de `prognostico.MESES_DO_PLANO`, na
       ordem do primeiro mês em que aparecem, seguidos das dívidas de
       `ORDEM_QUITACAO` que nunca foram alvo, na ordem de quitação;
    4. snapshot sem `prognostico` (anterior a `RF-77`): `ORDEM_QUITACAO`.

    Os ramos 2–4 ficam restritos ao conjunto de `ORDEM_QUITACAO` (as
    elegíveis). Limite aceito (`R18.10`): a dívida que só recebe resíduo no
    mês em que quita nunca é `DIVIDA_ALVO` e vai para o fim."""
    if snapshot.ORDEM_DO_REVISOR is not None:
        return snapshot.ORDEM_DO_REVISOR, True

    quitacao = tuple(posicao.DIVIDA_ID for posicao in snapshot.ORDEM_QUITACAO)
    elegiveis = frozenset(quitacao)
    ataque = snapshot.cenarios[snapshot.METODO_RECOMENDADO_PIQ].ORDEM_DE_ATAQUE
    if ataque:
        return tuple(d for d in ataque if d in elegiveis), False
    if snapshot.prognostico is None:
        return quitacao, False

    vez: list[str] = []
    for mes in snapshot.prognostico.MESES_DO_PLANO:
        alvo = mes.DIVIDA_ALVO
        if alvo is not None and alvo in elegiveis and alvo not in vez:
            vez.append(alvo)
    vez.extend(d for d in quitacao if d not in vez)
    return tuple(vez), False


def e_ajuste_da_ordem(snapshot: SnapshotOrdem) -> bool:
    """O snapshot nasceu da rota do revisor — o ajuste e a volta à ordem do
    método (que sai sem `ORDEM_DO_REVISOR`, mas com o mesmo motivo)."""
    return snapshot.MOTIVO_RECALCULO == MOTIVO_AJUSTE_DA_ORDEM


def anterior_para_comparar(historico: Sequence[SnapshotOrdem]) -> SnapshotOrdem | None:
    """`RF-549`/`AC-572` — o anterior de "O que mudou": entre os snapshots que
    NÃO são ajuste, o penúltimo. `None` com menos de dois (v1 → `null`)."""
    envios = [snapshot for snapshot in historico if not e_ajuste_da_ordem(snapshot)]
    return envios[-2] if len(envios) >= 2 else None


def registrar_ajuste_na_trilha(
    repositorio_eventos: RepositorioEventosCaso,
    *,
    caso_id: str,
    autor: str,
    motivo: str,
    ordem_anterior: tuple[str, ...],
    ordem_nova: tuple[str, ...],
    snapshot_anterior_id: str,
    snapshot_novo_id: str,
    agora: datetime,
) -> None:
    """`RF-547`/`AC-568` — um evento sem `estado_de`/`estado_para`: não há
    transição, e `lista_de_casos._ultima_entrada` mede o "parado há" pelo
    `estado_para`, que assim não zera (`R18.7`). O motivo interno vai só
    para a trilha (vazio na volta, `OQ-99`), nunca para log."""
    repositorio_eventos.registrar(
        EventoCaso(
            evento_id=f"EVENTO_{uuid.uuid4().hex}",
            CASO_ID=caso_id,
            tipo_evento=TIPO_EVENTO_AJUSTE_DA_ORDEM,
            estado_de=None,
            estado_para=None,
            detalhe=json.dumps(
                {
                    "ordem_anterior": list(ordem_anterior),
                    "ordem_nova": list(ordem_nova),
                    "motivo": motivo,
                    "autor": autor,
                    "snapshot_anterior_id": snapshot_anterior_id,
                    "snapshot_novo_id": snapshot_novo_id,
                },
                sort_keys=True,
            ),
            ocorrido_em=agora,
        )
    )
