"""Rotas da calculadora da dívida: prévia (sem gravar) e confirmação — `RF-518`,
`RF-519`, `RF-524`, `RF-525`, `RF-529`, `RF-530`, `AC-525`, `AC-528`, `AC-529`,
`AC-530`, `AC-541`, `EC-77` (`T-502` a `T-506`).

Aplicação real, registros REAIS, repositórios em memória por
`app.dependency_overrides` (mesmo padrão de `test_registro_calculo_divida.py`).

REGRAS: RF-518, RF-519, RF-524, RF-525, RF-529, RF-530
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from functools import cache
from pathlib import Path

import pytest
import yaml
from fastapi import Request
from fastapi.testclient import TestClient

from app.casos.maquina import ESTADO_CASO, Caso
from app.http import rotas_calculadora
from app.http.aplicacao import criar_aplicacao
from app.http.isolamento import obter_repositorio_casos
from app.http.rotas_coleta import (
    obter_colecao_de_registros,
    obter_repositorio_itens,
    obter_repositorio_respostas,
)
from app.http.sessao import iniciar_sessao_conta
from app.montagem.calculo_divida import (
    CAMPO_DA_DIVIDA,
    CODIGO_ERRO_DE_CALCULO,
    CODIGO_ERRO_DE_ENTRADA,
)
from app.montagem.premissas import (
    MARCA_DO_VALOR,
    SITUACAO_DA_DIVIDA,
    impressao_dos_valores,
    resolver_divida,
)
from collection.carga import ColecaoDeRegistros, carregar_registros
from collection.registro import EscopoRepeticao
from collection.respostas import NAO_SEI, Resposta, RespostasCaso
from engine.tipos import SISTEMA_AMORTIZACAO
from persistencia.app_aluno.itens import ItemRepetido
from persistencia.app_aluno.respostas import ErroGravacaoResposta

_RAIZ = Path(__file__).resolve().parent.parent.parent
_CHAVE_TESTE = "chave-de-teste-para-assinatura-de-sessao-nao-usar-em-producao"
_CONTA = "CONTA-CALCULADORA-1"
_CASO = "CASO-CALCULADORA-1"
_DIVIDA = "D001"
_AGORA = datetime(2026, 11, 4, tzinfo=UTC)
_PREVIA = f"/caso/{_CASO}/calculadora/previa"
_CONFIRMAR = f"/caso/{_CASO}/divida/{_DIVIDA}/calculadora/confirmar"
_FRASE_RF519 = (
    "Nas condições informadas, essa parcela não reduz o saldo devedor. "
    "Revise os dados ou simule outra condição."
)
_V_SALDO = "SALDO_DEVEDOR_ATUAL"
_V_PARCELA = "PARCELA_CONTRATUAL" + " (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)"


class _Respostas:
    def __init__(self) -> None:
        self.respostas: list[Resposta] = []
        self.chamadas: list[str] = []
        self.falhar_na_chamada: int | None = None

    def gravar(self, resposta: Resposta) -> None:
        if self.falhar_na_chamada is not None and len(self.chamadas) == self.falhar_na_chamada:
            raise ErroGravacaoResposta("falha simulada")
        self.chamadas.append(resposta.ID_PERGUNTA)
        self.respostas = [
            r
            for r in self.respostas
            if not (r.ID_PERGUNTA == resposta.ID_PERGUNTA and r.item_id == resposta.item_id)
        ] + [resposta]

    def listar_do_caso(self, caso_id: str) -> tuple[Resposta, ...]:
        return tuple(self.respostas)

    def valor(self, variavel: str) -> object:
        return next(r.valor for r in self.respostas if r.ID_PERGUNTA == variavel)


class _Itens:
    def listar_do_caso(self, caso_id: str, *, incluir_removidos: bool = True) -> tuple[object, ...]:
        return (
            ItemRepetido(
                item_id=_DIVIDA,
                CASO_ID=_CASO,
                escopo=EscopoRepeticao.DIVIDA_ID,
                removido_em=None,
                criado_em=_AGORA,
                origem=None,
            ),
        )


class _Casos:
    estado = ESTADO_CASO.COLETA_INICIAL

    def buscar(self, caso_id: str) -> Caso | None:
        if caso_id != _CASO:
            return None
        return Caso(
            CASO_ID=_CASO,
            conta_id=_CONTA,
            estado=type(self).estado,
            DATA_REFERENCIA=date(2026, 11, 4),
            QUESTIONARIO_VERSION="1.5.0",
            snapshot_raiz_id=None,
            snapshot_liberado_id=None,
            ultima_interacao_em=_AGORA,
            criado_em=_AGORA,
        )

    def pertence_a_conta(self, caso_id: str, conta_id: str) -> bool:
        return caso_id == _CASO and conta_id == _CONTA


@cache
def _colecao() -> ColecaoDeRegistros:
    return carregar_registros()


def _cliente(
    monkeypatch: pytest.MonkeyPatch, *, com_sessao: bool = True
) -> tuple[TestClient, _Respostas]:
    monkeypatch.setenv("CHAVE_ASSINATURA_SESSAO", _CHAVE_TESTE)
    _Casos.estado = ESTADO_CASO.COLETA_INICIAL
    respostas = _Respostas()
    aplicacao = criar_aplicacao()
    aplicacao.dependency_overrides[obter_repositorio_casos] = _Casos
    aplicacao.dependency_overrides[obter_colecao_de_registros] = _colecao
    aplicacao.dependency_overrides[obter_repositorio_respostas] = lambda: respostas
    aplicacao.dependency_overrides[obter_repositorio_itens] = _Itens

    @aplicacao.post("/_teste/abrir-sessao/{conta_id}")
    def abrir_sessao(conta_id: str, request: Request) -> dict[str, str]:
        iniciar_sessao_conta(request, conta_id=conta_id)
        return {"conta_id": conta_id}

    cliente = TestClient(aplicacao, base_url="https://teste.local")
    if com_sessao:
        cliente.post(f"/_teste/abrir-sessao/{_CONTA}")
    return cliente, respostas


def _corpo(**campos: object) -> dict[str, object]:
    base: dict[str, object] = {
        "sistema": "PRICE",
        "periodicidade": "MENSAL",
        "saldo": "10.000,00",
        "parcela": "528,72",
        "taxa": "2,00",
        "prazo": "24",
        "recalcular": None,
    }
    return {**base, **campos}


# --------------------------------------------------------------- T-502: textos


def test_ac528_frase_do_rf519_identica_a_da_spec_e_ao_yaml() -> None:
    spec = (_RAIZ / "specs" / "calculo-de-divida.spec.md").read_text(encoding="utf-8")
    linha = next(row for row in spec.splitlines() if row.startswith("| `RF-519`"))
    frase_da_spec = re.search(r'mostra exatamente: "([^"]+)"', linha)
    assert frase_da_spec is not None
    assert frase_da_spec.group(1) == _FRASE_RF519

    textos = yaml.safe_load(rotas_calculadora.CAMINHO_TEXTOS_CALCULADORA.read_text("utf-8"))
    assert set(textos["erros_de_calculo"].values()) == {_FRASE_RF519}


def test_todo_codigo_de_erro_estado_e_marca_tem_chave() -> None:
    textos = yaml.safe_load(rotas_calculadora.CAMINHO_TEXTOS_CALCULADORA.read_text("utf-8"))
    assert set(textos["erros_de_calculo"]) == {c.value for c in CODIGO_ERRO_DE_CALCULO}
    assert set(textos["erros_de_entrada"]) == {c.value for c in CODIGO_ERRO_DE_ENTRADA}
    assert set(textos["marcas"]) == {m.value for m in MARCA_DO_VALOR}
    assert set(textos["estados"]) >= {"CALCULADO", "CONFERIDO", "INCOMPATIVEL", "PENDENTE"}


def test_nenhum_texto_leva_marcador_provisorio() -> None:
    """Textos aprovados: nenhum marcador `[PROVISORIO ...]` sobra."""
    textos = yaml.safe_load(rotas_calculadora.CAMINHO_TEXTOS_CALCULADORA.read_text("utf-8"))
    assert not [x for g in textos.values() for x in g.values() if "[PROVISORIO" in x]


# ---------------------------------------------------------------- T-503: prévia


def test_previa_compativel_e_conferida_com_resumo(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    resposta = cliente.post(_PREVIA, json=_corpo(parcela="528,71"))
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert dados["estado"] == "CONFERIDO"  # AC-535
    assert dados["campo_calculado"] is None
    assert dados["valores"]["PARCELA"]["texto"] == "R$ 528,71"
    assert dados["valores"]["PARCELA"]["marca"] == "INFORMADO"
    assert dados["resumo"]["prazo"] == 24
    assert set(dados["resumo"]) == {
        "prazo",
        "primeira_parcela",
        "ultimo_pagamento",
        "total_de_juros",
    }
    assert repositorio.respostas == []  # AC-529: nada gravado


def test_previa_incompativel_traz_teorico_e_alternativas(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, _ = _cliente(monkeypatch)
    dados = cliente.post(_PREVIA, json=_corpo(parcela="400,00")).json()
    assert dados["estado"] == "INCOMPATIVEL"  # AC-534
    assert dados["teorico"] == {"campo": "PARCELA", "texto": "R$ 528,72"}
    assert dados["alternativas"] == ["SALDO", "PARCELA", "TAXA", "PRAZO"]
    assert dados["resumo"] is None


@pytest.mark.parametrize(
    ("campo", "texto_esperado"),
    [("PARCELA", "R$ 528,72"), ("SALDO", "R$ 7.567,53")],
)
def test_ac536_recalcular_o_campo_escolhido_o_marca_como_calculado(
    monkeypatch: pytest.MonkeyPatch, campo: str, texto_esperado: str
) -> None:
    cliente, _ = _cliente(monkeypatch)
    dados = cliente.post(_PREVIA, json=_corpo(parcela="400,00", recalcular=campo)).json()
    assert dados["estado"] == "CALCULADO"
    assert dados["campo_calculado"] == campo
    assert dados["valores"][campo]["marca"] == "CALCULADO"
    if campo == "PARCELA":
        assert dados["valores"][campo]["texto"] == texto_esperado
    else:
        assert dados["valores"]["PARCELA"]["texto"] == "R$ 400,00"
        assert dados["valores"]["SALDO"]["marca"] == "CALCULADO"


@pytest.mark.parametrize(
    ("campos", "campo", "texto"),
    [
        ({"prazo": None}, "PRAZO", "24"),
        ({"parcela": None}, "PARCELA", "R$ 528,72"),
        ({"parcela": None, "sistema": "SAC"}, "PARCELA", "R$ 616,67"),
        ({"taxa": None}, "TAXA", "2% a.m."),
        ({"taxa": None, "periodicidade": "ANUAL"}, "TAXA", "26,83% a.a."),
    ],
)
def test_previa_calcula_o_unico_valor_desconhecido(
    monkeypatch: pytest.MonkeyPatch, campos: dict[str, object], campo: str, texto: str
) -> None:
    cliente, _ = _cliente(monkeypatch)
    dados = cliente.post(_PREVIA, json=_corpo(**campos)).json()
    assert dados["estado"] == "CALCULADO", dados
    assert dados["campo_calculado"] == campo
    assert dados["valores"][campo]["texto"] == texto
    assert dados["valores"][campo]["marca"] == "CALCULADO"
    assert dados["valores"][campo]["entrada"]
    assert dados["valores"][campo]["rotulo"]


def test_previa_com_string_vazia_e_null_sao_desconhecido(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, _ = _cliente(monkeypatch)
    dados = cliente.post(_PREVIA, json=_corpo(prazo="")).json()
    assert dados["campo_calculado"] == "PRAZO"


@pytest.mark.parametrize(
    ("campos", "estado"),
    [
        ({"prazo": None, "taxa": None}, "PENDENTE"),
        ({k: None for k in ("saldo", "parcela", "taxa", "prazo")}, "SEM_CALCULO"),
    ],
)
def test_previa_sem_dados_suficientes_nao_calcula(
    monkeypatch: pytest.MonkeyPatch, campos: dict[str, object], estado: str
) -> None:
    cliente, _ = _cliente(monkeypatch)
    dados = cliente.post(_PREVIA, json=_corpo(**campos)).json()
    assert dados["estado"] == estado
    assert dados["campo_calculado"] is None and dados["resumo"] is None


def test_ac543_ac545_previa_traz_a_parcela_estimada_a_parte_e_marcada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Saldo e taxa, sem parcela e sem prazo: 24 meses em linha própria, nunca em `valores`."""
    cliente, _ = _cliente(monkeypatch)
    dados = cliente.post(_PREVIA, json=_corpo(parcela=None, prazo=None)).json()
    assert dados["estado"] == "PENDENTE"
    estimada = dados["parcela_estimada"]
    assert (estimada["texto"], estimada["marca"]) == ("R$ 528,72", "ESTIMADO")
    assert "24 meses" in estimada["hipotese"]
    assert "PARCELA" not in dados["valores"]  # nunca no campo digitado
    assert dados["resumo"] is None


@pytest.mark.parametrize("campos", [{"prazo": "36"}, {"parcela": "600,00"}])
def test_ac544_rf536_com_prazo_ou_pagamento_informado_nao_estima_nem_cita_24_meses(
    monkeypatch: pytest.MonkeyPatch, campos: dict[str, object]
) -> None:
    cliente, _ = _cliente(monkeypatch)
    corpo = _corpo(**{"parcela": None, "prazo": None, **campos})
    dados = cliente.post(_PREVIA, json=corpo).json()
    assert dados["parcela_estimada"] is None
    assert "24 meses" not in str(dados["mensagem"])


@pytest.mark.parametrize("parcela", ["200,00", "150,00"])
def test_ac528_parcela_que_nao_reduz_o_saldo_mostra_a_frase_e_apaga_o_resultado(
    monkeypatch: pytest.MonkeyPatch, parcela: str
) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    # AC-529: primeiro um sucesso (prazo 24), depois o erro — nada do 24 antigo.
    assert cliente.post(_PREVIA, json=_corpo(prazo=None)).json()["valores"]["PRAZO"]
    dados = cliente.post(_PREVIA, json=_corpo(prazo=None, parcela=parcela)).json()
    assert dados["estado"] == "ERRO"
    assert dados["valores"] == {}
    assert dados["resumo"] is None
    assert dados["mensagem"] == _FRASE_RF519
    assert repositorio.respostas == []


def test_ac525_taxa_sem_solucao_responde_a_mesma_frase(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, _ = _cliente(monkeypatch)
    dados = cliente.post(_PREVIA, json=_corpo(taxa=None, parcela="10.100,00", prazo="12")).json()
    assert dados["estado"] == "ERRO" and dados["valores"] == {}
    assert dados["mensagem"] == _FRASE_RF519


@pytest.mark.parametrize(
    ("campos", "campo", "codigo"),
    [
        ({"saldo": "abc"}, "SALDO", "VALOR_ILEGIVEL"),
        ({"saldo": "0"}, "SALDO", "SALDO_NAO_POSITIVO"),
        ({"parcela": "-5,00"}, "PARCELA", "PARCELA_NAO_POSITIVA"),
        ({"taxa": "-1"}, "TAXA", "TAXA_NEGATIVA"),
        ({"prazo": "2,5"}, "PRAZO", "PRAZO_NAO_INTEIRO"),
        ({"prazo": "481"}, "PRAZO", "PRAZO_ACIMA_DO_MAXIMO"),
    ],
)
def test_ac527_entrada_invalida_e_erro_de_negocio_com_200(
    monkeypatch: pytest.MonkeyPatch, campos: dict[str, object], campo: str, codigo: str
) -> None:
    cliente, _ = _cliente(monkeypatch)
    resposta = cliente.post(_PREVIA, json=_corpo(**campos))
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["estado"] == "ERRO" and dados["valores"] == {}
    assert dados["erros"][0]["campo"] == campo
    assert dados["erros"][0]["codigo"] == codigo
    assert dados["erros"][0]["mensagem"]


def test_ac541_formato_brasileiro_na_entrada_e_na_saida(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, _ = _cliente(monkeypatch)
    entrada = _corpo(saldo="1.234,50", parcela=None, taxa="0", prazo="10")
    assert cliente.post(_PREVIA, json=entrada).json()["valores"]["PARCELA"]["texto"] == "R$ 123,45"
    grande = _corpo(saldo="1.234.567,89", parcela=None, taxa="0", prazo="1")
    valor = cliente.post(_PREVIA, json=grande).json()["valores"]["PARCELA"]
    assert valor["texto"] == "R$ 1.234.567,89"
    assert valor["entrada"] == "1.234.567,89"


@pytest.mark.parametrize(
    "corpo",
    [
        b"isto nao e json",
        b'["lista"]',
        b'{"sistema": "PRICE"}',
        b'{"sistema": "OUTRO", "periodicidade": "MENSAL"}',
        b'{"sistema": "PRICE", "periodicidade": "MENSAL", "saldo": 10000}',
        b'{"sistema": "PRICE", "periodicidade": "MENSAL", "extra": "x"}',
    ],
)
def test_corpo_malformado_responde_400(monkeypatch: pytest.MonkeyPatch, corpo: bytes) -> None:
    cliente, _ = _cliente(monkeypatch)
    resposta = cliente.post(_PREVIA, content=corpo, headers={"content-type": "application/json"})
    assert resposta.status_code == 400


def test_previa_sem_sessao_responde_401(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, _ = _cliente(monkeypatch, com_sessao=False)
    assert cliente.post(_PREVIA, json=_corpo()).status_code == 401


def test_previa_de_caso_de_outro_aluno_nao_vaza_a_existencia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente, _ = _cliente(monkeypatch)
    resposta = cliente.post("/caso/CASO-DE-OUTRO/calculadora/previa", json=_corpo())
    assert resposta.status_code in {403, 404}


def test_ec77_falha_interna_responde_503(monkeypatch: pytest.MonkeyPatch) -> None:
    def quebra(corpo: object) -> object:
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(rotas_calculadora, "_avaliar", quebra)
    cliente, _ = _cliente(monkeypatch)
    resposta = cliente.post(_PREVIA, json=_corpo())
    assert resposta.status_code == 503
    assert resposta.json()["erro"]


def test_total_de_juros_e_cronograma_so_existem_na_rota_da_previa() -> None:
    donos = [
        arquivo.name
        for arquivo in (_RAIZ / "app" / "http").glob("*.py")
        if re.search(r"total_de_juros|\bcronograma\(", arquivo.read_text(encoding="utf-8"))
    ]
    assert donos == ["rotas_calculadora.py"]


# ---------------------------------------------------------------- T-505: eventos


@pytest.mark.parametrize(
    ("campos", "evento"),
    [
        ({"prazo": None, "parcela": "200,00"}, "CALCULADORA_NAO_REDUZ_SALDO"),
        ({"taxa": None, "parcela": "400,00"}, "CALCULADORA_SEM_CONVERGENCIA"),
        ({"taxa": None, "parcela": "10.100,00", "prazo": "12"}, "CALCULADORA_TETO_DE_TAXA"),
    ],
)
def test_cada_falha_emite_exatamente_o_seu_evento_sem_dado_do_aluno(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    campos: dict[str, object],
    evento: str,
) -> None:
    cliente, _ = _cliente(monkeypatch)
    with caplog.at_level(logging.DEBUG):
        dados = cliente.post(_PREVIA, json=_corpo(**campos)).json()
    assert dados["estado"] == "ERRO"
    emitidos = [r for r in caplog.records if getattr(r, "evento", None)]
    assert [r.__dict__["evento"] for r in emitidos] == [evento]
    for registro in (r for r in caplog.records if r.name == rotas_calculadora._LOGGER.name):
        texto = " ".join(str(v) for v in (registro.getMessage(), *registro.__dict__.values()))
        for dado in (
            *(str(v) for v in campos.values() if v and len(str(v)) > 3),
            "10.000",
            "10000",
            _CASO,
        ):
            assert dado not in texto


def test_erro_de_entrada_nao_emite_evento(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    cliente, _ = _cliente(monkeypatch)
    with caplog.at_level(logging.DEBUG):
        cliente.post(_PREVIA, json=_corpo(saldo="abc"))
    assert not [r for r in caplog.records if getattr(r, "evento", None)]


# -------------------------------------------------------------- T-504: confirmar


def _stored(repositorio: _Respostas) -> RespostasCaso:
    return RespostasCaso(respostas=tuple(repositorio.respostas))


def test_ac530_confirmar_grava_o_digitado_intacto_e_a_marca_por_ultimo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    resposta = cliente.post(_CONFIRMAR, json=_corpo(parcela="528,71"))
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert dados["ID_PERGUNTA"] == "B5.CALC01"
    assert "proxima" in dados and isinstance(dados["avisos"], list)
    assert "resumo" not in dados

    assert repositorio.valor(_V_PARCELA) == Decimal("528.71")  # nunca vira 528,72
    assert repositorio.valor(_V_SALDO) == Decimal("10000.00")
    assert repositorio.valor("TAXA_DIVIDA") == Decimal("0.02")
    assert repositorio.valor("PRAZO_RESTANTE_MESES") == 24
    assert repositorio.valor("PERIODICIDADE_TAXA_DIVIDA") == "MENSAL"
    assert repositorio.valor("SISTEMA_AMORTIZACAO") == "PRICE"
    assert repositorio.valor("INFORMACAO_A_RECALCULAR") == "NENHUMA"
    assert repositorio.valor("CONFERENCIA_DA_DIVIDA") == "CONFIRMADA"
    assert repositorio.chamadas[-1] == "CONFERENCIA_DA_DIVIDA"


def test_confirmar_duas_vezes_e_idempotente(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    cliente.post(_CONFIRMAR, json=_corpo(parcela="528,71"))
    primeira = {(r.ID_PERGUNTA, r.item_id): r.valor for r in repositorio.respostas}
    assert cliente.post(_CONFIRMAR, json=_corpo(parcela="528,71")).status_code == 200
    segunda = {(r.ID_PERGUNTA, r.item_id): r.valor for r in repositorio.respostas}
    assert primeira == segunda and len(repositorio.respostas) == 8


def test_ac537_desconhecido_grava_nao_sei_nunca_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    resposta = cliente.post(_CONFIRMAR, json=_corpo(taxa=None, prazo=""))
    assert resposta.status_code == 200, resposta.text
    assert repositorio.valor("TAXA_DIVIDA") is NAO_SEI
    assert repositorio.valor("PRAZO_RESTANTE_MESES") is NAO_SEI
    assert repositorio.valor("PERIODICIDADE_TAXA_DIVIDA") == "DESCONHECIDA"
    assert not [r for r in repositorio.respostas if r.valor == 0]
    # Dois desconhecidos: a dívida fica pendente, nada é inventado.
    premissas = resolver_divida(_stored(repositorio), _DIVIDA)
    assert premissas.situacao is SITUACAO_DA_DIVIDA.PENDENTE
    assert CAMPO_DA_DIVIDA.TAXA in premissas.faltas


def test_ac536_recalcular_grava_nao_sei_no_campo_e_a_escolha_com_impressao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    resposta = cliente.post(_CONFIRMAR, json=_corpo(parcela="400,00", recalcular="PARCELA"))
    assert resposta.status_code == 200, resposta.text
    assert repositorio.valor(_V_PARCELA) is NAO_SEI
    impressao = impressao_dos_valores(
        Decimal("10000.00"), NAO_SEI, Decimal("0.02"), 24, SISTEMA_AMORTIZACAO.PRICE, "MENSAL"
    )
    assert repositorio.valor("INFORMACAO_A_RECALCULAR") == f"PARCELA|{impressao}"
    premissas = resolver_divida(_stored(repositorio), _DIVIDA)
    assert premissas.situacao is SITUACAO_DA_DIVIDA.COMPLETA
    assert premissas.valores[CAMPO_DA_DIVIDA.PARCELA].valor == Decimal("528.72")


def test_confirmar_incompativel_sem_escolha_mantem_os_originais(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    assert cliente.post(_CONFIRMAR, json=_corpo(parcela="400,00")).status_code == 200
    assert repositorio.valor(_V_PARCELA) == Decimal("400.00")
    assert repositorio.valor("INFORMACAO_A_RECALCULAR") == "NENHUMA"
    premissas = resolver_divida(_stored(repositorio), _DIVIDA)
    assert premissas.situacao is SITUACAO_DA_DIVIDA.INCOMPATIVEL


@pytest.mark.parametrize(
    "campos",
    [{"saldo": "abc"}, {"parcela": "0"}, {"prazo": "481"}, {"parcela": "200,00", "prazo": None}],
)
def test_confirmar_com_entrada_invalida_ou_sem_resultado_responde_422_sem_gravar(
    monkeypatch: pytest.MonkeyPatch, campos: dict[str, object]
) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    resposta = cliente.post(_CONFIRMAR, json=_corpo(**campos))
    assert resposta.status_code == 422
    assert resposta.json()["erro"]
    assert repositorio.respostas == [] and repositorio.chamadas == []


def test_confirmar_em_conferencia_responde_409(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    _Casos.estado = ESTADO_CASO.AGUARDANDO_REVISAO
    assert cliente.post(_CONFIRMAR, json=_corpo()).status_code == 409
    assert repositorio.respostas == []


def test_confirmar_divida_inexistente_responde_404(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    resposta = cliente.post(f"/caso/{_CASO}/divida/D999/calculadora/confirmar", json=_corpo())
    assert resposta.status_code == 404
    assert repositorio.respostas == []


def test_confirmar_de_caso_alheio_ou_sem_sessao(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, _ = _cliente(monkeypatch)
    alheio = "/caso/CASO-DE-OUTRO/divida/D001/calculadora/confirmar"
    assert cliente.post(alheio, json=_corpo()).status_code in {403, 404}
    anonimo, _ = _cliente(monkeypatch, com_sessao=False)
    assert anonimo.post(_CONFIRMAR, json=_corpo()).status_code == 401


def test_confirmar_corpo_malformado_responde_400(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    resposta = cliente.post(_CONFIRMAR, content=b"{", headers={"content-type": "application/json"})
    assert resposta.status_code == 400 and repositorio.respostas == []


@pytest.mark.parametrize("falha_na", [0, 3, 6])
def test_falha_no_meio_responde_503_e_nao_deixa_a_marca(
    monkeypatch: pytest.MonkeyPatch, falha_na: int
) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    repositorio.falhar_na_chamada = falha_na
    resposta = cliente.post(_CONFIRMAR, json=_corpo())
    assert resposta.status_code == 503
    assert resposta.json()["erro"] == "Não foi possível salvar."
    assert "CONFERENCIA_DA_DIVIDA" not in repositorio.chamadas
    # Reenviar completa: a confirmação é idempotente.
    repositorio.falhar_na_chamada = None
    assert cliente.post(_CONFIRMAR, json=_corpo()).status_code == 200
    assert repositorio.valor("CONFERENCIA_DA_DIVIDA") == "CONFIRMADA"


def test_confirmar_parcela_maior_que_o_saldo_devolve_o_aviso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente, _ = _cliente(monkeypatch)
    corpo = _corpo(saldo="100,00", parcela="200,00", taxa=None, prazo=None)
    dados = cliente.post(_CONFIRMAR, json=corpo).json()
    assert [a["codigo"] for a in dados["avisos"]] == ["PARCELA_MAIOR_QUE_O_SALDO"]
    assert dados["avisos"][0]["ID_PERGUNTA"] == "B5.CALC01"


def test_ac545_confirmar_sem_parcela_nem_prazo_nao_grava_a_estimada_no_campo_digitado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`RF-533`/`AC-545`: a parcela estimada vive só na prévia; a ficha guarda o 'não sei'."""
    cliente, repositorio = _cliente(monkeypatch)
    resposta = cliente.post(_CONFIRMAR, json=_corpo(parcela=None, prazo=None))
    assert resposta.status_code == 200, resposta.text
    assert repositorio.valor(_V_PARCELA) is NAO_SEI
    assert repositorio.valor("PRAZO_RESTANTE_MESES") is NAO_SEI
    assert Decimal("528.72") not in [r.valor for r in repositorio.respostas]
