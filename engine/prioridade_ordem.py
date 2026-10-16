"""Prioridade na ordem de quitação — regra `§16.4`.

`specs/motor-calculo.spec.md` §16.4 (Rodada 6). Cinco respostas por dívida
(`B5.F03`, `B5.E03`, `B5.F02`, `B5.H03`, `B5.H04`) reordenam o alvo que o método
vigente (Avalanche, Bola de Neve ou Híbrido) escolheria. Ausente/neutro = a regra
não se aplica e o `SelecionarAlvo` do método é devolvido sem alteração. Sem
parâmetro `P_*` novo (a tolerância de custo é `P_DIFERENCA_CUSTO_EQUIVALENTE`);
pesos 3/2/1 e 20% são decisão do especialista.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from decimal import Decimal
from typing import Final

from engine.ciclo_mensal import EstadoSimulacao, SelecionarAlvo
from engine.estado import Divida
from engine.parametros import Parametros
from engine.tipos import DESCONHECIDO, Desconhecido, Dinheiro

REGRAS: Final[tuple[str, ...]] = ("§16.4", "RF-12", "RF-16", "O-05")

# Decisão do especialista (§16.4, passo 3): peso por tipo de garantia.
_PESO_GARANTIA: Final[Mapping[str, int]] = {"IMOVEL": 3, "VEICULO": 2}
_PESO_GARANTIA_OUTROS: Final[int] = 1
# Decisão do especialista (§16.4, passo 4): a urgência soma 20% ao peso.
_FRACAO_URGENCIA: Final[Decimal] = Decimal("0.2")
_CEM: Final[Decimal] = Decimal(100)


def peso_garantia(divida: Divida) -> int:
    """`§16.4` passo 3: imóvel 3, veículo 2, outro tipo declarado 1, sem garantia 0."""
    if divida.TIPO_GARANTIA is None:
        return 0
    return _PESO_GARANTIA.get(divida.TIPO_GARANTIA, _PESO_GARANTIA_OUTROS)


def peso_emocional_efetivo(divida: Divida) -> Decimal | Desconhecido:
    """`§16.4` passo 4: `PESO_EMOCIONAL + 0,20 × URGENCIA_PERCEBIDA`.

    Sem urgência o peso é o próprio `PESO_EMOCIONAL`; peso desconhecido continua
    desconhecido (perde o desempate, `RF-16`).
    """
    peso = divida.PESO_EMOCIONAL
    if peso is DESCONHECIDO:
        return DESCONHECIDO
    efetivo = Decimal(peso)
    if divida.URGENCIA_PERCEBIDA is not None:
        efetivo += _FRACAO_URGENCIA * divida.URGENCIA_PERCEBIDA
    return efetivo


def _chave_grupo(divida: Divida) -> tuple[bool, bool, int]:
    """`§16.4` passos 1 a 3, em ordem lexicográfica (maior chave entra antes)."""
    return (divida.GARANTIA_ESSENCIAL, divida.NEGATIVADA, peso_garantia(divida))


def _regra_se_aplica(dividas: Mapping[str, Divida]) -> bool:
    return any(
        d.GARANTIA_ESSENCIAL
        or d.NEGATIVADA
        or d.TIPO_GARANTIA is not None
        or d.PREFERENCIA_QUITACAO
        for d in dividas.values()
    )


def _custos_proximos(a: Divida, b: Divida, p: Parametros) -> bool:
    """`§16.4` passo 5: `|custo(a) − custo(b)| ≤ T × máx(custo)`, custo =
    `TAXA_EFETIVA_MENSAL_NORMALIZADA`, `T = P_DIFERENCA_CUSTO_EQUIVALENTE ÷ 100`."""
    ca, cb = a.TAXA_EFETIVA_MENSAL_NORMALIZADA, b.TAXA_EFETIVA_MENSAL_NORMALIZADA
    if ca is DESCONHECIDO or cb is DESCONHECIDO:
        return False
    teto = p.numero("P_DIFERENCA_CUSTO_EQUIVALENTE") / _CEM
    return abs(ca - cb) <= teto * max(ca, cb)


def aplicar_prioridade_ordem(
    sel_base: SelecionarAlvo, dividas: Mapping[str, Divida], p: Parametros
) -> SelecionarAlvo:
    """Envolve o `SelecionarAlvo` de um método com a regra `§16.4`.

    O método é consultado sobre subconjuntos da carteira marcando as demais
    dívidas como quitadas no `EstadoSimulacao` (os três métodos ignoram
    `estado.quitadas`), então seus critérios e desempates seguem valendo
    dentro do grupo.
    """
    if not _regra_se_aplica(dividas):
        return sel_base

    def selecionar_alvo_com_prioridade(estado: EstadoSimulacao, delta: Dinheiro) -> Divida | None:
        alvo_id = estado.DIVIDA_ALVO_ATUAL
        if alvo_id is not None and alvo_id not in estado.quitadas:
            return sel_base(estado, delta)  # O-02/H-06: alvo fixo até a quitação

        restantes = {i for i in dividas if i not in estado.quitadas}
        if not restantes:
            return sel_base(estado, delta)
        melhor = max(_chave_grupo(dividas[i]) for i in restantes)
        grupo = {i for i in restantes if _chave_grupo(dividas[i]) == melhor}
        fora = frozenset(restantes - grupo)

        def consultar(excluir: frozenset[str]) -> Divida | None:
            return sel_base(dataclasses.replace(estado, quitadas=estado.quitadas | excluir), delta)

        primeira = consultar(fora)
        if primeira is None:
            return sel_base(estado, delta)  # sem candidata no grupo: nunca deixa sem alvo
        if len(grupo) > 1:
            segunda = consultar(fora | {primeira.DIVIDA_ID})
            if (
                segunda is not None
                and segunda.PREFERENCIA_QUITACAO
                and not primeira.PREFERENCIA_QUITACAO
                and _custos_proximos(primeira, segunda, p)
            ):
                return segunda
        return primeira

    return selecionar_alvo_com_prioridade
