"""Fonte de comprovação e pendências de homologação — `RF-91`, `RF-93`
(`T-261`, `T-263`).

`AC-140`, `EC-36`, `EC-39` sobre os registros REAIS: o nível é atributo da
opção no YAML, e o teste lê o YAML carregado — nunca uma cópia do mapa.
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import cache

import pytest

from app.revisao.comprovacao import (
    NivelDaFicha,
    PendenciaHomologacao,
    niveis_por_ficha,
    pendencias_de_homologacao,
)
from collection.carga import carregar_registros
from collection.registro import NIVEL_COMPROVACAO, EscopoRepeticao, RegistroPergunta
from collection.respostas import NAO_SEI, Resposta, RespostasCaso

_N = NIVEL_COMPROVACAO

# `AC-140` / `EC-36` — `valor_interno` → nível esperado, por pergunta de fonte.
# (`B7.16` e `B8.15` saíram com os Blocos 7 e 8, `T-390`; sobra `B5.I02`.)
_NIVEIS_ESPERADOS: dict[str, dict[str, NIVEL_COMPROVACAO]] = {
    "B5.I02": {
        "DOCUMENTO_CONTRATO": _N.COMPROVADO,
        "APLICATIVO": _N.COMPROVADO,
        "CONTRACHEQUE": _N.COMPROVADO,
        "MEMORIA": _N.INFORMADO,
        "COMBINACAO": _N.INFORMADO,
        "OUTRA": _N.INFORMADO,
        "ATENDIMENTO_CREDOR": _N.PENDENTE_DE_CONFIRMACAO,
    },
}

_AGORA = datetime(2026, 9, 30, tzinfo=UTC)


@cache
def _registros() -> tuple[RegistroPergunta, ...]:
    return carregar_registros().registros


def _registro(ID: str) -> RegistroPergunta:
    return next(r for r in _registros() if r.ID == ID)


# ---------------------------------------------------------------------------
# T-261 — os níveis e `indispensavel` estão no YAML
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ID", sorted(_NIVEIS_ESPERADOS))
def test_t261_toda_opcao_das_perguntas_de_fonte_tem_nivel(ID: str) -> None:
    registro = _registro(ID)

    obtidos = {o.valor_interno: o.nivel_comprovacao for o in registro.opcoes}

    assert obtidos == _NIVEIS_ESPERADOS[ID]


def test_t261_outra_sobe_a_comprovado_so_com_documento_em_b5_i01() -> None:
    (outra,) = [o for o in _registro("B5.I02").opcoes if o.valor_interno == "OUTRA"]

    assert outra.nivel_comprovacao_se is not None
    assert outra.nivel_comprovacao_se.nivel is _N.COMPROVADO


def test_t261_classificacao_de_t218_segue_igual_nas_seis_opcoes() -> None:
    """`T-218`: os seis códigos de `B5.I02` não mudam — só "Outra" ganha o seu."""
    codigos = {o.valor_interno for o in _registro("B5.I02").opcoes}

    assert codigos == {
        "DOCUMENTO_CONTRATO",
        "APLICATIVO",
        "ATENDIMENTO_CREDOR",
        "CONTRACHEQUE",
        "MEMORIA",
        "COMBINACAO",
        "OUTRA",
    }


def test_t261_indispensaveis_sao_os_que_o_motor_le() -> None:
    """`R9-8`: saldo, parcela, taxa (valor e periodicidade na mesma pergunta,
    `B5.D06`, `T-393`) e renda — o motor não lê prazo."""
    indispensaveis = {r.ID for r in _registros() if r.indispensavel}

    assert indispensaveis == {"B3.01", "B5.B03", "B5.C02", "B5.D06"}


# ---------------------------------------------------------------------------
# T-263 — `niveis_por_ficha` e `pendencias_de_homologacao` sobre o YAML real
# ---------------------------------------------------------------------------

_D = "D001"
_ITENS = {EscopoRepeticao.DIVIDA_ID: (_D,)}

# O que abre a pergunta de fonte no item.
_ABRE_FONTE: dict[str, dict[str, object]] = {
    "B5.I02": {},
}

# Uma dívida com os quatro dados que o motor lê, todos respondidos.
_DIVIDA_COMPLETA: dict[str, object] = {
    "SALDO_DEVEDOR_ATUAL": "1000",
    "POSSUI_PARCELA_DEFINIDA": "SIM",
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


def _nivel_de(ID: str, no_item: dict[str, object]) -> NIVEL_COMPROVACAO | None:
    niveis = niveis_por_ficha(_registros(), _caso(no_item), _ITENS)
    (nivel,) = [n for n in niveis if n.origem_fonte == ID]
    return nivel.nivel


def _pendencias(no_item: dict[str, object], renda: object = "5000") -> set[tuple[str, str]]:
    return {
        (p.ID_PERGUNTA, p.motivo)
        for p in pendencias_de_homologacao(_registros(), _caso(no_item, renda), _ITENS)
    }


@pytest.mark.parametrize(
    ("ID", "valor", "esperado"),
    [(ID, valor, nivel) for ID, mapa in _NIVEIS_ESPERADOS.items() for valor, nivel in mapa.items()],
)
def test_ac140_cada_opcao_no_nivel_esperado(
    ID: str, valor: str, esperado: NIVEL_COMPROVACAO
) -> None:
    variavel = _registro(ID).VARIAVEL_GRAVADA
    assert variavel is not None

    assert _nivel_de(ID, {**_ABRE_FONTE[ID], variavel: valor}) is esperado


def test_ac140_outra_com_documento_associado_e_comprovado() -> None:
    no_item: dict[str, object] = {
        "FONTE_DADO": "OUTRA",
        "DOCUMENTACAO_DISPONIVEL": frozenset({"FATURA"}),
    }

    assert _nivel_de("B5.I02", no_item) is _N.COMPROVADO


def test_ac140_outra_sem_documento_e_informado() -> None:
    no_item: dict[str, object] = {
        "FONTE_DADO": "OUTRA",
        "DOCUMENTACAO_DISPONIVEL": frozenset({"NAO_TENHO_NENHUM_DOCUMENTO_AGORA"}),
    }

    assert _nivel_de("B5.I02", no_item) is _N.INFORMADO


def test_fonte_fechada_pela_condicao_nao_aparece_e_nao_respondida_e_none() -> None:
    niveis = niveis_por_ficha(_registros(), _caso({}), _ITENS)

    assert niveis == (NivelDaFicha(item_id=_D, origem_fonte="B5.I02", nivel=None),)


def test_ec39_seguro_nao_sei_e_nao_informado_nunca_nivel_3() -> None:
    no_item = {**_DIVIDA_COMPLETA, "SEGURO_PRESTAMISTA": "SIM", "SITUACAO_SEGURO": NAO_SEI}

    niveis = niveis_por_ficha(_registros(), _caso(no_item), _ITENS)

    assert all(n.nivel is not _N.PENDENTE_DE_CONFIRMACAO for n in niveis)
    assert _pendencias(no_item) == set()


def test_rf93_dados_completos_e_fonte_comprovada_nenhuma_pendencia() -> None:
    assert _pendencias({**_DIVIDA_COMPLETA, "FONTE_DADO": "DOCUMENTO_CONTRATO"}) == set()


def test_rf93_indispensavel_em_branco_ou_nao_sei_e_ausente() -> None:
    no_item = {**_DIVIDA_COMPLETA, "SALDO_DEVEDOR_ATUAL": NAO_SEI}
    del no_item["PERIODICIDADE_TAXA_DIVIDA"]

    assert _pendencias(no_item, renda=None) == {
        ("B3.01", "AUSENTE"),
        ("B5.B03", "AUSENTE"),
        ("B5.D06", "AUSENTE"),
    }


def test_rf93_fonte_em_nivel_3_pende_todo_indispensavel_da_ficha() -> None:
    no_item = {**_DIVIDA_COMPLETA, "FONTE_DADO": "ATENDIMENTO_CREDOR"}

    assert pendencias_de_homologacao(_registros(), _caso(no_item), _ITENS) == (
        PendenciaHomologacao(_D, "B5.B03", "PENDENTE_DE_CONFIRMACAO"),
        PendenciaHomologacao(_D, "B5.C02", "PENDENTE_DE_CONFIRMACAO"),
    )


def test_gab03_parcela_fechada_pela_condicao_rotativo_nunca_pende() -> None:
    no_item = {**_DIVIDA_COMPLETA, "POSSUI_PARCELA_DEFINIDA": "NAO"}
    del no_item["PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)"]

    assert _pendencias(no_item) == set()


def test_r9_9_taxa_anual_respondida_nao_pende() -> None:
    assert _pendencias({**_DIVIDA_COMPLETA, "PERIODICIDADE_TAXA_DIVIDA": "ANUAL"}) == set()


def test_t393_b5_d06_em_branco_e_ausente_e_nao_duplica_confirmacao() -> None:
    """`T-393`: a pergunta única de custo, em branco, pende como `AUSENTE`; em
    nível 3 de fonte ela (seleção) não vira `PENDENTE_DE_CONFIRMACAO`."""
    sem_custo = {**_DIVIDA_COMPLETA}
    del sem_custo["PERIODICIDADE_TAXA_DIVIDA"]
    nivel_3 = {**_DIVIDA_COMPLETA, "FONTE_DADO": "ATENDIMENTO_CREDOR"}

    assert _pendencias(sem_custo) == {("B5.D06", "AUSENTE")}
    assert ("B5.D06", "PENDENTE_DE_CONFIRMACAO") not in _pendencias(nivel_3)
