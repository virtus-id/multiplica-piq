"""Fonte de comprovação e pendências de homologação — `RF-91`, `RF-93`
(`T-261`, `T-263`).

`EC-39` e `RF-513` sobre os registros REAIS. A pergunta de fonte (`B5.I02`) saiu
em `RF-513`; o mecanismo de nível segue no código, sem dado que o alimente.
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import cache

from app.revisao.comprovacao import (
    niveis_por_ficha,
    pendencias_de_homologacao,
)
from collection.carga import carregar_registros
from collection.registro import NIVEL_COMPROVACAO, EscopoRepeticao, RegistroPergunta
from collection.respostas import NAO_SEI, Resposta, RespostasCaso

_N = NIVEL_COMPROVACAO

_AGORA = datetime(2026, 9, 30, tzinfo=UTC)


@cache
def _registros() -> tuple[RegistroPergunta, ...]:
    return carregar_registros().registros


# ---------------------------------------------------------------------------
# T-261 — os níveis e `indispensavel` estão no YAML
# ---------------------------------------------------------------------------


def test_t261_indispensaveis_sao_os_que_o_motor_le() -> None:
    """`R9-8`: saldo, parcela, taxa (valor e periodicidade na mesma pergunta,
    `B5.D06`, `T-393`) e renda — o motor não lê prazo. `B5.C02A` deixou de ser
    indispensável (`RF-523`, `OQ-93`, `T-493`): Price é o padrão."""
    indispensaveis = {r.ID for r in _registros() if r.indispensavel}

    assert indispensaveis == {"B3.01", "B5.B03", "B5.C02", "B5.D06"}


# ---------------------------------------------------------------------------
# T-263 — `niveis_por_ficha` e `pendencias_de_homologacao` sobre o YAML real
# ---------------------------------------------------------------------------

_D = "D001"
_ITENS = {EscopoRepeticao.DIVIDA_ID: (_D,)}

# Uma dívida com os quatro dados que o motor lê, todos respondidos.
_DIVIDA_COMPLETA: dict[str, object] = {
    "SALDO_DEVEDOR_ATUAL": "1000",
    "PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)": "100",
    "PERIODICIDADE_TAXA_DIVIDA": "MENSAL",
    "TAXA_DIVIDA": "0.02",
}


def _resposta(variavel: str, valor: object, item_id: str | None = None) -> Resposta:
    return Resposta(
        CASO_ID="CASO-COMPROVACAO",
        ID_PERGUNTA=variavel,
        item_id=item_id,
        valor=valor,  # type: ignore[arg-type]
        QUESTIONARIO_VERSION="1.0.3",
        respondida_em=_AGORA,
    )


def _caso(no_item: dict[str, object], renda: object = "5000") -> RespostasCaso:
    respostas = [_resposta(v, x, _D) for v, x in no_item.items()]
    if renda is not None:
        respostas.append(_resposta("RENDA_PRINCIPAL", renda))
    return RespostasCaso(respostas=tuple(respostas))


def _pendencias(no_item: dict[str, object], renda: object = "5000") -> set[tuple[str, str]]:
    return {
        (p.ID_PERGUNTA, p.motivo)
        for p in pendencias_de_homologacao(_registros(), _caso(no_item, renda), _ITENS)
    }


def test_ec39_seguro_nao_sei_e_nao_informado_nunca_nivel_3() -> None:
    no_item = {**_DIVIDA_COMPLETA, "SEGURO_PRESTAMISTA": "SIM", "SITUACAO_SEGURO": NAO_SEI}

    niveis = niveis_por_ficha(_registros(), _caso(no_item), _ITENS)

    assert all(n.nivel is not _N.PENDENTE_DE_CONFIRMACAO for n in niveis)
    assert _pendencias(no_item) == set()


def test_rf93_dados_completos_nenhuma_pendencia() -> None:
    assert _pendencias(_DIVIDA_COMPLETA) == set()


def test_rf93_indispensavel_em_branco_ou_nao_sei_e_ausente() -> None:
    no_item = {**_DIVIDA_COMPLETA, "SALDO_DEVEDOR_ATUAL": NAO_SEI}
    del no_item["PERIODICIDADE_TAXA_DIVIDA"]

    assert _pendencias(no_item, renda=None) == {
        ("B3.01", "AUSENTE"),
        ("B5.B03", "AUSENTE"),
        ("B5.D06", "AUSENTE"),
    }


def test_r9_9_taxa_anual_respondida_nao_pende() -> None:
    assert _pendencias({**_DIVIDA_COMPLETA, "PERIODICIDADE_TAXA_DIVIDA": "ANUAL"}) == set()


def test_t393_b5_d06_em_branco_e_ausente() -> None:
    """`T-393`: a pergunta única de custo, em branco, pende como `AUSENTE`."""
    sem_custo = {**_DIVIDA_COMPLETA}
    del sem_custo["PERIODICIDADE_TAXA_DIVIDA"]

    assert _pendencias(sem_custo) == {("B5.D06", "AUSENTE")}


def test_rf513_parcela_em_branco_e_ausente_em_toda_divida() -> None:
    """`RF-513`: `B5.C01` saiu; a parcela é sempre perguntada e indispensável."""
    sem_parcela = {**_DIVIDA_COMPLETA}
    del sem_parcela["PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)"]

    assert _pendencias(sem_parcela) == {("B5.C02", "AUSENTE")}


def test_rf513_nenhuma_pergunta_declara_fonte_de_comprovacao() -> None:
    """`RF-513`: sem `B5.I02` não há nível de comprovação nem confirmação pendente."""
    assert niveis_por_ficha(_registros(), _caso(_DIVIDA_COMPLETA), _ITENS) == ()
