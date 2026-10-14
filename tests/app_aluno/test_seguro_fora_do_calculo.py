"""O seguro da dívida não entra no cálculo nem no plano — `RF-410` (`T-391`).

Decisão do produto (2026-10-14): as 7 perguntas `B5.D05*` saíram do
questionário. `EstadoFinanceiro` e `SnapshotOrdem` são idênticos com e sem
respostas do seguro (a montagem entrega `SEGURO_INCLUIDO_PARCELA = False` e
`CUSTO_SEGURO = DESCONHECIDO` fixos), e o plano — tela, revisor e PDF — não
menciona seguro nem o pede como informação pendente.

REGRAS: `RF-410`
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.montagem.conversao import converter_para_dinheiro
from app.montagem.estado import montar_divida, montar_estado_financeiro
from collection.carga import carregar_registros
from collection.respostas import Resposta, RespostasCaso
from engine.estado import EstadoFinanceiro
from engine.motor import calcular_plano
from engine.snapshot import SnapshotOrdem
from engine.tipos import DESCONHECIDO
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from report.pdf import renderizar_html_do_plano
from report.plano import (
    VocabularioDoCaso,
    carregar_textos_canonicos,
    montar_contexto_estado_inputs,
    montar_contexto_plano,
)
from tests.app_aluno.fixtures.caso_completo import DATA_REFERENCIA, caso_completo

_VERSAO_PARAMETROS_REAL = "1.0.1"
# As variáveis que as perguntas removidas gravavam (ver `bloco-05.yaml` no
# histórico do `git`): nenhuma delas pode mexer em nada.
_RESPOSTAS_DO_SEGURO: tuple[tuple[str, object], ...] = (
    ("SEGURO_PRESTAMISTA", "SIM"),
    ("CUSTO_SEGURO (+ base MENSAL/TOTAL)", "MENSAL"),
    ("SEGURO_INCLUIDO_PARCELA", "NAO"),
    ("SITUACAO_SEGURO", "COBRADO_MENSAL_A_PARTE"),
    ("CUSTO_SEGURO_VALOR", converter_para_dinheiro("100,00")),
    ("CUSTO_SEGURO_MESES", 12),
    ("RESTITUICAO_SEGURO_CONFIRMADA", converter_para_dinheiro("300,00")),
)


def _com_seguro(respostas: RespostasCaso, DIVIDA_ID: str) -> RespostasCaso:
    seguro = tuple(
        Resposta(
            CASO_ID=respostas.respostas[0].CASO_ID,
            ID_PERGUNTA=variavel,
            item_id=DIVIDA_ID,
            valor=valor,  # type: ignore[arg-type]
            QUESTIONARIO_VERSION=respostas.respostas[0].QUESTIONARIO_VERSION,
            respondida_em=datetime(2026, 1, 1, tzinfo=UTC),
        )
        for variavel, valor in _RESPOSTAS_DO_SEGURO
    )
    return RespostasCaso(respostas=respostas.respostas + seguro)


def _estado(respostas: RespostasCaso, DIVIDA_ID: str) -> EstadoFinanceiro:
    caso = caso_completo()
    return montar_estado_financeiro(
        respostas,
        DATA_REFERENCIA=DATA_REFERENCIA,
        dividas=(montar_divida(respostas, DIVIDA_ID),),
        **caso.parametros_externos,  # type: ignore[arg-type]
    )


def _snapshot(estado: EstadoFinanceiro) -> SnapshotOrdem:
    return calcular_plano(estado, FonteParametrosArquivo().carregar(_VERSAO_PARAMETROS_REAL))


def test_nenhuma_pergunta_do_seguro_resta_no_questionario() -> None:
    ids = {r.ID for r in carregar_registros().registros}
    assert not {i for i in ids if i.startswith("B5.D05")}
    variaveis = {r.VARIAVEL_GRAVADA for r in carregar_registros().registros}
    assert not {v for v in variaveis if v and "SEGURO" in v and not v.startswith("ITENS_")}


def test_divida_montada_entrega_o_seguro_neutro_com_ou_sem_respostas() -> None:
    caso = caso_completo()
    sem = montar_divida(caso.respostas, caso.DIVIDA_ID)
    com = montar_divida(_com_seguro(caso.respostas, caso.DIVIDA_ID), caso.DIVIDA_ID)

    assert com == sem
    assert sem.SEGURO_INCLUIDO_PARCELA is False
    assert sem.CUSTO_SEGURO is DESCONHECIDO


def test_estado_e_snapshot_sao_identicos_com_e_sem_as_respostas_do_seguro() -> None:
    caso = caso_completo()
    sem = _estado(caso.respostas, caso.DIVIDA_ID)
    com = _estado(_com_seguro(caso.respostas, caso.DIVIDA_ID), caso.DIVIDA_ID)

    assert com == sem
    assert com.DESPESAS_OPERACIONAIS_ATUAIS == sem.DESPESAS_OPERACIONAIS_ATUAIS
    snapshot_sem, snapshot_com = _snapshot(sem), _snapshot(com)
    assert snapshot_com == snapshot_sem
    assert snapshot_com.ORDEM_STATUS is snapshot_sem.ORDEM_STATUS
    assert snapshot_com.hash_inputs == snapshot_sem.hash_inputs


def test_plano_nao_menciona_seguro_nem_o_pede_como_pendencia() -> None:
    caso = caso_completo()
    textos = carregar_textos_canonicos()
    snapshot = _snapshot(_estado(caso.respostas, caso.DIVIDA_ID))
    contexto = montar_contexto_plano(snapshot, textos)
    contexto_com = montar_contexto_plano(
        _snapshot(_estado(_com_seguro(caso.respostas, caso.DIVIDA_ID), caso.DIVIDA_ID)), textos
    )

    # O caso é PROVISORIA: a lista de pendências é de fato exercitada.
    assert contexto.pendencias is not None
    # As pendências (e o ORDEM_STATUS que as dispara) não mudam com o seguro.
    assert contexto_com.pendencias == contexto.pendencias
    assert contexto_com.pendencias_acionaveis == contexto.pendencias_acionaveis
    campos_pedidos = [
        campo
        for pendencia in (
            contexto.pendencias.campos_faltantes_por_divida if contexto.pendencias else ()
        )
        for campo in pendencia[2]
    ]
    assert not [c for c in campos_pedidos if "seguro" in c.lower()]
    assert not [p for p in contexto.pendencias_acionaveis if "seguro" in p.rotulo.lower()]
    assert not [p for p in contexto.pendencias_acionaveis if p.id_pergunta == "B5.D05A"]

    # Tela do aluno e PDF (mesmo template) e conferência do revisor.
    html = renderizar_html_do_plano(contexto, textos)
    assert "seguro" not in html.lower()
    revisor = montar_contexto_estado_inputs(snapshot.estado_inputs, textos, VocabularioDoCaso())
    codigos = {c.codigo for d in revisor.dividas for c in d.campos}
    assert not {"CUSTO_SEGURO", "SEGURO_INCLUIDO_PARCELA"} & codigos
