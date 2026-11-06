"""Registro da calculadora da dívida e "não sei" pela API de coleta — `RF-514`,
`RF-523`, `RF-526`, `AC-533`, `AC-537` (`T-491` a `T-497`).

Aplicação real, registros REAIS, repositórios em memória por
`app.dependency_overrides` (mesmo padrão de `test_rotas_coleta_fotografia.py`).

REGRAS: RF-514, RF-523, RF-526
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from functools import cache

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.casos.maquina import ESTADO_CASO, Caso
from app.casos.progresso import pendencias_obrigatorias
from app.http.aplicacao import criar_aplicacao
from app.http.isolamento import obter_repositorio_casos
from app.http.rotas_coleta import (
    obter_colecao_de_registros,
    obter_repositorio_itens,
    obter_repositorio_respostas,
)
from app.http.sessao import iniciar_sessao_conta
from app.revisao.comprovacao import pendencias_de_homologacao
from collection.carga import ColecaoDeRegistros, carregar_registros
from collection.condicoes import avaliar
from collection.registro import EscopoRepeticao, Obrigatoriedade, TipoResposta
from collection.respostas import NAO_SEI, Resposta, RespostasCaso
from persistencia.app_aluno.itens import ItemRepetido

_CHAVE_TESTE = "chave-de-teste-para-assinatura-de-sessao-nao-usar-em-producao"
_CONTA = "CONTA-CALC-1"
_CASO = "CASO-CALC-1"
_DIVIDA = "D001"
_AGORA = datetime(2026, 11, 4, tzinfo=UTC)
_VERSAO = "1.5.0"


class _Respostas:
    def __init__(self) -> None:
        self.respostas: list[Resposta] = []

    def gravar(self, resposta: Resposta) -> None:
        self.respostas = [
            r
            for r in self.respostas
            if not (r.ID_PERGUNTA == resposta.ID_PERGUNTA and r.item_id == resposta.item_id)
        ] + [resposta]

    def listar_do_caso(self, caso_id: str) -> tuple[Resposta, ...]:
        return tuple(self.respostas)


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
    def __init__(self) -> None:
        self.caso = Caso(
            CASO_ID=_CASO,
            conta_id=_CONTA,
            estado=ESTADO_CASO.COLETA_INICIAL,
            DATA_REFERENCIA=date(2026, 11, 4),
            QUESTIONARIO_VERSION=_VERSAO,
            snapshot_raiz_id=None,
            snapshot_liberado_id=None,
            ultima_interacao_em=_AGORA,
            criado_em=_AGORA,
        )

    def buscar(self, caso_id: str) -> Caso | None:
        return self.caso if caso_id == _CASO else None

    def pertence_a_conta(self, caso_id: str, conta_id: str) -> bool:
        return caso_id == _CASO and conta_id == _CONTA


@cache
def _colecao() -> ColecaoDeRegistros:
    return carregar_registros()


def _registro(ID: str):  # type: ignore[no-untyped-def]
    return next(r for r in _colecao().registros if r.ID == ID)


def _cliente(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, _Respostas]:
    monkeypatch.setenv("CHAVE_ASSINATURA_SESSAO", _CHAVE_TESTE)
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
    cliente.post(f"/_teste/abrir-sessao/{_CONTA}")
    return cliente, respostas


def _resposta(variavel: str, valor: object) -> Resposta:
    return Resposta(
        CASO_ID=_CASO,
        ID_PERGUNTA=variavel,
        item_id=_DIVIDA,
        valor=valor,  # type: ignore[arg-type]
        QUESTIONARIO_VERSION=_VERSAO,
        respondida_em=_AGORA,
    )


# ------------------------------------------------------------ T-491 / T-492


def test_versao_unica_1_5_0() -> None:
    assert _colecao().QUESTIONARIO_VERSION == "1.5.0"


def test_calc01_e_c02b_na_ficha_da_divida_na_ordem_do_plano() -> None:
    ids = [r.ID for r in _colecao().registros]
    assert ids.index("B5.CALC01") == ids.index("B5.A02") + 1
    assert ids.index("B5.C02B") == ids.index("B5.C02") + 1

    calc = _registro("B5.CALC01")
    assert calc.tipo is TipoResposta.CALCULO_DIVIDA
    assert calc.escopo_repeticao is EscopoRepeticao.DIVIDA_ID
    assert calc.obrigatoriedade == frozenset({Obrigatoriedade.OPT, Obrigatoriedade.REP})
    assert calc.VARIAVEL_GRAVADA == "CONFERENCIA_DA_DIVIDA"

    prazo = _registro("B5.C02B")
    assert prazo.VARIAVEL_GRAVADA == "PRAZO_RESTANTE_MESES"
    assert prazo.obrigatoriedade == frozenset({Obrigatoriedade.OPT, Obrigatoriedade.REP})
    assert prazo.admite_nao_sei is True


def test_historico_c03_a_c07a_sem_reaproveitamento() -> None:
    ids = {r.ID for r in _colecao().registros}
    assert not {i for i in ids if i.startswith(("B5.C03", "B5.C04", "B5.C05", "B5.C06", "B5.C07"))}


# ------------------------------------------------------------------- T-493


@pytest.mark.parametrize("tipo", ["CARTAO_ROTATIVO", "PESSOAL", "CONSIGNADO"])
def test_ac533_c02a_presente_em_toda_modalidade(tipo: str) -> None:
    """`AC-533`: sem `condicao_exibicao`, aberta em qualquer tipo de dívida."""
    c02a = _registro("B5.C02A")
    respostas = RespostasCaso(respostas=(_resposta("TIPO_DIVIDA", tipo),))
    assert c02a.condicao_exibicao is None
    assert c02a.indispensavel is False
    assert c02a.condicao_exibicao is None or avaliar(c02a.condicao_exibicao, respostas, _DIVIDA)


def test_ac533_texto_de_c02a_nao_diz_financiamento_nem_do_credor() -> None:
    enunciado = _registro("B5.C02A").enunciado.lower()
    assert "financiamento" not in enunciado
    assert "credor" not in enunciado


def test_ac533_a_pergunta_composta_nasce_com_price(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, _ = _cliente(monkeypatch)
    pergunta = cliente.get(f"/caso/{_CASO}/pergunta/B5.CALC01?item_id={_DIVIDA}").json()["pergunta"]
    assert pergunta["tipo"] == "CALCULO_DIVIDA"
    assert pergunta["sistema"] == "PRICE"
    assert pergunta["enunciado"] and pergunta["apoio"]


def test_ac533_sac_escolhido_continua_sac_ao_reabrir(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente, _ = _cliente(monkeypatch)
    gravada = cliente.post(
        f"/caso/{_CASO}/resposta",
        data={"ID_PERGUNTA": "B5.C02A", "item_id": _DIVIDA, "valor": "SAC"},
    )
    assert gravada.status_code == 200, gravada.text

    reaberta = cliente.get(f"/caso/{_CASO}/pergunta/B5.C02A?item_id={_DIVIDA}").json()["pergunta"]
    assert reaberta["valor_atual"] == "SAC"


# ------------------------------------------------------------------- T-496


def test_post_resposta_para_calculo_divida_e_recusado_sem_gravar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    resposta = cliente.post(
        f"/caso/{_CASO}/resposta",
        data={"ID_PERGUNTA": "B5.CALC01", "item_id": _DIVIDA, "valor": "CONFIRMADA"},
    )
    assert resposta.status_code == 422
    assert repositorio.respostas == []


def test_pergunta_ja_respondida_pela_composta_e_pulada() -> None:
    """A composta grava as mesmas variáveis; "não sei" conta como resposta."""
    from app.casos.progresso import proxima_pergunta_nao_respondida

    gravadas = tuple(
        _resposta(v, NAO_SEI)
        for v in (
            "TIPO_DIVIDA",
            "CONFERENCIA_DA_DIVIDA",
            "SALDO_DEVEDOR_ATUAL",
            "PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)",
            "PRAZO_RESTANTE_MESES",
            "SISTEMA_AMORTIZACAO",
        )
    )
    pendente = proxima_pergunta_nao_respondida(
        _colecao().registros,
        RespostasCaso(respostas=gravadas),
        {EscopoRepeticao.DIVIDA_ID: (_DIVIDA,)},
    )
    assert pendente is None or pendente.ID not in {
        "B5.CALC01",
        "B5.B03",
        "B5.C02",
        "B5.C02B",
        "B5.C02A",
    }


# ------------------------------------------------------------------- T-497


@pytest.mark.parametrize("pergunta", ["B5.B03", "B5.C02", "B5.C02B"])
def test_ac537_nao_sei_em_saldo_parcela_e_prazo_grava_nao_sei_nunca_zero(
    monkeypatch: pytest.MonkeyPatch, pergunta: str
) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    resposta = cliente.post(
        f"/caso/{_CASO}/resposta",
        data={"ID_PERGUNTA": pergunta, "item_id": _DIVIDA, "nao_sei": "1"},
    )
    assert resposta.status_code == 200, resposta.text

    variavel = _registro(pergunta).VARIAVEL_GRAVADA
    (gravada,) = [r for r in repositorio.respostas if r.ID_PERGUNTA == variavel]
    assert gravada.valor is NAO_SEI
    assert not [r for r in repositorio.respostas if r.valor == 0]


def test_ac537_nao_sei_a_taxa_e_a_opcao_do_registro() -> None:
    (opcao,) = [o for o in _registro("B5.D06").opcoes if o.valor_interno == "DESCONHECIDA"]
    assert opcao.admite_nao_sei is True and opcao.abre_campo is None


def test_ac537_nao_sei_no_saldo_nao_bloqueia_o_avanco_e_vira_pendencia_de_envio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente, repositorio = _cliente(monkeypatch)
    cliente.post(
        f"/caso/{_CASO}/resposta",
        data={"ID_PERGUNTA": "B5.B03", "item_id": _DIVIDA, "nao_sei": "1"},
    )
    respostas = RespostasCaso(respostas=tuple(repositorio.respostas))
    itens = {EscopoRepeticao.DIVIDA_ID: (_DIVIDA,)}

    # O saldo respondido como "não sei" deixa de bloquear o avanço (`RF-11`).
    bloqueios = {p.ID for p in pendencias_obrigatorias(_colecao().registros, respostas, itens)}
    assert "B5.B03" not in bloqueios
    pendencias = pendencias_de_homologacao(_colecao().registros, respostas, itens)
    assert (_DIVIDA, "B5.B03") in {(p.item_id, p.ID_PERGUNTA) for p in pendencias}


# ------------------------------------------------------------------- T-525


def test_ac545_c02c_pergunta_o_minimo_ao_lado_do_habitual_em_toda_divida() -> None:
    """`RF-533`, `AC-545`: `B5.C02C` em toda dívida, `OPT` (caso antigo não trava)."""
    ids = [r.ID for r in _colecao().registros]
    assert ids.index("B5.C02C") == ids.index("B5.C02B") + 1
    minimo = _registro("B5.C02C")
    assert minimo.tipo is TipoResposta.MOEDA
    assert minimo.escopo_repeticao is EscopoRepeticao.DIVIDA_ID
    assert minimo.obrigatoriedade == frozenset({Obrigatoriedade.OPT, Obrigatoriedade.REP})
    assert minimo.VARIAVEL_GRAVADA == "PAGAMENTO_MINIMO_DIVIDA"
    assert minimo.condicao_exibicao is None
    assert minimo.admite_nao_sei is True
    # o habitual segue sendo a parcela de `B5.C02` (`OQ-85`)
    assert _registro("B5.C02").escopo_repeticao is EscopoRepeticao.DIVIDA_ID


def test_ac545_nenhum_arquivo_do_questionario_fica_na_versao_anterior() -> None:
    """`T-525`: a mesma `QUESTIONARIO_VERSION` em todos os arquivos que a declaram (`PD-13`)."""
    from pathlib import Path

    import yaml

    pasta = Path(__file__).resolve().parents[2] / "collection" / "registros"
    versoes = {
        arquivo.name: yaml.safe_load(arquivo.read_text(encoding="utf-8")).get(
            "QUESTIONARIO_VERSION"
        )
        for arquivo in pasta.glob("*.yaml")
    }
    declaradas = {nome: v for nome, v in versoes.items() if v is not None}
    assert declaradas, "nenhum arquivo declara a versão"
    assert set(declaradas.values()) == {_VERSAO}, declaradas
