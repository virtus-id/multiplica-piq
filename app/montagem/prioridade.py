"""Quem recebe a parcela estimada de 24 meses — `RF-534`, `PD-16`, `OQ-75`, `OQ-84`.

Só a dívida **prioritária** (a dívida-alvo da ordem do motor) paga a parcela
estimada; as demais pagam o mínimo (aula 12: "mínimo em todas, extra
concentrado em uma"). Como a alvo só se conhece rodando o motor, o plano é de
até três passagens, **em processo e sem gravar snapshot**:

1. ninguém recebe a estimada (todas no mínimo) ⇒ o motor diz a alvo;
2. a alvo recebe a estimada ⇒ o motor confirma a alvo (e o caixa observado);
3. se a alvo mudou (empate em `H-04` nível 3, que lê o fluxo liberado), repete
   com a nova; sem estabilizar em três passagens, fica na passagem 1 e a
   prioridade vira `hipotese` (`EC-75`: a parcela migra com a alvo).

O motor entra por `rodar` (injetado por quem tem a fonte de parâmetros), então
este módulo não importa `engine.motor`. Falha em qualquer passagem cai para a
passagem 1 e marca `hipotese` (`T-528`).

Mapeamento nos dois campos de pagamento: decisão do spike `T-523` — **hipótese
adotada, aguardando confirmação do especialista** (plano, seção 11.2). Sem
dívida com parcela estimada nada disto roda: o estado é o de sempre.

REGRAS: `RF-534`, `RF-535`, `RF-537`, `RF-540`, `EC-75`, `OQ-75`, `OQ-83`, `OQ-84`
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Final

from app.montagem.conversao import converter_para_dinheiro
from app.montagem.estado import montar_divida
from app.montagem.premissas import (
    SITUACAO_DA_DIVIDA,
    PremissasDaDivida,
    resolver_divida,
)
from collection.registro import EscopoRepeticao
from collection.respostas import RespostasCaso
from engine.estado import Divida, EstadoFinanceiro
from engine.tipos import Dinheiro, DinheiroTalvez

REGRAS: Final[tuple[str, ...]] = ("RF-534", "RF-535", "RF-537", "EC-75", "OQ-84")

MAXIMO_DE_PASSAGENS: Final[int] = 3  # `PD-16`
_ZERO: Final[Dinheiro] = converter_para_dinheiro("0")


@dataclass(frozen=True, slots=True)
class ResultadoDaPassagem:
    """O que se lê do motor em cada passagem — só leitura, nenhuma conta."""

    divida_alvo: str | None
    caixa_observado: Dinheiro


type Montar = Callable[[tuple[Divida, ...], tuple[PremissasDaDivida, ...]], EstadoFinanceiro]
type Rodar = Callable[[EstadoFinanceiro], ResultadoDaPassagem]


@dataclass(frozen=True, slots=True)
class PlanoDePagamentos:
    estado: EstadoFinanceiro
    prioritaria: str | None  # quem recebeu a parcela estimada
    passagens: int  # execuções do motor feitas para decidir (0 a 3)
    hipotese: bool  # alvo não estabilizou ou o motor falhou: ficou na passagem 1
    capacidade_limitada: bool  # `limitar_capacidade_ao_caixa` agiu
    sem_minimo: tuple[str, ...]  # `OQ-84`: fora do plano, sem mínimo e sem habitual


def limitar_capacidade_ao_caixa(estado: EstadoFinanceiro, caixa: Dinheiro) -> EstadoFinanceiro:
    """RESSALVA (b) do spike `T-523` — **ponto único, fácil de reverter** (basta
    `planejar_pagamentos` deixar de chamar esta função; nada mais depende dela).

    O ataque do motor sai do pagamento devido (`PARCELA_CONTRATUAL`, 0 quando o
    habitual é ausente) e a simulação paga também o efetivo: sem este limite a
    saída do mês excede o orçamento. `CAPACIDADE_ATAQUE_DECLARADA` desce até o
    caixa observado (nunca sobe, nunca abaixo de zero) — altera um campo
    declarado, por isso o relatório a marca como `hipótese`. `DESCONHECIDO`
    fica como está."""
    declarada: DinheiroTalvez = estado.CAPACIDADE_ATAQUE_DECLARADA
    if not isinstance(declarada, Decimal):
        return estado
    teto = max(caixa, _ZERO)
    if teto >= declarada:
        return estado
    return replace(estado, CAPACIDADE_ATAQUE_DECLARADA=teto)


def planejar_pagamentos(
    respostas: RespostasCaso,
    itens_por_escopo: Mapping[EscopoRepeticao, tuple[str, ...]],
    montar: Montar,
    rodar: Rodar | None = None,
) -> PlanoDePagamentos:
    """`rodar=None` monta só a configuração da passagem 1 (sem executar o motor):
    é o estado provisório, que valida a montagem antes de o caso entrar em
    `CALCULANDO`."""
    premissas = {
        item: resolver_divida(respostas, item)
        for item in itens_por_escopo.get(EscopoRepeticao.DIVIDA_ID, ())
    }
    pendentes = tuple(p for p in premissas.values() if p.situacao is SITUACAO_DA_DIVIDA.PENDENTE)
    completas = tuple(
        item for item, p in premissas.items() if p.situacao is not SITUACAO_DA_DIVIDA.PENDENTE
    )
    estimaveis = {item for item in completas if premissas[item].parcela_estimada is not None}

    def construir(
        alvo: str | None, *, definitivo: bool
    ) -> tuple[EstadoFinanceiro, tuple[str, ...]]:
        # `OQ-84`: sem alvo conhecida (passagem 1) todas entram, a estimada cobre
        # o mínimo que falta; com a alvo definida, a não prioritária sem mínimo sai.
        sem_minimo = tuple(
            item
            for item in completas
            if definitivo
            and item in estimaveis
            and item != alvo
            and premissas[item].pagamento_minimo is None
        )
        dividas = tuple(
            montar_divida(respostas, item, recebe_estimada=item == alvo)
            for item in completas
            if item not in sem_minimo
        )
        fora = (*pendentes, *(premissas[item] for item in sem_minimo))
        return montar(dividas, fora), sem_minimo

    if not estimaveis:
        estado, _ = construir(None, definitivo=False)
        return PlanoDePagamentos(estado, None, 0, False, False, ())

    base, _ = construir(None, definitivo=False)
    if rodar is None:
        return PlanoDePagamentos(base, None, 0, False, False, ())

    def fechar(
        estado: EstadoFinanceiro,
        caixa: Dinheiro | None,
        *,
        prioritaria: str | None,
        passagens: int,
        hipotese: bool,
        sem_minimo: tuple[str, ...] = (),
    ) -> PlanoDePagamentos:
        limitado = estado if caixa is None else limitar_capacidade_ao_caixa(estado, caixa)
        return PlanoDePagamentos(
            limitado, prioritaria, passagens, hipotese, limitado is not estado, sem_minimo
        )

    try:
        primeira = rodar(base)
    except Exception:  # noqa: BLE001 — `T-528`: o motor falhar aqui cai para a passagem 1
        return fechar(base, None, prioritaria=None, passagens=1, hipotese=True)
    alvo = primeira.divida_alvo
    if alvo is None:
        # Sem alvo (estabilização): ninguém recebe a estimada, todas no mínimo.
        return fechar(base, primeira.caixa_observado, prioritaria=None, passagens=1, hipotese=False)
    if alvo not in estimaveis:
        # A alvo tem pagamento informado: as estimáveis são todas não prioritárias.
        estado, sem_minimo = construir(alvo, definitivo=True)
        return fechar(
            estado,
            primeira.caixa_observado,
            prioritaria=None,
            passagens=1,
            hipotese=False,
            sem_minimo=sem_minimo,
        )

    passagens = 1
    while passagens < MAXIMO_DE_PASSAGENS:
        estado, sem_minimo = construir(alvo, definitivo=True)
        try:
            resultado = rodar(estado)
        except Exception:  # noqa: BLE001 — `T-528`
            return fechar(
                base,
                primeira.caixa_observado,
                prioritaria=None,
                passagens=passagens + 1,
                hipotese=True,
            )
        passagens += 1
        if resultado.divida_alvo == alvo:
            return fechar(
                estado,
                resultado.caixa_observado,
                prioritaria=alvo,
                passagens=passagens,
                hipotese=False,
                sem_minimo=sem_minimo,
            )
        if resultado.divida_alvo is None or resultado.divida_alvo not in estimaveis:
            break
        alvo = resultado.divida_alvo
    return fechar(
        base, primeira.caixa_observado, prioritaria=None, passagens=passagens, hipotese=True
    )
