"""Testes da regra `§16.4` (`engine/prioridade_ordem.py`) — prioridade na ordem
de quitação: bem essencial, negativada, peso da garantia, urgência e escolha do
aluno. Cada teste cita o critério `§16.4-Cn` de `specs/motor-calculo.spec.md`.

Os métodos são exercitados pelo `SelecionarAlvo` (Avalanche, Bola de Neve e a
fase do Híbrido), o mesmo ponto onde `engine/motor.py` encaixa a regra.

REGRAS: §16.4
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal

import pytest

from engine.ciclo_mensal import EstadoSimulacao, SelecionarAlvo
from engine.estado import TIPO_DIVIDA, Divida
from engine.metodos.avalanche import criar_selecionar_alvo_avalanche
from engine.metodos.bola_de_neve import criar_selecionar_alvo_bola_de_neve
from engine.metodos.hibrido import criar_selecionar_alvo_forcar_depois_avalanche
from engine.parametros import Parametros
from engine.precisao import dinheiro
from engine.prioridade_ordem import aplicar_prioridade_ordem, peso_emocional_efetivo
from engine.tipos import (
    DESCONHECIDO,
    STATUS_DIVIDA,
    STATUS_VALIDADE_PROPOSTA,
    SimNaoTalvez,
)
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.conftest import assertar_exato

type Fabrica = Callable[[Mapping[str, Divida], Parametros], SelecionarAlvo]


def _hibrido(dividas: Mapping[str, Divida], p: Parametros) -> SelecionarAlvo:
    # Fase do Híbrido com D* inexistente: delega à Avalanche (H-07).
    return criar_selecionar_alvo_forcar_depois_avalanche("D-NENHUMA", dividas, p)


_METODOS: dict[str, Fabrica] = {
    "avalanche": criar_selecionar_alvo_avalanche,
    "bola_de_neve": criar_selecionar_alvo_bola_de_neve,
    "hibrido": _hibrido,
}
_TODOS = pytest.mark.parametrize("metodo", list(_METODOS))


def _p() -> Parametros:
    return FonteParametrosArquivo().carregar("1.0.1")


def _divida(divida_id: str, **sobrescritas: object) -> Divida:
    base: dict[str, object] = dict(
        DIVIDA_ID=divida_id,
        TIPO_DIVIDA=TIPO_DIVIDA.CONSIGNADO,
        STATUS_DIVIDA=STATUS_DIVIDA.ATIVA,
        SALDO_DEVEDOR_ATUAL=dinheiro("1000"),
        VALOR_QUITACAO_HOJE=dinheiro("1000"),
        QUITACAO_CONSULTADA=SimNaoTalvez.SIM,
        STATUS_VALIDADE_PROPOSTA=STATUS_VALIDADE_PROPOSTA.VIGENTE,
        TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal("0.02"),
        CET=DESCONHECIDO,
        PARCELA_CONTRATUAL=dinheiro("100"),
        PAGAMENTO_MENSAL_EFETIVO=dinheiro("100"),
        SEGURO_INCLUIDO_PARCELA=False,
        CUSTO_SEGURO=DESCONHECIDO,
        PESO_EMOCIONAL=0,
        RENEGOCIACAO_PENDENTE=False,
        TROCA_PENDENTE=False,
        RISCO_MATERIAL_IMINENTE=False,
        OPORTUNIDADE_VIGENTE=None,
    )
    base.update(sobrescritas)
    return Divida(**base)  # type: ignore[arg-type]


def _estado(
    dividas: Mapping[str, Divida],
    quitadas: frozenset[str] = frozenset(),
    alvo: str | None = None,
) -> EstadoSimulacao:
    return EstadoSimulacao(
        mes=1,
        saldos={i: d.SALDO_DEVEDOR_ATUAL for i, d in dividas.items()},  # type: ignore[misc]
        quitadas=quitadas,
        DIVIDA_ALVO_ATUAL=alvo,
        CAPACIDADE_ATAQUE_M=dinheiro("100"),
        ATAQUE_NAO_UTILIZADO_ACUMULADO=dinheiro("0"),
        DESEMBOLSO_ACUMULADO=dinheiro("0"),
    )


def _ordem(metodo: str, dividas: Mapping[str, Divida]) -> list[str]:
    """Ordem em que o método (com a regra) escolhe, quitando uma a uma."""
    p = _p()
    sel = aplicar_prioridade_ordem(_METODOS[metodo](dividas, p), dividas, p)
    quitadas: frozenset[str] = frozenset()
    ordem: list[str] = []
    while len(quitadas) < len(dividas):
        alvo = sel(_estado(dividas, quitadas), dinheiro("100"))
        assert alvo is not None
        ordem.append(alvo.DIVIDA_ID)
        quitadas = quitadas | {alvo.DIVIDA_ID}
    return ordem


def _ordem_do_metodo(metodo: str, dividas: Mapping[str, Divida]) -> list[str]:
    p = _p()
    sel = _METODOS[metodo](dividas, p)
    quitadas: frozenset[str] = frozenset()
    ordem: list[str] = []
    while len(quitadas) < len(dividas):
        alvo = sel(_estado(dividas, quitadas), dinheiro("100"))
        assert alvo is not None
        ordem.append(alvo.DIVIDA_ID)
        quitadas = quitadas | {alvo.DIVIDA_ID}
    return ordem


def _carteira(**por_id: Mapping[str, object]) -> dict[str, Divida]:
    return {i: _divida(i, **campos) for i, campos in por_id.items()}


# Três dívidas de mesmo saldo que os três métodos ordenam, sem a regra, como
# A, B, C: a taxa decrescente decide (benefício marginal e desempate `O-05`).
def _base() -> dict[str, dict[str, object]]:
    return {
        "A": dict(
            TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal("0.09"),
        ),
        "B": dict(
            TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal("0.06"),
        ),
        "C": dict(
            TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal("0.03"),
        ),
    }


def _com(**extras: Mapping[str, object]) -> dict[str, Divida]:
    base = _base()
    return {i: _divida(i, **{**campos, **extras.get(i, {})}) for i, campos in base.items()}


@_TODOS
def test_c1_sem_respostas_o_selecionar_alvo_e_o_do_metodo(metodo: str) -> None:
    """`§16.4-C1`: carteira sem os cinco campos — identidade e ordem idêntica."""
    dividas = _com()
    p = _p()
    sel = _METODOS[metodo](dividas, p)
    assert aplicar_prioridade_ordem(sel, dividas, p) is sel
    assertar_exato(_ordem(metodo, dividas), _ordem_do_metodo(metodo, dividas))
    assertar_exato(_ordem(metodo, dividas), ["A", "B", "C"])


@_TODOS
def test_c2_campos_neutros_mantem_a_ordem(metodo: str) -> None:
    """`§16.4-C2`: `NAO`/urgência ausente/sem garantia = regra não se aplica."""
    neutros = {"NEGATIVADA": False, "GARANTIA_ESSENCIAL": False, "TIPO_GARANTIA": None}
    dividas = _com(A=neutros, B=neutros, C=neutros)
    assertar_exato(_ordem(metodo, dividas), ["A", "B", "C"])


@_TODOS
def test_c3_bem_essencial_sobe_ao_topo(metodo: str) -> None:
    """`§16.4-C3`."""
    dividas = _com(C=dict(GARANTIA_ESSENCIAL=True, TIPO_GARANTIA="OUTRO_BEM"))
    assertar_exato(_ordem(metodo, dividas)[0], "C")
    assertar_exato(_ordem(metodo, dividas), ["C", "A", "B"])


@_TODOS
def test_c4_negativada_entra_antes(metodo: str) -> None:
    """`§16.4-C4`."""
    dividas = _com(C=dict(NEGATIVADA=True))
    assertar_exato(_ordem(metodo, dividas), ["C", "A", "B"])


@_TODOS
def test_c5_peso_da_garantia_imovel_veiculo_outros(metodo: str) -> None:
    """`§16.4-C5`: imóvel 3, veículo 2, outro 1, sem garantia 0."""
    dividas = _com(
        A=dict(TIPO_GARANTIA="OUTRO_BEM"),
        B=dict(TIPO_GARANTIA="VEICULO"),
        C=dict(TIPO_GARANTIA="IMOVEL"),
    )
    assertar_exato(_ordem(metodo, dividas), ["C", "B", "A"])
    sem_garantia = _com(B=dict(TIPO_GARANTIA="AVAL_FIANCA"))
    assertar_exato(_ordem(metodo, sem_garantia), ["B", "A", "C"])


@_TODOS
def test_c6_essencial_vence_negativada(metodo: str) -> None:
    """`§16.4-C6`."""
    dividas = _com(A=dict(NEGATIVADA=True), C=dict(GARANTIA_ESSENCIAL=True, TIPO_GARANTIA="OUTRA"))
    assertar_exato(_ordem(metodo, dividas), ["C", "A", "B"])


@_TODOS
def test_c7_negativada_vence_peso_da_garantia(metodo: str) -> None:
    """`§16.4-C7`: negativada com garantia 1 antes de não negativada com garantia 3."""
    dividas = _com(A=dict(TIPO_GARANTIA="IMOVEL"), C=dict(NEGATIVADA=True, TIPO_GARANTIA="OUTRA"))
    assertar_exato(_ordem(metodo, dividas), ["C", "A", "B"])


def test_c8_urgencia_soma_20_por_cento_ao_peso_emocional() -> None:
    """`§16.4-C8`: empate total na Bola de Neve; o peso efetivo desempata."""
    iguais = dict(
        SALDO_DEVEDOR_ATUAL=dinheiro("500"),
        VALOR_QUITACAO_HOJE=dinheiro("500"),
        TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal("0.05"),
    )
    sem_urgencia = _carteira(X=dict(iguais, PESO_EMOCIONAL=5), Y=dict(iguais, PESO_EMOCIONAL=4))
    assertar_exato(_ordem_do_metodo("bola_de_neve", sem_urgencia)[0], "X")
    com_urgencia = _carteira(
        X=dict(iguais, PESO_EMOCIONAL=5, URGENCIA_PERCEBIDA=0),
        Y=dict(iguais, PESO_EMOCIONAL=4, URGENCIA_PERCEBIDA=10),
    )
    assertar_exato(peso_emocional_efetivo(com_urgencia["X"]), Decimal("5"))
    assertar_exato(peso_emocional_efetivo(com_urgencia["Y"]), Decimal("6.0"))
    assertar_exato(_ordem_do_metodo("bola_de_neve", com_urgencia)[0], "Y")
    assertar_exato(peso_emocional_efetivo(_divida("Z", PESO_EMOCIONAL=DESCONHECIDO)), DESCONHECIDO)


def _duas_primeiras(taxa_a: str, taxa_b: str, **extras: Mapping[str, object]) -> dict[str, Divida]:
    """A e B são as duas primeiras do método; C é a terceira."""
    return _com(
        A=dict(TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal(taxa_a), **extras.get("A", {})),
        B=dict(TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal(taxa_b), **extras.get("B", {})),
        C=dict(TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal("0.01"), **extras.get("C", {})),
    )


@pytest.mark.parametrize(
    ("taxa_a", "taxa_b", "preferida_entra"),
    [
        ("0.0200", "0.0195", True),  # C9: 2,5%
        ("0.0200", "0.0180", False),  # C10: 10%
        ("0.0200", "0.0190", True),  # C11: exatamente 5%
    ],
)
def test_c9_c10_c11_escolha_do_aluno_ate_5_por_cento(
    taxa_a: str, taxa_b: str, preferida_entra: bool
) -> None:
    """`§16.4-C9`, `C10`, `C11`."""
    dividas = _duas_primeiras(taxa_a, taxa_b, B=dict(PREFERENCIA_QUITACAO=True))
    primeiro = _ordem("bola_de_neve", dividas)[0]
    assertar_exato(primeiro, "B" if preferida_entra else "A")


def test_c12_as_duas_ou_nenhuma_com_preferencia_mantem_a_ordem() -> None:
    """`§16.4-C12`."""
    ambas = _duas_primeiras(
        "0.0200", "0.0200", A=dict(PREFERENCIA_QUITACAO=True), B=dict(PREFERENCIA_QUITACAO=True)
    )
    assertar_exato(_ordem("bola_de_neve", ambas)[0], "A")
    so_a = _duas_primeiras("0.0200", "0.0200", A=dict(PREFERENCIA_QUITACAO=True))
    assertar_exato(_ordem("bola_de_neve", so_a)[0], "A")


@_TODOS
def test_c13_preferencia_nao_atravessa_grupos(metodo: str) -> None:
    """`§16.4-C13`: a preferência de uma dívida de grupo inferior não vale."""
    dividas = _com(
        A=dict(PREFERENCIA_QUITACAO=True, TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal("0.03")),
        C=dict(
            GARANTIA_ESSENCIAL=True,
            TIPO_GARANTIA="IMOVEL",
            TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal("0.03"),
        ),
    )
    assertar_exato(_ordem(metodo, dividas)[0], "C")


def test_c14_custo_desconhecido_nao_aplica_a_escolha() -> None:
    """`§16.4-C14`."""
    dividas = _duas_primeiras("0.0200", "0.0200", B=dict(PREFERENCIA_QUITACAO=True))
    dividas["B"] = _divida(
        "B",
        **{
            **_base()["B"],
            "TAXA_EFETIVA_MENSAL_NORMALIZADA": DESCONHECIDO,
            "PREFERENCIA_QUITACAO": True,
        },
    )
    assertar_exato(_ordem("bola_de_neve", dividas)[0], "A")


@_TODOS
def test_c15_alvo_vigente_nao_quitado_e_mantido(metodo: str) -> None:
    """`§16.4-C15`: o alvo fixo (`O-02`, `H-06`) nunca é trocado pela regra."""
    dividas = _com(C=dict(GARANTIA_ESSENCIAL=True, TIPO_GARANTIA="IMOVEL"))
    p = _p()
    sel = aplicar_prioridade_ordem(_METODOS[metodo](dividas, p), dividas, p)
    alvo = sel(_estado(dividas, alvo="B"), dinheiro("100"))
    assert alvo is not None
    assertar_exato(alvo.DIVIDA_ID, "B")


@_TODOS
def test_c16_determinismo(metodo: str) -> None:
    """`§16.4-C16`."""
    dividas = _com(B=dict(NEGATIVADA=True, PREFERENCIA_QUITACAO=True, URGENCIA_PERCEBIDA=7))
    assertar_exato(_ordem(metodo, dividas), _ordem(metodo, dividas))


def test_snapshot_antigo_sem_os_cinco_campos_e_lido_como_neutro() -> None:
    """`§16.4-C1` na persistência: snapshot gravado antes da regra reidrata neutro."""
    from engine.snapshot import _serializar_canonico
    from persistencia.arquivo.repositorio_snapshots import _divida as reidratar

    nova = _divida("N", NEGATIVADA=True, TIPO_GARANTIA="VEICULO", URGENCIA_PERCEBIDA=4)
    bruto = _serializar_canonico(nova)
    assert isinstance(bruto, dict)
    assert reidratar(bruto) == nova
    for campo in (
        "GARANTIA_ESSENCIAL",
        "NEGATIVADA",
        "TIPO_GARANTIA",
        "URGENCIA_PERCEBIDA",
        "PREFERENCIA_QUITACAO",
    ):
        del bruto[campo]
    assert reidratar(bruto) == _divida("N")
