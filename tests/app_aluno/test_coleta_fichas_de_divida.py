"""Ficha de dívida no `POST /resposta` — `T-291` (`RF-87`, `DE-04`) e
`T-292` (`RF-09`, `AC-11`).

Aplicação real, registros REAIS, repositórios em memória por
`app.dependency_overrides` (sem banco) — mesmo arranjo de
`test_rotas_coleta_fotografia.py`.

- `T-292`: "Sim, salvar dívida." em `B5.CHECK` com `B5.F02` aberta (por
  `B5.F01` = garantia "Sim") e em branco no item é recusado com
  `400` que lista o que falta; nada é gravado. (`T-389`: era `B5.D02`;
  `T-391`: era `B5.D05S`.)
- `T-643` (`RF-557`, `RF-558`): o mecanismo novo (`B5.FIM02` cria a ficha 1),
  isolado numa coleção REDUZIDA sem `B5.00` (`_trecho`).
- `T-652` (`RF-557`, `RF-558`): os dois testes antigos de `B5.00` (`T-291`)
  não têm mais pergunta para postar — `B5.00` saiu em `T-649`. Reescritos
  sobre a coleção REAL completa: zero fichas abre direto em `B5.A01`;
  fechar a única ficha (as 15 perguntas REP de `DIVIDA_ID`, a última por
  `POST`) reabre a lista, nunca serve `B5.FIM02`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from functools import cache

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.casos.maquina import ESTADO_CASO, Caso
from app.http.aplicacao import criar_aplicacao
from app.http.isolamento import obter_repositorio_casos
from app.http.rotas_coleta import (
    obter_colecao_de_registros,
    obter_repositorio_itens,
    obter_repositorio_respostas,
)
from app.http.sessao import iniciar_sessao_conta
from collection.carga import ColecaoDeRegistros, carregar_registros
from collection.registro import EscopoRepeticao
from collection.respostas import Resposta
from persistencia.app_aluno.itens import ItemRepetido
from tests.app_aluno.fixtures.caso_completo import DIVIDA_ID_UNICA, caso_completo

_CHAVE_TESTE = "chave-de-teste-para-assinatura-de-sessao-nao-usar-em-producao"
_CONTA = "CONTA-FICHA-1"
_CASO = "CASO-FICHA-1"
_AGORA = datetime(2026, 9, 30, tzinfo=UTC)


class _Respostas:
    def __init__(self, respostas: tuple[Resposta, ...]) -> None:
        self.respostas = list(respostas)

    def gravar(self, resposta: Resposta) -> None:
        self.respostas = [
            r
            for r in self.respostas
            if not (r.ID_PERGUNTA == resposta.ID_PERGUNTA and r.item_id == resposta.item_id)
        ] + [resposta]

    def listar_do_caso(self, caso_id: str) -> tuple[Resposta, ...]:
        return tuple(self.respostas)


class _Itens:
    def __init__(self, item_ids: tuple[str, ...]) -> None:
        self.itens = tuple(
            ItemRepetido(
                item_id=item_id,
                CASO_ID=_CASO,
                escopo=EscopoRepeticao.DIVIDA_ID,
                removido_em=None,
                criado_em=_AGORA,
            )
            for item_id in item_ids
        )

    def listar_do_caso(
        self, caso_id: str, *, incluir_removidos: bool = True
    ) -> tuple[ItemRepetido, ...]:
        return self.itens

    def proximo_identificador(
        self,
        CASO_ID: str,
        escopo: EscopoRepeticao,
        origem: str | None = None,
        item_pai_id: str | None = None,
    ) -> str:
        item_id = f"D{len(self.itens) + 1:03d}"
        self.itens = (
            *self.itens,
            ItemRepetido(
                item_id=item_id, CASO_ID=CASO_ID, escopo=escopo, removido_em=None, criado_em=_AGORA
            ),
        )
        return item_id


class _Casos:
    def buscar(self, caso_id: str) -> Caso | None:
        if caso_id != _CASO:
            return None
        return Caso(
            CASO_ID=_CASO,
            conta_id=_CONTA,
            estado=ESTADO_CASO.COLETA_INICIAL,
            DATA_REFERENCIA=date(2026, 9, 30),
            QUESTIONARIO_VERSION="1.0.3",
            snapshot_raiz_id=None,
            snapshot_liberado_id=None,
            ultima_interacao_em=_AGORA,
            criado_em=_AGORA,
        )

    def pertence_a_conta(self, caso_id: str, conta_id: str) -> bool:
        return caso_id == _CASO and conta_id == _CONTA


@cache
def _colecao_real() -> ColecaoDeRegistros:
    return carregar_registros()


def _trecho(*ids: str) -> ColecaoDeRegistros:
    reais = {r.ID: r for r in _colecao_real().registros}
    return ColecaoDeRegistros(
        QUESTIONARIO_VERSION="1.0.3", registros=tuple(reais[i] for i in ids)
    )


def _resposta(variavel: str, valor: object, item_id: str | None = None) -> Resposta:
    return Resposta(
        CASO_ID=_CASO,
        ID_PERGUNTA=variavel,
        item_id=item_id,
        valor=valor,  # type: ignore[arg-type]
        QUESTIONARIO_VERSION="1.0.3",
        respondida_em=_AGORA,
    )


def _cliente(
    monkeypatch: pytest.MonkeyPatch,
    respostas: tuple[Resposta, ...],
    item_ids: tuple[str, ...] = (),
    colecao: ColecaoDeRegistros | None = None,
) -> tuple[TestClient, _Respostas]:
    monkeypatch.setenv("CHAVE_ASSINATURA_SESSAO", _CHAVE_TESTE)
    repositorio = _Respostas(respostas)
    aplicacao = criar_aplicacao()
    aplicacao.dependency_overrides[obter_repositorio_casos] = _Casos
    aplicacao.dependency_overrides[obter_colecao_de_registros] = lambda: colecao or _colecao_real()
    aplicacao.dependency_overrides[obter_repositorio_respostas] = lambda: repositorio
    aplicacao.dependency_overrides[obter_repositorio_itens] = lambda: _Itens(item_ids)

    @aplicacao.post("/_teste/abrir-sessao/{conta_id}")
    def abrir_sessao(conta_id: str, request: Request) -> dict[str, str]:
        iniciar_sessao_conta(request, conta_id=conta_id)
        return {"conta_id": conta_id}

    cliente = TestClient(aplicacao, base_url="https://teste.local")
    cliente.post(f"/_teste/abrir-sessao/{_CONTA}")
    return cliente, repositorio


# Tudo que `caso_completo()` responde, MENOS a ficha de dívida (para zero
# fichas) e `B5.FIM02`/`QUANTIDADE_DIVIDAS_DECLARADA_INICIAL` (para a
# varredura não passar por eles antes de chegar a este teste) — o estado
# exatamente ANTES da última pergunta antes do Bloco 5. `DESEJA_PLANO_
# ACELERADO` (`B3.C02`, `OPT`, sem condição) falta na fixture — drift
# pré-existente e documentado (`T-640`, mesma falha de
# `test_perguntas_removidas_nao_existem_e_as_mantidas_continuam`); sem
# respondê-la a varredura pararia nela antes de alcançar o Bloco 5, e é
# por isso que este teste a posta por último, não como pré-condição muda.
def _respostas_quase_completas() -> tuple[Resposta, ...]:
    caso = caso_completo()
    return tuple(
        r
        for r in caso.respostas.respostas
        if r.item_id != DIVIDA_ID_UNICA
        and r.ID_PERGUNTA
        not in ("QUANTIDADE_DIVIDAS_DECLARADA_INICIAL", "CONFIRMACAO_FIM_CADASTRO")
    )


def test_t652_fim_da_coleta_inicial_sem_b5_00_abre_direto_em_b5_a01(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`T-652` (`RF-557`, `AC-592`): sem `B5.00` na coleção real, zero
    fichas — a última pergunta antes do Bloco 5 já entrega `B5.A01` de um
    item novo, em vez da lista (`T-311`, decisão do produto, 2026-10-01)."""
    cliente, _ = _cliente(monkeypatch, _respostas_quase_completas())

    gravada = cliente.post(
        f"/caso/{_CASO}/resposta", data={"ID_PERGUNTA": "B3.C02", "valor": "NAO"}
    )

    assert gravada.status_code == 200, gravada.text
    assert "DIVIDA_ID" not in gravada.json()["abrir_fichas"]
    assert gravada.json()["proxima"]["pergunta"]["ID"] == "B5.A01"
    assert gravada.json()["proxima"]["pergunta"]["item_id"] == "D001"


# As 15 perguntas `REP` de `DIVIDA_ID` da coleção real — todo `valor_interno`
# abaixo é o do registro real (`collection/registros/bloco-05.yaml`),
# caractere por caractere, mesma disciplina de `fixtures/caso_completo.py`.
# `B5.H04` fica de fora: é a última da ordem do registro, postada pelo teste
# para fechar a ficha. `B5.F01 = NAO` fecha a garantia sem abrir `B5.F02`/
# `B5.F03` (`COND`). `B5.CALC01` (`CONFERENCIA_DA_DIVIDA`) não passa pelo
# `POST /resposta` em produção (`T-496`, só a calculadora grava a marca) —
# aqui é gravada direto no repositório, como já faz
# `test_registro_calculo_divida.py::test_pergunta_ja_respondida_pela_
# composta_e_pulada`.
def _respostas_da_ficha_exceto_a_ultima(item_id: str) -> tuple[Resposta, ...]:
    valores = {
        "CREDOR": "Nubank",
        "TIPO_DIVIDA": "CARTAO_ROTATIVO",
        "CONFERENCIA_DA_DIVIDA": "CONFIRMADA",
        "SALDO_DEVEDOR_ATUAL": Decimal("5000.00"),
        "PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)": Decimal("300.00"),
        "PRAZO_RESTANTE_MESES": 12,
        "SISTEMA_AMORTIZACAO": "PRICE",
        "PERIODICIDADE_TAXA_DIVIDA": "MENSAL",
        "NEGATIVACAO": "NAO",
        "COBRANCA_JUDICIAL_INFORMADA": "NAO",
        "POSSUI_GARANTIA": "NAO",
        "PESO_EMOCIONAL": 5,
        "URGENCIA_PERCEBIDA": 5,
    }
    return tuple(_resposta(variavel, valor, item_id) for variavel, valor in valores.items())


def test_t652_fechar_a_unica_ficha_reabre_a_lista_sem_servir_fim02(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`T-652` (`RF-558`, `AC-593`, `AC-594`): fechar a única ficha (a
    última das 15 perguntas `REP` de `DIVIDA_ID`, sobre a coleção real
    completa) devolve a lista, nunca `B5.FIM02` isolada."""
    item_id = "D001"
    cliente, _ = _cliente(
        monkeypatch, _respostas_da_ficha_exceto_a_ultima(item_id), (item_id,)
    )

    gravada = cliente.post(
        f"/caso/{_CASO}/resposta",
        data={"ID_PERGUNTA": "B5.H04", "item_id": item_id, "valor": "NAO"},
    )

    assert gravada.status_code == 200, gravada.text
    assert gravada.json()["abrir_fichas"] == ["DIVIDA_ID"]
    assert gravada.json()["proxima"]["pergunta"]["ID"] != "B5.FIM02"


def test_t643_fim_do_bloco_4_sem_b5_00_abre_direto_em_b5_a01(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`T-643` (`RF-557`, `AC-592`): coleção sem `B5.00` — fechar a última
    pergunta do Bloco 4, com zero fichas, já entrega `B5.A01` de um item
    novo; `DIVIDA_ID` nunca aparece em `abrir_fichas` (a ficha já nasceu)."""
    colecao = _trecho("B4.02", "B5.A01", "B5.FIM02")
    cliente, _ = _cliente(monkeypatch, (), colecao=colecao)

    gravada = cliente.post(
        f"/caso/{_CASO}/resposta", data={"ID_PERGUNTA": "B4.02", "valor": "NAO"}
    )

    assert gravada.status_code == 200, gravada.text
    assert gravada.json()["proxima"]["pergunta"]["ID"] == "B5.A01"
    assert gravada.json()["proxima"]["pergunta"]["item_id"] == "D001"
    assert "DIVIDA_ID" not in gravada.json()["abrir_fichas"]


def test_t643_fechar_a_unica_ficha_reabre_a_lista_sem_servir_fim02(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`T-643` (`RF-558`, `AC-594`): uma ficha já criada e fechada (sem
    nenhuma resposta nova de quantidade) devolve a lista (`abrir_fichas`),
    nunca `B5.FIM02` isolada."""
    colecao = _trecho("B4.02", "B5.A01", "B5.FIM02")
    cliente, _ = _cliente(monkeypatch, (), ("D001",), colecao=colecao)

    gravada = cliente.post(
        f"/caso/{_CASO}/resposta",
        data={"ID_PERGUNTA": "B5.A01", "item_id": "D001", "valor": "Itaú"},
    )

    assert gravada.status_code == 200, gravada.text
    assert gravada.json()["abrir_fichas"] == ["DIVIDA_ID"]
    assert gravada.json()["proxima"]["pergunta"]["ID"] != "B5.FIM02"
