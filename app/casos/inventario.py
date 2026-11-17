"""Pendências de inventário — `RF-86`, `RF-88` (`T-246`, `DE-04`);
`SEM_DIVIDAS` reescrita por `RF-559` (`T-647`, Rodada 18).

`plans/app-aluno.plan.md` §R9.5. Função PURA: recebe os registros, as
respostas e os itens ativos por escopo, e devolve o que impede o cálculo
final. Nunca grava nada — as pendências são derivadas a cada leitura
(`R9.7`), para que não exista segunda fonte que envelheça.

- **Dívidas** (`RF-559`): nenhuma ficha de `DIVIDA_ID` com ao menos uma
  resposta bloqueia (`SEM_DIVIDAS`); a correção é cadastrar uma, nunca
  corrigir uma quantidade — não existe mais quantidade declarada para
  comparar (`T-389`, `T-649`: `B5.00`/`B5.00A` saíram do questionário).
- **Itens declarados** (`RF-88`): só a resposta `SIM` exige ao menos um item
  (`EC-34` — "não sei" não exige).
- **Consignado sem vínculo** (`T-282`, `DE-04`, `AC-139`): dívida em que
  `B5.A02V` se aplica, sem nenhum vínculo cadastrado para apontar.

"Cadastrado" = item ATIVO com ao menos uma resposta: ficha criada e vazia
não conta. `ID_PARA_CORRIGIR` é resolvido pela `VARIAVEL_GRAVADA` no
registro — nenhum `ID` de pergunta aqui, nenhum texto (`AC-37`): a redação
vive em `textos/inventario.yaml`. `None` em `SEM_DIVIDAS`: não há mais
pergunta a corrigir (`RF-559`).

REGRAS: `RF-86`, `RF-88`, `RF-559`, `AC-37`
"""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from functools import cache
from pathlib import Path
from typing import Final

import yaml

from collection.registro import EscopoRepeticao, RegistroPergunta
from collection.respostas import RespostasCaso
from persistencia.app_aluno.eventos import EventoCaso, RepositorioEventosCaso
from persistencia.app_aluno.itens import ItemRepetido

REGRAS: Final[tuple[str, ...]] = ("RF-86", "RF-88", "RF-559", "AC-37")

CAMINHO_TEXTOS: Final[Path] = Path(__file__).parent / "textos" / "inventario.yaml"

_SIM: Final[str] = "SIM"
_CREDOR: Final[str] = "CREDOR"
_CREDOR_OUTRO: Final[str] = "CREDOR_OUTRO"
_OUTRA_INSTITUICAO: Final[str] = "OUTRA"

# Trilha (`RF-31`) e painel (`RF-35`): o bloqueio é um motivo NOMEADO — o
# `detalhe` leva só os tipos de pendência, nunca valor (NFR da Rodada 9).
TIPO_EVENTO_CALCULO_BLOQUEADO: Final[str] = "calculo_bloqueado_inventario"


class TIPO_PENDENCIA_INVENTARIO(Enum):
    # `DIVIDAS_FALTANDO`/`DIVIDAS_ACIMA`/`DIVIDAS_SEM_CONFIRMACAO`: saíram
    # com a quantidade declarada (`RF-559`, `T-647`) — não há mais o que
    # comparar.
    SEM_DIVIDAS = "SEM_DIVIDAS"
    RENDA_EXTRA_SEM_ITEM = "RENDA_EXTRA_SEM_ITEM"
    NAO_MENSAL_SEM_ITEM = "NAO_MENSAL_SEM_ITEM"


# RF-88 — declaração "Sim" → escopo em que ao menos um item é exigido.
_DECLARACOES_DE_ITEM: Final[
    tuple[tuple[TIPO_PENDENCIA_INVENTARIO, str, EscopoRepeticao], ...]
] = (
    (
        TIPO_PENDENCIA_INVENTARIO.RENDA_EXTRA_SEM_ITEM,
        "RENDA_RECORRENTE_ADICIONAL_EXISTE",
        EscopoRepeticao.RENDA_ADICIONAL_ID,
    ),
    (
        TIPO_PENDENCIA_INVENTARIO.NAO_MENSAL_SEM_ITEM,
        "DESPESAS_NAO_MENSAIS_EXISTE",
        EscopoRepeticao.DESPESA_NAO_MENSAL_ID,
    ),
)


@dataclass(frozen=True, slots=True)
class PendenciaInventario:
    """Uma pendência que bloqueia o cálculo. `ID_PARA_CORRIGIR` é a pergunta
    da declaração (a ação direta de `AC-154`); `None` quando não há mais
    pergunta a corrigir — a correção é cadastrar uma ficha (`RF-559`,
    `SEM_DIVIDAS`). `escopo`, quando a correção também pode ser cadastrar
    item, é o escopo das fichas a abrir."""

    tipo: TIPO_PENDENCIA_INVENTARIO
    declaradas: int | None
    cadastradas: int | None
    ID_PARA_CORRIGIR: str | None
    escopo: EscopoRepeticao | None


def pendencias_de_inventario(
    registros: tuple[RegistroPergunta, ...],
    respostas: RespostasCaso,
    itens_por_escopo: Mapping[EscopoRepeticao, tuple[str, ...]],
) -> tuple[PendenciaInventario, ...]:
    """RF-86, RF-88, RF-559 — as pendências de inventário do caso, na ordem:
    dívidas primeiro, depois os itens declarados."""
    com_resposta = {r.item_id for r in respostas.respostas if r.item_id}

    def cadastrados(escopo: EscopoRepeticao) -> tuple[str, ...]:
        return tuple(i for i in itens_por_escopo.get(escopo, ()) if i in com_resposta)

    pendencias: list[PendenciaInventario] = []
    # `RF-559` (`T-647`, Rodada 18): nenhuma ficha de `DIVIDA_ID` com
    # resposta — nunca uma comparação com quantidade declarada, que não
    # existe mais no questionário (`T-649`).
    if not cadastrados(EscopoRepeticao.DIVIDA_ID):
        pendencias.append(
            PendenciaInventario(
                tipo=TIPO_PENDENCIA_INVENTARIO.SEM_DIVIDAS,
                declaradas=None,
                cadastradas=0,
                ID_PARA_CORRIGIR=None,
                escopo=EscopoRepeticao.DIVIDA_ID,
            )
        )

    for tipo, variavel, escopo in _DECLARACOES_DE_ITEM:
        id_declaracao = _id_da_variavel(registros, variavel)
        if (
            id_declaracao is not None
            and respostas.valor(variavel) == _SIM
            and not cadastrados(escopo)
        ):
            pendencias.append(
                PendenciaInventario(
                    tipo=tipo,
                    declaradas=None,
                    cadastradas=0,
                    ID_PARA_CORRIGIR=id_declaracao,
                    escopo=escopo,
                )
            )
    return tuple(pendencias)


def credor_da_ficha(respostas: RespostasCaso, item_id: str) -> str | None:
    """T-324 — o credor da ficha de dívida, `None` enquanto não respondido.
    Também nomeia a dívida no plano e na conferência (`T-326`)."""
    credor = respostas.valor_no_item(item_id, _CREDOR)
    if credor == _OUTRA_INSTITUICAO:
        # `T-415`: "Outra instituição ou pessoa" — o nome digitado no campo da opção.
        credor = respostas.valor_no_item(item_id, _CREDOR_OUTRO)
    return credor if isinstance(credor, str) and credor.strip() else None


def rotulos_das_dividas(itens: Iterable[ItemRepetido], respostas: RespostasCaso) -> dict[str, str]:
    """`DIVIDA_ID` → o credor já informado em `B5.A01` ("Itaú"), para a lista e
    o formulário não mostrarem "Dívida D001". Credor repetido ganha o ordinal
    na ordem das fichas ("Itaú · 2"); ficha sem credor fica sem rótulo."""
    credores = {
        item.item_id: credor
        for item in itens
        if item.escopo is EscopoRepeticao.DIVIDA_ID
        and (credor := credor_da_ficha(respostas, item.item_id)) is not None
    }
    total = Counter(credores.values())
    vistos: Counter[str] = Counter()
    rotulos: dict[str, str] = {}
    for item_id, credor in credores.items():
        vistos[credor] += 1
        rotulos[item_id] = credor if total[credor] == 1 else f"{credor} · {vistos[credor]}"
    return rotulos


class ErroInventarioIncompleto(Exception):
    """RF-86 — o cálculo final foi recusado por inventário incompleto. Carrega
    as pendências para a porta que recusou montar a resposta ao aluno."""

    def __init__(self, pendencias: tuple[PendenciaInventario, ...]) -> None:
        self.pendencias = pendencias
        super().__init__(",".join(p.tipo.value for p in pendencias))


def exigir_inventario_completo(
    pendencias: tuple[PendenciaInventario, ...],
    *,
    caso_id: str,
    repositorio_eventos: RepositorioEventosCaso,
    agora: datetime | None = None,
) -> None:
    """RF-86 (`T-248`) — a guarda ÚNICA das duas portas do cálculo
    (hoje só `rotas_calculo._preparar_calculo`),
    chamada ANTES de qualquer transição: o caso nunca fica em `CALCULANDO`.
    Com pendência, registra o motivo na trilha (sem valor) e levanta
    `ErroInventarioIncompleto`; sem pendência, não faz nada."""
    if not pendencias:
        return
    repositorio_eventos.registrar(
        EventoCaso(
            evento_id=f"EVENTO_{uuid.uuid4().hex}",
            CASO_ID=caso_id,
            tipo_evento=TIPO_EVENTO_CALCULO_BLOQUEADO,
            estado_de=None,
            estado_para=None,
            detalhe=",".join(p.tipo.value for p in pendencias),
            ocorrido_em=agora if agora is not None else datetime.now(UTC),
        )
    )
    raise ErroInventarioIncompleto(pendencias)


def mensagem_da_pendencia(pendencia: PendenciaInventario) -> str:
    """A mensagem ao aluno, de `textos/inventario.yaml` — redação aprovada
    pelo produto (`T-289`); `SEM_DIVIDAS` é sugestão, a validar (`RF-559`,
    `T-647`). Nenhuma das três chaves restantes interpola valor."""
    return _textos()[pendencia.tipo.value]


@cache
def _textos(caminho: Path = CAMINHO_TEXTOS) -> Mapping[str, str]:
    with caminho.open(encoding="utf-8") as arquivo:
        bruto = yaml.safe_load(arquivo)
    return {str(chave): str(valor) for chave, valor in bruto.items()}


def _id_da_variavel(registros: tuple[RegistroPergunta, ...], variavel: str) -> str | None:
    """A pergunta que grava `variavel` — a primeira, quando há mais de uma.
    `None` quando o questionário não tem a declaração: sem pergunta, não há
    o que declarar nem pendência sem destino."""
    return next((r.ID for r in registros if r.VARIAVEL_GRAVADA == variavel), None)
