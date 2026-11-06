"""Calculadora das quatro variáveis da dívida — `RF-514` a `RF-522`, `RF-524`.

Módulo **puro** (`PD-01`): `Decimal` sob `engine.precisao.CONTEXTO_MOTOR`,
`ln` e potência pelos métodos do próprio `Decimal`, sem `float`, sem I/O. Dado
três entre saldo, parcela, taxa e prazo (Price ou SAC), calcula o quarto.
Precedente: `app/montagem/entrada.py` — agregação de entrada, nunca o cálculo
do motor refeito: o prazo da tela sai da **mesma recorrência** do motor
(`PD-03`, `AC-526`), e `engine/` não é tocado (`RF-531`).

Toda constante `Decimal` nasce de `converter_para_dinheiro`/`converter_para_taxa`
(`PD-02`); este módulo não chama `Decimal(...)` nem `dinheiro(...)`.

Arredondamentos (`OQ-77`, `OQ-80`, `OQ-81`, `OQ-91` — ver plano, seção 4.3):
parcela e prazo **para cima**; saldo e taxa **para baixo**. Antes de cada um,
o valor passa por `RESIDUO_DE_ARREDONDAMENTO`, para que ruído de precisão
(`100,0000000000000000000000001`) não mude o centavo.

Simplificações declaradas:
- A parcela informada em SAC é a de hoje, a maior (`OQ-88`).
- O `cronograma` em SAC usa amortização `saldo / prazo` (`AC-521`, `AC-531`),
  não `parcela - saldo × taxa`; o argumento `parcela` só vale em Price.
  Price segue a recorrência integral do motor, só as linhas são arredondadas.
- Taxa negativa como resultado (parcela abaixo de `saldo / prazo`, SAC ou
  Price) não tem solução: vira `SEM_CONVERGENCIA`.

REGRAS: `RF-514`, `RF-515`, `RF-516`, `RF-517`, `RF-518`, `RF-519`, `RF-520`,
`RF-521`, `RF-522`, `RF-524`, `RF-530`, `EC-63`, `EC-64`, `EC-65`, `EC-66`,
`EC-67`, `EC-68`, `EC-69`
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import (
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_HALF_UP,
    Context,
    Decimal,
    localcontext,
)
from enum import Enum
from typing import Final, Literal

from app.montagem.conversao import (
    ErroConversaoInvalida,
    converter_para_dinheiro,
    converter_para_taxa,
)
from engine.precisao import CONTEXTO_MOTOR
from engine.taxa import derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA
from engine.tipos import SISTEMA_AMORTIZACAO, Dinheiro, Taxa

REGRAS: Final[tuple[str, ...]] = (
    "RF-514",
    "RF-515",
    "RF-516",
    "RF-517",
    "RF-518",
    "RF-519",
    "RF-520",
    "RF-521",
    "RF-522",
    "RF-524",
    "RF-530",
)

# --- Limites numéricos (plano, tabela 0.2 — `OQ-79`) ---------------------------
LIMITE_INICIAL_TAXA: Final[Taxa] = converter_para_taxa("1")  # 1% ao mês (`RF-516`)
TETO_TAXA_MENSAL: Final[Taxa] = converter_para_taxa("100")  # 100% ao mês
PRAZO_MAXIMO_MESES: Final[int] = 480
# `OQ-95`: teto de saldo e parcela (hipótese adotada, a confirmar).
VALOR_MAXIMO: Final[Dinheiro] = converter_para_dinheiro("1.000.000.000,00")
MAXIMO_ITERACOES_TAXA: Final[int] = 100
MAXIMO_DOBRAS_TAXA: Final[int] = 7  # 0,01 -> 1,28, travado em `TETO_TAXA_MENSAL`
TOLERANCIA_TAXA: Final[Taxa] = converter_para_dinheiro("0,000000000001")  # 1E-12
TOLERANCIA_FUNCAO: Final[Dinheiro] = converter_para_dinheiro("0,000000001")  # 1E-9 R$
RESIDUO_DE_ARREDONDAMENTO: Final[Dinheiro] = converter_para_dinheiro("0,000000001")

# --- Grade de compatibilidade (`OQ-78`) ----------------------------------------
FOLGA_DINHEIRO: Final[Dinheiro] = converter_para_dinheiro("0,005")
FOLGA_TAXA: Final[Taxa] = converter_para_taxa("0,005")  # 0,005 ponto percentual

_ZERO: Final[Dinheiro] = converter_para_dinheiro("0")
_UM: Final[Dinheiro] = converter_para_dinheiro("1")
_CENTAVO: Final[Dinheiro] = converter_para_dinheiro("0,01")
_SEIS_CASAS: Final[Taxa] = converter_para_dinheiro("0,000001")  # 4 casas do percentual
_DOZE: Final[int] = 12

# Dígitos de guarda: `1 - (1+i)^-n` subtrai números próximos quando `i` é
# pequeno (mesma técnica de `engine/taxa.py`).
_CONTEXTO_CALCULO: Final[Context] = Context(
    prec=CONTEXTO_MOTOR.prec + 10, rounding=CONTEXTO_MOTOR.rounding
)


# Mesmo domínio de `engine.taxa.PeriodicidadeTaxa`, redeclarado: o nome não está
# na allowlist de `test_fronteira_import_engine.py` (sem exceção nova).
type PeriodicidadeTaxa = Literal["MENSAL", "ANUAL"]


class CAMPO_DA_DIVIDA(Enum):
    SALDO = "SALDO"
    PARCELA = "PARCELA"
    TAXA = "TAXA"
    PRAZO = "PRAZO"


class CODIGO_ERRO_DE_ENTRADA(Enum):
    VALOR_ILEGIVEL = "VALOR_ILEGIVEL"
    SALDO_NAO_POSITIVO = "SALDO_NAO_POSITIVO"
    PARCELA_NAO_POSITIVA = "PARCELA_NAO_POSITIVA"
    TAXA_NEGATIVA = "TAXA_NEGATIVA"
    TAXA_ACIMA_DO_TETO = "TAXA_ACIMA_DO_TETO"
    PRAZO_NAO_INTEIRO = "PRAZO_NAO_INTEIRO"
    PRAZO_NAO_POSITIVO = "PRAZO_NAO_POSITIVO"
    PRAZO_ACIMA_DO_MAXIMO = "PRAZO_ACIMA_DO_MAXIMO"
    SALDO_ACIMA_DO_MAXIMO = "SALDO_ACIMA_DO_MAXIMO"
    PARCELA_ACIMA_DO_MAXIMO = "PARCELA_ACIMA_DO_MAXIMO"


class CODIGO_ERRO_DE_CALCULO(Enum):
    NAO_REDUZ_SALDO = "NAO_REDUZ_SALDO"
    SEM_CONVERGENCIA = "SEM_CONVERGENCIA"
    TAXA_ACIMA_DO_TETO = "TAXA_ACIMA_DO_TETO"
    PRAZO_ACIMA_DO_MAXIMO = "PRAZO_ACIMA_DO_MAXIMO"


class ErroDeEntrada(Exception):
    """`RF-518`: entrada recusada; nada é calculado nem salvo."""

    def __init__(self, campo: CAMPO_DA_DIVIDA, codigo: CODIGO_ERRO_DE_ENTRADA) -> None:
        self.campo = campo
        self.codigo = codigo
        super().__init__(f"{campo.value}: {codigo.value}")


class ErroDeCalculo(Exception):
    """`RF-519`: o cálculo não produz resultado válido; nada é devolvido."""

    def __init__(self, codigo: CODIGO_ERRO_DE_CALCULO) -> None:
        self.codigo = codigo
        super().__init__(codigo.value)


@dataclass(frozen=True, slots=True)
class EntradaDaDivida:
    """Tudo já tipado; `None` = desconhecido (não é erro). Taxa já mensal."""

    saldo: Dinheiro | None
    parcela: Dinheiro | None
    taxa_mensal: Taxa | None
    prazo: int | None
    sistema: SISTEMA_AMORTIZACAO


@dataclass(frozen=True, slots=True)
class LinhaDoCronograma:
    mes: int
    amortizacao: Dinheiro
    juros: Dinheiro
    pagamento: Dinheiro
    saldo_final: Dinheiro


class COMPATIBILIDADE(Enum):
    COMPATIVEL = "COMPATIVEL"
    INCOMPATIVEL = "INCOMPATIVEL"


# --- Validação de entrada (`T-473`) ---------------------------------------------


def _desconhecido(texto: str | None) -> bool:
    return texto is None or not texto.strip()


_MILHAR_BR: Final = re.compile(r"^-?\d{1,3}(\.\d{3})+$")


def _ponto_decimal(texto: str) -> bool:
    """`AC-527`/`EC-69`: `1234.56` não é formato brasileiro; ponto sem vírgula
    só vale como milhar (`1.234`). O conversor genérico o leria como decimal."""
    t = texto.strip()
    return "." in t and "," not in t and not _MILHAR_BR.match(t)


def _ler(texto: str, campo: CAMPO_DA_DIVIDA) -> Decimal:
    if _ponto_decimal(texto):
        raise ErroDeEntrada(campo, CODIGO_ERRO_DE_ENTRADA.VALOR_ILEGIVEL)
    try:
        return converter_para_dinheiro(texto)
    except ErroConversaoInvalida as erro:
        raise ErroDeEntrada(campo, CODIGO_ERRO_DE_ENTRADA.VALOR_ILEGIVEL) from erro


def validar_entrada(
    saldo: str | None = None,
    parcela: str | None = None,
    taxa: str | None = None,
    prazo: str | None = None,
    *,
    periodicidade: PeriodicidadeTaxa = "MENSAL",
    sistema: SISTEMA_AMORTIZACAO = SISTEMA_AMORTIZACAO.PRICE,
) -> EntradaDaDivida:
    """`RF-518`, `RF-530`, `EC-69`: texto brasileiro -> tipos. `None`/`""` é
    desconhecido. A taxa (percentual digitado) é normalizada ao mês pelo
    motor (`PD-04`) e então comparada ao teto."""
    saldo_lido = None
    if not _desconhecido(saldo):
        saldo_lido = _ler(str(saldo), CAMPO_DA_DIVIDA.SALDO)
        if saldo_lido <= _ZERO:
            raise ErroDeEntrada(CAMPO_DA_DIVIDA.SALDO, CODIGO_ERRO_DE_ENTRADA.SALDO_NAO_POSITIVO)
        if saldo_lido > VALOR_MAXIMO:
            raise ErroDeEntrada(CAMPO_DA_DIVIDA.SALDO, CODIGO_ERRO_DE_ENTRADA.SALDO_ACIMA_DO_MAXIMO)

    parcela_lida = None
    if not _desconhecido(parcela):
        parcela_lida = _ler(str(parcela), CAMPO_DA_DIVIDA.PARCELA)
        if parcela_lida <= _ZERO:
            raise ErroDeEntrada(
                CAMPO_DA_DIVIDA.PARCELA, CODIGO_ERRO_DE_ENTRADA.PARCELA_NAO_POSITIVA
            )
        if parcela_lida > VALOR_MAXIMO:
            raise ErroDeEntrada(
                CAMPO_DA_DIVIDA.PARCELA, CODIGO_ERRO_DE_ENTRADA.PARCELA_ACIMA_DO_MAXIMO
            )

    taxa_lida = None
    if not _desconhecido(taxa):
        try:
            if _ponto_decimal(str(taxa)):
                raise ErroConversaoInvalida(str(taxa), "ponto decimal")
            digitada = converter_para_taxa(str(taxa))
        except ErroConversaoInvalida as erro:
            raise ErroDeEntrada(
                CAMPO_DA_DIVIDA.TAXA, CODIGO_ERRO_DE_ENTRADA.VALOR_ILEGIVEL
            ) from erro
        if digitada < _ZERO:
            raise ErroDeEntrada(CAMPO_DA_DIVIDA.TAXA, CODIGO_ERRO_DE_ENTRADA.TAXA_NEGATIVA)
        taxa_lida = derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(digitada, periodicidade)
        if taxa_lida > TETO_TAXA_MENSAL:
            raise ErroDeEntrada(CAMPO_DA_DIVIDA.TAXA, CODIGO_ERRO_DE_ENTRADA.TAXA_ACIMA_DO_TETO)

    prazo_lido = None
    if not _desconhecido(prazo):
        bruto = _ler(str(prazo), CAMPO_DA_DIVIDA.PRAZO)
        if bruto != bruto.to_integral_value():
            raise ErroDeEntrada(CAMPO_DA_DIVIDA.PRAZO, CODIGO_ERRO_DE_ENTRADA.PRAZO_NAO_INTEIRO)
        if bruto <= _ZERO:
            raise ErroDeEntrada(CAMPO_DA_DIVIDA.PRAZO, CODIGO_ERRO_DE_ENTRADA.PRAZO_NAO_POSITIVO)
        if bruto > PRAZO_MAXIMO_MESES:
            raise ErroDeEntrada(CAMPO_DA_DIVIDA.PRAZO, CODIGO_ERRO_DE_ENTRADA.PRAZO_ACIMA_DO_MAXIMO)
        prazo_lido = int(bruto)

    return EntradaDaDivida(saldo_lido, parcela_lida, taxa_lida, prazo_lido, sistema)


# --- Arredondamento e conversão de taxa (`T-474`) --------------------------------


def _arredondar(valor: Decimal, passo: Decimal, modo: str) -> Decimal:
    with localcontext(_CONTEXTO_CALCULO):
        return valor.quantize(passo, rounding=modo)


def _limpar_residuo(valor: Decimal) -> Decimal:
    return _arredondar(valor, RESIDUO_DE_ARREDONDAMENTO, ROUND_HALF_UP)


def arredondar_taxa(taxa: Taxa) -> Taxa:
    """`OQ-81`: 6 casas da fração (4 do percentual), para baixo."""
    return _arredondar(_limpar_residuo(taxa), _SEIS_CASAS, ROUND_DOWN)


def taxa_anual_para_mensal(taxa_anual: Taxa) -> Taxa:
    """`RF-522`: a conversão é a do motor (`§16.1`), sem alteração."""
    return derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(taxa_anual, "ANUAL")


def taxa_mensal_para_anual(taxa_mensal: Taxa) -> Taxa:
    """`(1 + i)^12 - 1` (`PD-04`), para baixo em 6 casas da fração."""
    with localcontext(_CONTEXTO_CALCULO):
        anual = (_UM + taxa_mensal) ** _DOZE - _UM
    return arredondar_taxa(anual)


def taxa_na_periodicidade(taxa_mensal: Taxa, periodicidade: PeriodicidadeTaxa) -> Taxa:
    """`RF-522`: a taxa calculada volta na periodicidade que o aluno escolheu."""
    if periodicidade == "ANUAL":
        return taxa_mensal_para_anual(taxa_mensal)
    return taxa_mensal


# --- Fórmulas (`T-475` a `T-478`) --------------------------------------------------


def _parcela_exata(
    saldo: Dinheiro, taxa: Taxa, prazo: int, sistema: SISTEMA_AMORTIZACAO
) -> Dinheiro:
    with localcontext(_CONTEXTO_CALCULO):
        if sistema is SISTEMA_AMORTIZACAO.SAC:
            return saldo / prazo + saldo * taxa
        if taxa == _ZERO:
            return saldo / prazo
        return saldo * taxa / (_UM - (_UM + taxa) ** -prazo)


def calcular_parcela(
    saldo: Dinheiro, taxa_mensal: Taxa, prazo: int, sistema: SISTEMA_AMORTIZACAO
) -> Dinheiro:
    """`RF-514`, `RF-520`: para cima ao centavo, depois do resíduo."""
    exata = _parcela_exata(saldo, taxa_mensal, prazo, sistema)
    return _arredondar(_limpar_residuo(exata), _CENTAVO, ROUND_CEILING)


def calcular_saldo(
    parcela: Dinheiro, taxa_mensal: Taxa, prazo: int, sistema: SISTEMA_AMORTIZACAO
) -> Dinheiro:
    """`RF-514`, `OQ-80`/`OQ-91`: para baixo ao centavo (o centavo a mais
    faria o plano passar de `n` para `n + 1` meses)."""
    with localcontext(_CONTEXTO_CALCULO):
        if sistema is SISTEMA_AMORTIZACAO.SAC:
            exato = parcela / (_UM / prazo + taxa_mensal)
        elif taxa_mensal == _ZERO:
            exato = parcela * prazo
        else:
            exato = parcela * (_UM - (_UM + taxa_mensal) ** -prazo) / taxa_mensal
    saldo = _arredondar(_limpar_residuo(exato), _CENTAVO, ROUND_DOWN)
    if saldo <= _ZERO:
        raise ErroDeCalculo(CODIGO_ERRO_DE_CALCULO.SEM_CONVERGENCIA)  # saldo 0,00 não é resultado
    return saldo


def calcular_taxa(
    saldo: Dinheiro,
    parcela: Dinheiro,
    prazo: int,
    sistema: SISTEMA_AMORTIZACAO,
    *,
    maximo_iteracoes: int = MAXIMO_ITERACOES_TAXA,
    ao_dobrar_limite: Callable[[Taxa], None] | None = None,
) -> Taxa:
    """`RF-514`, `RF-516`, `RF-515`: SAC por fórmula fechada; Price por
    bisseção (limite superior inicial 1% que dobra até envolver a raiz).
    Não convergir ou passar do teto: `ErroDeCalculo`, nada devolvido.
    `ao_dobrar_limite` é um gancho de teste (`AC-524`)."""
    if sistema is SISTEMA_AMORTIZACAO.SAC:
        with localcontext(_CONTEXTO_CALCULO):
            sem_juros = saldo / prazo
            taxa = parcela / saldo - _UM / prazo
        if abs(sem_juros - parcela) <= FOLGA_DINHEIRO:
            return _ZERO  # mesma folga do Price (`RF-515`)
        return _conferir_resultado_da_taxa(taxa)

    with localcontext(_CONTEXTO_CALCULO):
        sem_juros = saldo / prazo
    if abs(sem_juros - parcela) <= FOLGA_DINHEIRO:
        return _ZERO  # `S/n` dentro de meio centavo de `P`: taxa 0 (`RF-515`)
    if sem_juros > parcela:
        raise ErroDeCalculo(CODIGO_ERRO_DE_CALCULO.SEM_CONVERGENCIA)  # taxa seria negativa

    def f(taxa: Taxa) -> Decimal:
        return _parcela_exata(saldo, taxa, prazo, sistema) - parcela

    inferior, superior = _ZERO, LIMITE_INICIAL_TAXA
    dobras = 0
    while f(superior) < _ZERO:
        if superior >= TETO_TAXA_MENSAL or dobras >= MAXIMO_DOBRAS_TAXA:
            raise ErroDeCalculo(CODIGO_ERRO_DE_CALCULO.TAXA_ACIMA_DO_TETO)
        inferior, superior = superior, min(superior * 2, TETO_TAXA_MENSAL)
        dobras += 1
        if ao_dobrar_limite is not None:
            ao_dobrar_limite(superior)

    for _ in range(maximo_iteracoes):
        meio = (inferior + superior) / 2
        valor = f(meio)
        if abs(valor) <= TOLERANCIA_FUNCAO:
            return _conferir_resultado_da_taxa(meio)
        if valor < _ZERO:
            inferior = meio
        else:
            superior = meio
        if superior - inferior <= TOLERANCIA_TAXA:
            return _conferir_resultado_da_taxa((inferior + superior) / 2)
    raise ErroDeCalculo(CODIGO_ERRO_DE_CALCULO.SEM_CONVERGENCIA)


def _conferir_resultado_da_taxa(taxa: Decimal) -> Taxa:
    if taxa < _ZERO:
        raise ErroDeCalculo(CODIGO_ERRO_DE_CALCULO.SEM_CONVERGENCIA)
    if taxa > TETO_TAXA_MENSAL:
        raise ErroDeCalculo(CODIGO_ERRO_DE_CALCULO.TAXA_ACIMA_DO_TETO)
    return arredondar_taxa(taxa)


def _meses_pela_recorrencia(saldo: Dinheiro, parcela: Dinheiro, taxa_mensal: Taxa) -> int:
    """`PD-03`: a recorrência do motor (`saldo × (1+i) − min(pagamento,
    saldo + juros)`), precisão integral, sem tolerância de resíduo."""
    with localcontext(CONTEXTO_MOTOR):
        restante = saldo
        for mes in range(1, PRAZO_MAXIMO_MESES + 1):
            com_juros = restante * (_UM + taxa_mensal)
            restante = com_juros - min(parcela, com_juros)
            if restante <= _ZERO:
                return mes
    raise ErroDeCalculo(CODIGO_ERRO_DE_CALCULO.PRAZO_ACIMA_DO_MAXIMO)


def calcular_prazo(
    saldo: Dinheiro, parcela: Dinheiro, taxa_mensal: Taxa, sistema: SISTEMA_AMORTIZACAO
) -> int:
    """`RF-514`, `RF-517`, `RF-519`: meses inteiros, para cima. Price: a
    fórmula fechada só **semeia** (rejeita de saída o prazo absurdo); o valor
    final vem da recorrência do motor."""
    with localcontext(_CONTEXTO_CALCULO):
        juros = saldo * taxa_mensal
        if parcela <= juros:
            raise ErroDeCalculo(CODIGO_ERRO_DE_CALCULO.NAO_REDUZ_SALDO)
        if sistema is SISTEMA_AMORTIZACAO.SAC or taxa_mensal == _ZERO:
            # SAC: a = P1 − S·i, n = ⌈S/a⌉. Taxa 0: a = P, n = ⌈S/P⌉ (Price e SAC iguais).
            prazo = int((saldo / (parcela - juros)).to_integral_value(rounding=ROUND_CEILING))
        else:
            semente = -(_UM - juros / parcela).ln() / (_UM + taxa_mensal).ln()
            if semente > PRAZO_MAXIMO_MESES + 1:
                raise ErroDeCalculo(CODIGO_ERRO_DE_CALCULO.PRAZO_ACIMA_DO_MAXIMO)
            prazo = _meses_pela_recorrencia(saldo, parcela, taxa_mensal)
    if prazo > PRAZO_MAXIMO_MESES:
        raise ErroDeCalculo(CODIGO_ERRO_DE_CALCULO.PRAZO_ACIMA_DO_MAXIMO)
    return max(prazo, 1)


# --- Cronograma e total de juros (`T-479`) -------------------------------------------


def _a_centavo(valor: Decimal) -> Dinheiro:
    return _arredondar(valor, _CENTAVO, ROUND_HALF_UP)


def cronograma(
    saldo: Dinheiro,
    parcela: Dinheiro,
    taxa_mensal: Taxa,
    prazo: int,
    sistema: SISTEMA_AMORTIZACAO,
) -> tuple[LinhaDoCronograma, ...]:
    """`RF-517`, `RF-521`: exibição em centavos. Price: a recorrência do motor
    em precisão integral (o prazo e o último pagamento batem com o plano,
    `AC-526`); pagamento = `parcela` e o último é **calculado** (saldo restante
    + juros), só as linhas são arredondadas. SAC: amortização `saldo / prazo`
    para baixo, o resíduo cai na última parcela (a soma fecha o saldo)."""
    linhas: list[LinhaDoCronograma] = []
    if sistema is SISTEMA_AMORTIZACAO.SAC:
        restante = _a_centavo(saldo)
        amortizacao_sac = _arredondar(restante / prazo, _CENTAVO, ROUND_DOWN)
        for mes in range(1, prazo + 1):
            juros = _a_centavo(restante * taxa_mensal)
            amortizacao = restante if mes == prazo else amortizacao_sac
            restante = restante - amortizacao
            linhas.append(LinhaDoCronograma(mes, amortizacao, juros, amortizacao + juros, restante))
        return tuple(linhas)

    with localcontext(CONTEXTO_MOTOR):
        restante = saldo
        for mes in range(1, prazo + 1):
            com_juros = restante * (_UM + taxa_mensal)
            juros = com_juros - restante
            if mes < prazo and parcela <= juros:
                raise ErroDeCalculo(CODIGO_ERRO_DE_CALCULO.NAO_REDUZ_SALDO)
            pagamento = com_juros if mes == prazo else min(parcela, com_juros)
            restante = com_juros - pagamento
            linhas.append(
                LinhaDoCronograma(
                    mes,
                    _a_centavo(pagamento) - _a_centavo(juros),
                    _a_centavo(juros),
                    _a_centavo(pagamento),
                    _a_centavo(restante),
                )
            )
            if restante <= _ZERO:
                break
    return tuple(linhas)


def total_de_juros(linhas: tuple[LinhaDoCronograma, ...]) -> Dinheiro:
    """`RF-529`: só para a prévia."""
    total = _ZERO
    for linha in linhas:
        total += linha.juros
    return total


# --- Conferência de compatibilidade (`T-480`) ------------------------------------------


def conferir_compatibilidade(
    entrada: EntradaDaDivida, taxa_digitada: Taxa, periodicidade: PeriodicidadeTaxa
) -> tuple[COMPATIBILIDADE, Dinheiro]:
    """`RF-524`, `OQ-78`: os quatro valores informados. Cada um vale uma faixa
    fixa (dinheiro ± R$ 0,005; taxa ± 0,005 pp na periodicidade digitada,
    renormalizada; prazo exato). A parcela é monótona crescente em saldo e em
    taxa, então o intervalo teórico vai de `P(S−δ, i−δ)` a `P(S+δ, i+δ)`;
    compatível quando encontra `[parcela ± 0,005]`. Devolve a parcela teórica."""
    if (
        entrada.saldo is None
        or entrada.parcela is None
        or entrada.taxa_mensal is None
        or entrada.prazo is None
    ):
        raise ValueError("RF-524: faltam valores")
    saldo, parcela, prazo, sistema = entrada.saldo, entrada.parcela, entrada.prazo, entrada.sistema
    teorica = calcular_parcela(saldo, entrada.taxa_mensal, prazo, sistema)

    taxa_inferior = derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(
        max(taxa_digitada - FOLGA_TAXA, _ZERO), periodicidade
    )
    taxa_superior = derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(
        taxa_digitada + FOLGA_TAXA, periodicidade
    )
    teorica_minima = _parcela_exata(
        max(saldo - FOLGA_DINHEIRO, _ZERO), taxa_inferior, prazo, sistema
    )
    teorica_maxima = _parcela_exata(saldo + FOLGA_DINHEIRO, taxa_superior, prazo, sistema)
    encontra = (
        teorica_minima <= parcela + FOLGA_DINHEIRO and teorica_maxima >= parcela - FOLGA_DINHEIRO
    )
    return (COMPATIBILIDADE.COMPATIVEL if encontra else COMPATIBILIDADE.INCOMPATIVEL), teorica
