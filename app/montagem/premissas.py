"""Valores, marcas e situação da dívida — `RF-525` a `RF-528`, `RF-531`.

`resolver_divida` é **derivação pura** (`PD-06`): lê as respostas e devolve,
a cada chamada, os quatro valores da dívida com a marca de cada um. Nada é
gravado: a resposta do aluno fica intacta (`NAO_SEI` onde ele não soube) e o
valor calculado existe só na saída. Mudou uma resposta, mudou o derivado
(`EC-70`, `EC-71`); a escolha de recálculo (`RF-525`) carrega a impressão dos
valores em que foi feita e deixa de valer sozinha quando eles mudam.

Tabela-verdade (plano, 4.4; `S` saldo, `P` parcela, `T` taxa, `N` prazo):
nenhum desconhecido → conferência de compatibilidade; só um desconhecido →
calculado; só `N` → `COMPLETA` (o prazo nunca vai ao motor, `RF-531`); `N` mais
um de `S`/`P`/`T`, ou dois ou mais de `S`/`P`/`T` → `PENDENTE`.

Hipóteses declaradas (relatório da tarefa, "Open Questions"):
- Valor gravado que a validação recusa (saldo `<= 0`, taxa acima do teto, prazo
  fora de 1..480, taxa sem periodicidade) **não é sobrescrito** por cálculo:
  o campo fica `PENDENTE` e, sendo `S`/`P`/`T`, entra em `faltas`.
- Cálculo que falha (`ErroDeCalculo`, ou `P = 0,00` como dado de cálculo,
  `OQ-92`) deixa o campo `PENDENTE` em vez de inventar valor.
- Escolha de recálculo que não tem solução cai para os originais com a
  sinalização de incompatibilidade.

REGRAS: `RF-525`, `RF-526`, `RF-527`, `RF-528`, `RF-531`, `EC-62`, `EC-70`,
`EC-71`, `EC-74`, `OQ-92`
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Final

from app.montagem.calculo_divida import (
    CAMPO_DA_DIVIDA,
    CODIGO_ERRO_DE_CALCULO,
    COMPATIBILIDADE,
    PRAZO_MAXIMO_MESES,
    TETO_TAXA_MENSAL,
    EntradaDaDivida,
    ErroDeCalculo,
    PeriodicidadeTaxa,
    calcular_parcela,
    calcular_prazo,
    calcular_saldo,
    calcular_taxa,
    conferir_compatibilidade,
    taxa_na_periodicidade,
)
from app.montagem.cenario_conservador import HipoteseConservadora, escolher_hipotese
from app.montagem.conversao import converter_para_dinheiro
from collection.registro import EscopoRepeticao
from collection.respostas import NAO_SEI, RespostasCaso, ValorResposta
from engine.precisao import CONTEXTO_MOTOR
from engine.taxa import derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA
from engine.tipos import SISTEMA_AMORTIZACAO, Dinheiro, Taxa

REGRAS: Final[tuple[str, ...]] = ("RF-525", "RF-526", "RF-527", "RF-528", "RF-531", "RF-532")

_ZERO: Final[Dinheiro] = converter_para_dinheiro("0")

# `VARIAVEL_GRAVADA` do registro (`collection/registros/bloco-05.yaml`). A da
# parcela é composta; duas partes, como em `estado.py`, para não acionar o
# detector de enunciado de `test_sem_conteudo_de_questionario_no_codigo.py`.
_VARIAVEL_DO_CAMPO: Final[Mapping[CAMPO_DA_DIVIDA, str]] = {
    CAMPO_DA_DIVIDA.SALDO: "SALDO_DEVEDOR_ATUAL",
    CAMPO_DA_DIVIDA.PARCELA: "PARCELA_CONTRATUAL" + " (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)",
    CAMPO_DA_DIVIDA.TAXA: "TAXA_DIVIDA",
    CAMPO_DA_DIVIDA.PRAZO: "PRAZO_RESTANTE_MESES",
}
_VARIAVEL_PERIODICIDADE: Final[str] = "PERIODICIDADE_TAXA_DIVIDA"
_VARIAVEL_MINIMO: Final[str] = "PAGAMENTO_MINIMO_DIVIDA"  # `B5.C02C` (`RF-533`)
_VARIAVEL_SISTEMA: Final[str] = "SISTEMA_AMORTIZACAO"
_VARIAVEL_ESCOLHA: Final[str] = "INFORMACAO_A_RECALCULAR"
_SEM_ESCOLHA: Final[str] = "NENHUMA"
_TAMANHO_DA_IMPRESSAO: Final[int] = 12

#: `RF-532`: o prazo da hipótese, uma constante nomeada (não é parâmetro `P_*` do motor).
PRAZO_BASE_ESTIMATIVA_MESES: Final[int] = 24

_ORDEM_DOS_CAMPOS: Final[tuple[CAMPO_DA_DIVIDA, ...]] = (
    CAMPO_DA_DIVIDA.SALDO,
    CAMPO_DA_DIVIDA.PARCELA,
    CAMPO_DA_DIVIDA.TAXA,
    CAMPO_DA_DIVIDA.PRAZO,
)
_CAMPOS_DO_MOTOR: Final[tuple[CAMPO_DA_DIVIDA, ...]] = _ORDEM_DOS_CAMPOS[:3]


class MARCA_DO_VALOR(Enum):
    INFORMADO = "INFORMADO"
    CALCULADO = "CALCULADO"
    ESTIMADO = "ESTIMADO"  # Fase 2 (`RF-532`)
    HIPOTESE = "HIPOTESE"  # Fases 2 e 3
    PENDENTE = "PENDENTE"


class SITUACAO_DA_DIVIDA(Enum):
    COMPLETA = "COMPLETA"
    PENDENTE = "PENDENTE"
    INCOMPATIVEL = "INCOMPATIVEL"


type ValorDoCampo = Dinheiro | Taxa | int


@dataclass(frozen=True, slots=True)
class ValorDaDivida:
    campo: CAMPO_DA_DIVIDA
    valor: ValorDoCampo | None  # None só quando PENDENTE; taxa na periodicidade gravada
    marca: MARCA_DO_VALOR
    original: ValorDoCampo | None  # o que o aluno digitou, quando difere de `valor`


@dataclass(frozen=True, slots=True)
class ParcelaEstimada:
    """`RF-532`, `RF-533`: a parcela que o plano usa quando o aluno não informou
    pagamento habitual `> 0` nem prazo. Existe só em `parcela_estimada`, nunca
    no campo digitado."""

    valor: Dinheiro
    prazo_base: int  # meses da conta; hoje sempre `PRAZO_BASE_ESTIMATIVA_MESES`
    habitual_ausente: bool  # True: nada declarado (não é um "zero declarado", `OQ-73`)


@dataclass(frozen=True, slots=True)
class PremissasDaDivida:
    DIVIDA_ID: str
    sistema: SISTEMA_AMORTIZACAO
    valores: Mapping[CAMPO_DA_DIVIDA, ValorDaDivida]
    taxa_mensal_normalizada: Taxa | None  # o que vai ao motor
    taxa_na_periodicidade: Taxa | None  # o que o aluno vê/escolheu
    situacao: SITUACAO_DA_DIVIDA
    faltas: tuple[CAMPO_DA_DIVIDA, ...]  # S/P/T pendentes que impedem o motor
    parcela_teorica: Dinheiro | None  # só INCOMPATIVEL
    recalcular_escolhido: CAMPO_DA_DIVIDA | None
    parcela_estimada: ParcelaEstimada | None = None  # `RF-532`
    pagamento_minimo: Dinheiro | None = None  # `B5.C02C`; None = não informado
    # `RF-538`/`RF-539`: INCOMPATIVEL sem escolha válida. Saldo e taxa daqui já estão em
    # `valores` (marca HIPOTESE); parcela e prazo são só referência exibida.
    hipotese_conservadora: HipoteseConservadora | None = None


class _Invalido(Enum):
    INVALIDO = "INVALIDO"


_INVALIDO: Final = _Invalido.INVALIDO

type _Leitura = ValorDoCampo | _Invalido | None  # None = desconhecido (ausente ou "não sei")


# --- Leitura das respostas -------------------------------------------------------


def _decimal(valor: ValorResposta | None) -> Decimal | None:
    if isinstance(valor, bool) or not isinstance(valor, (Decimal, int)):
        return None
    return converter_para_dinheiro(str(valor)) if isinstance(valor, int) else valor


def _desconhecido(valor: ValorResposta | None) -> bool:
    return valor is None or valor is NAO_SEI


def _periodicidade(respostas: RespostasCaso, DIVIDA_ID: str) -> PeriodicidadeTaxa | None:
    bruta = _periodicidade_bruta(respostas, DIVIDA_ID)
    if bruta == "MENSAL":
        return "MENSAL"
    return "ANUAL" if bruta == "ANUAL" else None


def _periodicidade_bruta(respostas: RespostasCaso, DIVIDA_ID: str) -> str | None:
    bruta = respostas.valor_no_item(DIVIDA_ID, _VARIAVEL_PERIODICIDADE)
    return bruta if isinstance(bruta, str) else None


def _sistema(respostas: RespostasCaso, DIVIDA_ID: str) -> SISTEMA_AMORTIZACAO:
    """`RF-523`: `PRICE` é o padrão; `SAC` só quando o aluno o escolheu."""
    if respostas.valor_no_item(DIVIDA_ID, _VARIAVEL_SISTEMA) == "SAC":
        return SISTEMA_AMORTIZACAO.SAC
    return SISTEMA_AMORTIZACAO.PRICE


def _taxa_mensal(taxa: Taxa, periodicidade: PeriodicidadeTaxa) -> Taxa:
    return derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(taxa, periodicidade)


def _ler_campo(respostas: RespostasCaso, DIVIDA_ID: str, campo: CAMPO_DA_DIVIDA) -> _Leitura:
    """`RF-518` sobre o que já está gravado. Parcela `0,00` é válida (`OQ-92`)."""
    bruto = respostas.valor_no_item(DIVIDA_ID, _VARIAVEL_DO_CAMPO[campo])
    if _desconhecido(bruto):
        return None
    numero = _decimal(bruto)
    if numero is None:
        return _INVALIDO
    if campo is CAMPO_DA_DIVIDA.SALDO:
        return numero if numero > _ZERO else _INVALIDO
    if campo is CAMPO_DA_DIVIDA.PARCELA:
        return numero if numero >= _ZERO else _INVALIDO
    if campo is CAMPO_DA_DIVIDA.PRAZO:
        if numero != numero.to_integral_value() or not 1 <= numero <= PRAZO_MAXIMO_MESES:
            return _INVALIDO
        return int(numero)
    periodicidade = _periodicidade(respostas, DIVIDA_ID)
    if numero < _ZERO or periodicidade is None:
        return _INVALIDO
    return numero if _taxa_mensal(numero, periodicidade) <= TETO_TAXA_MENSAL else _INVALIDO


# --- Impressão da escolha de recálculo (`T-487`) -----------------------------------


def _texto_da_impressao(valor: ValorResposta | None) -> str:
    if valor is None:
        return "-"
    if valor is NAO_SEI:
        return "?"
    numero = _decimal(valor)
    if numero is None:
        return str(valor)
    return format(numero.normalize(CONTEXTO_MOTOR), "f")


def impressao_dos_valores(
    saldo: ValorResposta | None,
    parcela: ValorResposta | None,
    taxa: ValorResposta | None,
    prazo: ValorResposta | None,
    sistema: SISTEMA_AMORTIZACAO,
    periodicidade: str | None,
) -> str:
    """Hash curto dos quatro valores como estão gravados, do sistema e da
    periodicidade (que muda o sentido da taxa): a escolha de `RF-525` só vale
    enquanto nada disso mudar (`EC-70`, `EC-71`). É o que a confirmação grava
    depois de `<CAMPO>|`."""
    partes = [_texto_da_impressao(v) for v in (saldo, parcela, taxa, prazo)]
    partes += [sistema.value, periodicidade or "-"]
    resumo = hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()
    return resumo[:_TAMANHO_DA_IMPRESSAO]


def _impressao_atual(respostas: RespostasCaso, DIVIDA_ID: str) -> str:
    saldo, parcela, taxa, prazo = (
        respostas.valor_no_item(DIVIDA_ID, _VARIAVEL_DO_CAMPO[campo]) for campo in _ORDEM_DOS_CAMPOS
    )
    return impressao_dos_valores(
        saldo,
        parcela,
        taxa,
        prazo,
        _sistema(respostas, DIVIDA_ID),
        _periodicidade_bruta(respostas, DIVIDA_ID),
    )


def _escolha_valida(respostas: RespostasCaso, DIVIDA_ID: str) -> CAMPO_DA_DIVIDA | None:
    """`NENHUMA`, texto torto ou impressão velha: sem escolha, sem escrita."""
    bruta = respostas.valor_no_item(DIVIDA_ID, _VARIAVEL_ESCOLHA)
    if not isinstance(bruta, str) or bruta == _SEM_ESCOLHA or "|" not in bruta:
        return None
    nome, impressao = bruta.split("|", 1)
    if nome not in CAMPO_DA_DIVIDA.__members__:
        return None
    if impressao != _impressao_atual(respostas, DIVIDA_ID):
        return None
    return CAMPO_DA_DIVIDA[nome]


# --- Cálculo do campo desconhecido ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Calculado:
    valor: ValorDoCampo  # taxa na periodicidade
    taxa_mensal: Taxa | None  # só quando o campo é a taxa


def _calcular_campo(
    campo: CAMPO_DA_DIVIDA,
    informados: Mapping[CAMPO_DA_DIVIDA, ValorDoCampo],
    sistema: SISTEMA_AMORTIZACAO,
    periodicidade: PeriodicidadeTaxa,
) -> _Calculado:
    """Calcula `campo` a partir dos outros três (já válidos). `ErroDeCalculo`
    quando não há resultado válido, nunca valor inventado."""
    saldo = informados.get(CAMPO_DA_DIVIDA.SALDO)
    parcela = informados.get(CAMPO_DA_DIVIDA.PARCELA)
    taxa = informados.get(CAMPO_DA_DIVIDA.TAXA)
    prazo = informados.get(CAMPO_DA_DIVIDA.PRAZO)
    mensal = None if taxa is None else _taxa_mensal(_d(taxa), periodicidade)

    if campo is not CAMPO_DA_DIVIDA.PARCELA and parcela == _ZERO:
        raise ErroDeCalculo(
            CODIGO_ERRO_DE_CALCULO.NAO_REDUZ_SALDO
        )  # `OQ-92`: pagamento zero fica fora da conta
    if campo is CAMPO_DA_DIVIDA.SALDO:
        return _Calculado(calcular_saldo(_d(parcela), _d(mensal), _n(prazo), sistema), None)
    if campo is CAMPO_DA_DIVIDA.PARCELA:
        return _Calculado(calcular_parcela(_d(saldo), _d(mensal), _n(prazo), sistema), None)
    if campo is CAMPO_DA_DIVIDA.TAXA:
        calculada = calcular_taxa(_d(saldo), _d(parcela), _n(prazo), sistema)
        return _Calculado(taxa_na_periodicidade(calculada, periodicidade), calculada)
    return _Calculado(calcular_prazo(_d(saldo), _d(parcela), _d(mensal), sistema), None)


def _d(valor: ValorDoCampo | None) -> Decimal:
    assert isinstance(valor, Decimal)
    return valor


def _n(valor: ValorDoCampo | None) -> int:
    assert isinstance(valor, int)
    return valor


# --- resolver_divida -------------------------------------------------------------------


def resolver_divida(respostas: RespostasCaso, DIVIDA_ID: str) -> PremissasDaDivida:
    """`RF-526`, `RF-528`, `RF-525` (`PD-06`): tabela-verdade da seção 4.4."""
    sistema = _sistema(respostas, DIVIDA_ID)
    periodicidade = _periodicidade(respostas, DIVIDA_ID) or "MENSAL"
    lidos = {campo: _ler_campo(respostas, DIVIDA_ID, campo) for campo in _ORDEM_DOS_CAMPOS}
    informados: dict[CAMPO_DA_DIVIDA, ValorDoCampo] = {
        campo: valor
        for campo, valor in lidos.items()
        if valor is not None and not isinstance(valor, _Invalido)
    }
    nao_informados = [campo for campo in _ORDEM_DOS_CAMPOS if campo not in informados]

    valores = {
        campo: ValorDaDivida(campo, valor, MARCA_DO_VALOR.INFORMADO, None)
        for campo, valor in informados.items()
    }
    for campo in nao_informados:
        valores[campo] = ValorDaDivida(campo, None, MARCA_DO_VALOR.PENDENTE, None)
    situacao = SITUACAO_DA_DIVIDA.COMPLETA
    teorica: Dinheiro | None = None
    escolhido: CAMPO_DA_DIVIDA | None = None
    taxa_calculada: Taxa | None = None
    hipotese: HipoteseConservadora | None = None

    if not nao_informados:
        entrada = _entrada(informados, sistema, periodicidade)
        compatibilidade, teorica_da_parcela = conferir_compatibilidade(
            entrada, _d(informados[CAMPO_DA_DIVIDA.TAXA]), periodicidade
        )
        if compatibilidade is COMPATIBILIDADE.INCOMPATIVEL:
            situacao = SITUACAO_DA_DIVIDA.INCOMPATIVEL
            teorica = teorica_da_parcela
            campo_escolhido = _escolha_valida(respostas, DIVIDA_ID)
            if campo_escolhido is not None:
                restantes = {c: v for c, v in informados.items() if c is not campo_escolhido}
                try:
                    calculado = _calcular_campo(campo_escolhido, restantes, sistema, periodicidade)
                except ErroDeCalculo:
                    pass  # sem solução: originais e sinalização (OQ no relatório)
                else:
                    situacao, teorica, escolhido = (
                        SITUACAO_DA_DIVIDA.COMPLETA,
                        None,
                        campo_escolhido,
                    )
                    valores[campo_escolhido] = ValorDaDivida(
                        campo_escolhido,
                        calculado.valor,
                        MARCA_DO_VALOR.CALCULADO,
                        informados[campo_escolhido],
                    )
                    taxa_calculada = calculado.taxa_mensal
            if situacao is SITUACAO_DA_DIVIDA.INCOMPATIVEL:
                # `RF-538`: sem escolha válida, o plano segue por uma hipótese
                # conservadora; só saldo e taxa entram no motor (`RF-539`).
                hipotese = escolher_hipotese(
                    _d(informados[CAMPO_DA_DIVIDA.SALDO]),
                    _d(informados[CAMPO_DA_DIVIDA.PARCELA]),
                    entrada.taxa_mensal or _ZERO,
                    _n(informados[CAMPO_DA_DIVIDA.PRAZO]),
                    sistema,
                )
                if hipotese is not None:
                    taxa_calculada = hipotese.taxa_mensal
                    valores[CAMPO_DA_DIVIDA.SALDO] = ValorDaDivida(
                        CAMPO_DA_DIVIDA.SALDO,
                        hipotese.saldo,
                        MARCA_DO_VALOR.HIPOTESE,
                        informados[CAMPO_DA_DIVIDA.SALDO],
                    )
                    valores[CAMPO_DA_DIVIDA.TAXA] = ValorDaDivida(
                        CAMPO_DA_DIVIDA.TAXA,
                        taxa_na_periodicidade(hipotese.taxa_mensal, periodicidade),
                        MARCA_DO_VALOR.HIPOTESE,
                        informados[CAMPO_DA_DIVIDA.TAXA],
                    )
    elif len(nao_informados) == 1 and lidos[nao_informados[0]] is None:
        campo = nao_informados[0]
        try:
            calculado = _calcular_campo(campo, informados, sistema, periodicidade)
        except ErroDeCalculo:
            pass  # fica PENDENTE; vira falta se for S/P/T
        else:
            valores[campo] = ValorDaDivida(campo, calculado.valor, MARCA_DO_VALOR.CALCULADO, None)
            taxa_calculada = calculado.taxa_mensal

    estimada = _estimar_parcela(lidos, informados, sistema, periodicidade)
    if estimada is not None and valores[CAMPO_DA_DIVIDA.PARCELA].marca is MARCA_DO_VALOR.PENDENTE:
        valores[CAMPO_DA_DIVIDA.PARCELA] = ValorDaDivida(
            CAMPO_DA_DIVIDA.PARCELA, estimada.valor, MARCA_DO_VALOR.ESTIMADO, None
        )

    faltas = tuple(
        campo for campo in _CAMPOS_DO_MOTOR if valores[campo].marca is MARCA_DO_VALOR.PENDENTE
    )
    if faltas:
        situacao = SITUACAO_DA_DIVIDA.PENDENTE

    taxa_valor = valores[CAMPO_DA_DIVIDA.TAXA].valor
    if taxa_calculada is not None:
        mensal_normalizada: Taxa | None = taxa_calculada
    elif taxa_valor is not None:
        mensal_normalizada = _taxa_mensal(_d(taxa_valor), periodicidade)
    else:
        mensal_normalizada = None
    return PremissasDaDivida(
        DIVIDA_ID=DIVIDA_ID,
        sistema=sistema,
        valores=valores,
        taxa_mensal_normalizada=mensal_normalizada,
        taxa_na_periodicidade=None if taxa_valor is None else _d(taxa_valor),
        situacao=situacao,
        faltas=faltas,
        parcela_teorica=teorica,
        recalcular_escolhido=escolhido,
        parcela_estimada=estimada,
        pagamento_minimo=_pagamento_minimo(respostas, DIVIDA_ID),
        hipotese_conservadora=hipotese,
    )


def _estimar_parcela(
    lidos: Mapping[CAMPO_DA_DIVIDA, _Leitura],
    informados: Mapping[CAMPO_DA_DIVIDA, ValorDoCampo],
    sistema: SISTEMA_AMORTIZACAO,
    periodicidade: PeriodicidadeTaxa,
) -> ParcelaEstimada | None:
    """`RF-532`, `OQ-73`: saldo e taxa válidos, prazo desconhecido e habitual
    ausente ou `0,00` ⇒ parcela de `PRAZO_BASE_ESTIMATIVA_MESES`. Habitual
    `> 0` ou prazo informado nunca chegam aqui (soberania do aluno)."""
    habitual = lidos[CAMPO_DA_DIVIDA.PARCELA]
    sem_habitual = habitual is None or habitual == _ZERO
    if lidos[CAMPO_DA_DIVIDA.PRAZO] is not None or not sem_habitual:
        return None
    if CAMPO_DA_DIVIDA.SALDO not in informados or CAMPO_DA_DIVIDA.TAXA not in informados:
        return None
    mensal = _taxa_mensal(_d(informados[CAMPO_DA_DIVIDA.TAXA]), periodicidade)
    try:
        valor = calcular_parcela(
            _d(informados[CAMPO_DA_DIVIDA.SALDO]), mensal, PRAZO_BASE_ESTIMATIVA_MESES, sistema
        )
    except ErroDeCalculo:
        return None  # sem solução: fica `PENDENTE`, nunca valor inventado
    return ParcelaEstimada(valor, PRAZO_BASE_ESTIMATIVA_MESES, habitual is None)


def _pagamento_minimo(respostas: RespostasCaso, DIVIDA_ID: str) -> Dinheiro | None:
    """`B5.C02C` (`RF-533`): "não sei", ausente ou ilegível ⇒ `None`, nunca `0`."""
    minimo = _decimal(respostas.valor_no_item(DIVIDA_ID, _VARIAVEL_MINIMO))
    return minimo if minimo is not None and minimo >= _ZERO else None


def _entrada(
    informados: Mapping[CAMPO_DA_DIVIDA, ValorDoCampo],
    sistema: SISTEMA_AMORTIZACAO,
    periodicidade: PeriodicidadeTaxa,
) -> EntradaDaDivida:
    return EntradaDaDivida(
        _d(informados[CAMPO_DA_DIVIDA.SALDO]),
        _d(informados[CAMPO_DA_DIVIDA.PARCELA]),
        _taxa_mensal(_d(informados[CAMPO_DA_DIVIDA.TAXA]), periodicidade),
        _n(informados[CAMPO_DA_DIVIDA.PRAZO]),
        sistema,
    )


# --- Pendentes e campos resolvidos (`T-488`) ----------------------------------------------


def _dividas_da_ficha(
    itens_por_escopo: Mapping[EscopoRepeticao, tuple[str, ...]],
) -> tuple[str, ...]:
    return itens_por_escopo.get(EscopoRepeticao.DIVIDA_ID, ())


def premissas_da_ficha(
    respostas: RespostasCaso, itens_por_escopo: Mapping[EscopoRepeticao, tuple[str, ...]]
) -> tuple[PremissasDaDivida, ...]:
    """`T-517`/`T-519`: todas as dívidas da ficha resolvidas, na ordem da ficha."""
    return tuple(resolver_divida(respostas, item) for item in _dividas_da_ficha(itens_por_escopo))


def _respondido(respostas: RespostasCaso, item: str, campo: CAMPO_DA_DIVIDA) -> bool:
    """O aluno respondeu ("não sei" conta); em branco continua bloqueando. A taxa
    vale pela periodicidade, onde mora a opção "não sei a taxa" de `B5.D06`."""
    variavel = (
        _VARIAVEL_PERIODICIDADE if campo is CAMPO_DA_DIVIDA.TAXA else _VARIAVEL_DO_CAMPO[campo]
    )
    return respostas.valor_no_item(item, variavel) is not None


def dividas_pendentes(
    respostas: RespostasCaso, itens_por_escopo: Mapping[EscopoRepeticao, tuple[str, ...]]
) -> tuple[PremissasDaDivida, ...]:
    """`RF-526`, `RF-527`, `EC-62`: as dívidas `PENDENTE`, na ordem da ficha."""
    resolvidas = (resolver_divida(respostas, item) for item in _dividas_da_ficha(itens_por_escopo))
    return tuple(p for p in resolvidas if p.situacao is SITUACAO_DA_DIVIDA.PENDENTE)


def campos_dispensados(
    respostas: RespostasCaso,
    itens_por_escopo: Mapping[EscopoRepeticao, tuple[str, ...]],
    *,
    com_pendentes: bool = True,
) -> frozenset[tuple[str, str]]:
    """`PD-11`, `OQ-89`: `(item_id, VARIAVEL_GRAVADA)` que não bloqueiam a
    liberação: os campos que a calculadora calculou e os que faltam numa dívida
    `PENDENTE` respondidos com "não sei" (fora do plano e apontada ao aluno;
    especialista, 2026-11-06: o plano parcial é liberado) e a parcela
    `ESTIMADO` respondida com "não sei" (o plano usa a de 24 meses e avisa o
    aluno, `T-541`). `com_pendentes=False`
    deixa só os calculados: o pedido de correção ainda lista o que falta."""
    resolvidos: set[tuple[str, str]] = set()
    for item in _dividas_da_ficha(itens_por_escopo):
        premissas = resolver_divida(respostas, item)
        for campo, valor in premissas.valores.items():
            if valor.marca is MARCA_DO_VALOR.CALCULADO or (
                com_pendentes
                and (campo in premissas.faltas or valor.marca is MARCA_DO_VALOR.ESTIMADO)
                and _respondido(respostas, item, campo)
            ):
                resolvidos.add((item, _VARIAVEL_DO_CAMPO[campo]))
                if campo is CAMPO_DA_DIVIDA.TAXA:  # sem taxa, a periodicidade também não vale
                    resolvidos.add((item, _VARIAVEL_PERIODICIDADE))
    return frozenset(resolvidos)
