"""`T-446` a `T-449` — o relatório só pede o que o aluno pode informar, e o plano
provisório não se diz definitivo.

Spec: `specs/pendencias-do-relatorio.spec.md`. O snapshot vem do motor REAL
(`calcular_plano`); só o que a apresentação lê é ajustado, com `replace`.

REGRAS: `RF-461`, `RF-462`, `RF-463`, `RF-464`, `RF-465`, `RF-466`, `RF-467`
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any

from app.http.serializacao_plano import maiores_gastos
from app.montagem.conversao import converter_para_dinheiro
from collection.carga import carregar_registros
from collection.registro import EscopoRepeticao
from collection.respostas import RespostasCaso
from engine.motor import calcular_plano
from engine.snapshot import SnapshotOrdem
from engine.tipos import DESCONHECIDO, ORDEM_STATUS
from persistencia.app_aluno.itens import ItemRepetido
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from report.pdf import renderizar_html_do_plano
from report.plano import (
    _CAMPOS_MATERIAIS_DA_DIVIDA,
    ContextoPlano,
    VocabularioDoCaso,
    carregar_textos_canonicos,
    montar_contexto_plano,
)
from tests.app_aluno.fixtures.caso_completo import _resposta_item
from tests.app_aluno.test_plano_ec07_ec08_ec09 import _VERSAO_PARAMETROS_REAL, _estado_gab04

_SECAO_DE_PENDENCIAS = "O que falta informar"


def _snapshot_base() -> SnapshotOrdem:
    return calcular_plano(
        _estado_gab04(), FonteParametrosArquivo().carregar(_VERSAO_PARAMETROS_REAL)
    )


def _snapshot_provisorio(**campos_da_divida: Any) -> SnapshotOrdem:
    """O plano do motor, marcado `PROVISORIA`, com os campos pedidos da PRIMEIRA
    dívida trocados (o resto do `estado_inputs` fica como o motor o leu)."""
    base = _snapshot_base()
    primeira, *demais = base.estado_inputs.dividas
    estado = replace(base.estado_inputs, dividas=(replace(primeira, **campos_da_divida), *demais))
    return replace(base, ORDEM_STATUS=ORDEM_STATUS.PROVISORIA, estado_inputs=estado)


def _contexto(
    snapshot: SnapshotOrdem, vocabulario: VocabularioDoCaso | None = None
) -> tuple[ContextoPlano, str]:
    textos = carregar_textos_canonicos()
    contexto = montar_contexto_plano(snapshot, textos, vocabulario)
    return contexto, renderizar_html_do_plano(contexto, textos)


# ---------------------------------------------------------------- RF-461


def test_rf461_quitacao_hoje_desconhecida_nao_e_pendencia() -> None:
    """O questionário não pergunta o valor de quitação (`T-408`); o motor usa o saldo."""
    assert "VALOR_QUITACAO_HOJE" not in _CAMPOS_MATERIAIS_DA_DIVIDA
    contexto, html = _contexto(_snapshot_provisorio(VALOR_QUITACAO_HOJE=DESCONHECIDO))

    assert contexto.pendencias is None
    assert contexto.pendencias_acionaveis == ()
    assert _SECAO_DE_PENDENCIAS not in html
    assert "quitar hoje" not in html


# ---------------------------------------------------------------- RF-462


def test_rf462_parcela_ausente_de_divida_sem_parcela_definida_nao_e_pendencia() -> None:
    snapshot = _snapshot_provisorio(PARCELA_CONTRATUAL=DESCONHECIDO)
    id_da_divida = snapshot.estado_inputs.dividas[0].DIVIDA_ID

    # Controle: sem a resposta "não há parcela definida", a falta continua sendo falta.
    com_pendencia, _ = _contexto(snapshot)
    assert com_pendencia.pendencias is not None
    assert [campos for _i, _n, campos in com_pendencia.pendencias.campos_faltantes_por_divida] == [
        ("o valor da parcela do contrato",)
    ]

    vocabulario = VocabularioDoCaso(dividas_sem_parcela_definida=frozenset({id_da_divida}))
    contexto, html = _contexto(snapshot, vocabulario)

    assert contexto.pendencias is None
    assert contexto.pendencias_acionaveis == ()
    assert _SECAO_DE_PENDENCIAS not in html


# ---------------------------------------------------------------- RF-463


def test_rf463_pendencia_real_continua_aparecendo() -> None:
    contexto, html = _contexto(_snapshot_provisorio(SALDO_DEVEDOR_ATUAL=DESCONHECIDO))

    assert contexto.pendencias is not None
    assert contexto.pendencias_acionaveis[0].id_pergunta == "B5.B03"
    assert _SECAO_DE_PENDENCIAS in html
    assert "Este plano ainda é provisório." in html


def test_rf463_inventario_incompleto_continua_sendo_pendencia() -> None:
    base = _snapshot_provisorio()
    snapshot = replace(base, estado_inputs=replace(base.estado_inputs, INVENTARIO_COMPLETO=False))

    contexto, html = _contexto(snapshot)

    assert contexto.pendencias is not None and contexto.pendencias.inventario_incompleto
    assert "ainda não foi confirmado como completo" in html


# ---------------------------------------------------------------- RF-464


def test_rf464_toda_pergunta_do_campo_existe_no_questionario() -> None:
    textos = carregar_textos_canonicos()
    ids = {registro.ID for registro in carregar_registros().registros}

    assert set(textos.pergunta_do_campo) <= set(_CAMPOS_MATERIAIS_DA_DIVIDA)
    for campo, pergunta in textos.pergunta_do_campo.items():
        assert pergunta in ids, f"{campo} aponta para {pergunta}, que não existe"


# ---------------------------------------------------------------- RF-465


def test_rf465_plano_provisorio_nao_se_diz_definitivo() -> None:
    contexto, html = _contexto(_snapshot_provisorio())

    assert contexto.provisorio is True
    assert "provisório" in contexto.corpo
    assert "definitivo" not in html.lower()
    resposta = dict(contexto.duvidas)["Quando o meu plano muda?"]
    assert "provisório" in resposta


def test_rf465_plano_definitivo_continua_se_dizendo_definitivo() -> None:
    definitivo = replace(_snapshot_base(), ORDEM_STATUS=ORDEM_STATUS.DEFINITIVA_NA_DATA)
    # Sem estabilização: o plano normal do motor.
    base = replace(
        definitivo,
        diagnostico=replace(definitivo.diagnostico, MODO_ESTABILIZACAO=False),
    )
    contexto, html = _contexto(base)

    assert contexto.provisorio is False
    assert "Este plano é definitivo" in html


# ---------------------------------------------------------------- RF-466


def test_rf466_rotulo_da_linha_de_resultado_antes_das_parcelas() -> None:
    textos = carregar_textos_canonicos()

    rotulo = textos.ponto_de_partida["despesas_mensais_totais"]
    assert rotulo == "Resultado do mês antes das parcelas de dívida (renda − despesas)"


# ---------------------------------------------------------------- RF-467


def test_rf467_saldo_devedor_e_parcela_continuam_exigidos_antes_do_envio() -> None:
    """`B5.B03` (saldo) e `B5.C02` (parcela, quando a dívida tem parcela definida)
    são `indispensavel` e não aceitam "não sei": o envio os cobra."""
    registros = {registro.ID: registro for registro in carregar_registros().registros}

    saldo = registros["B5.B03"]
    assert saldo.indispensavel is True and saldo.admite_nao_sei is False
    assert "REP" in {o.name for o in saldo.obrigatoriedade}

    parcela = registros["B5.C02"]
    assert parcela.indispensavel is True and parcela.admite_nao_sei is False
    assert "COND" in {o.name for o in parcela.obrigatoriedade}

    assert "B5.B05A" not in registros  # a pergunta do valor de quitação não existe mais


# -------------------------------------------------- aluno deficitário (RF-468 a RF-470)


def test_rf468_deficitario_ve_o_resultado_em_destaque_e_o_valor_para_zerar() -> None:
    contexto, html = _contexto(_snapshot_base())

    assert contexto.MODO_ESTABILIZACAO is True
    assert "Primeiro, estancar o problema" in html
    assert "Seu mês fecha em" in html
    assert html.count("R$ -1.000,00") >= 2
    assert "faltam cortar por mês" in html
    assert 'estatistica-valor">R$ 1.000,00<' in html
    assert "provisório" in html


def test_rf469_deficitario_ve_os_maiores_gastos_sem_meta_inventada() -> None:
    gastos = (("Aluguel", Decimal("2500")), ("Mercado", Decimal("1800")))
    _contexto_, html = _contexto(_snapshot_base(), VocabularioDoCaso(maiores_gastos=gastos))

    assert "Onde olhar nos seus gastos" in html
    assert html.index("Aluguel") < html.index("Mercado")
    assert "R$ 2.500,00" in html and "R$ 1.800,00" in html
    assert "%" not in html[html.index("Onde olhar nos seus gastos") :][:900]


def test_rf469_plano_normal_nao_mostra_o_bloco_dos_gastos() -> None:
    normal = replace(
        _snapshot_base(),
        diagnostico=replace(_snapshot_base().diagnostico, MODO_ESTABILIZACAO=False),
    )
    _contexto_, html = _contexto(
        normal, VocabularioDoCaso(maiores_gastos=(("Aluguel", Decimal("1")),))
    )

    assert "Onde olhar nos seus gastos" not in html
    assert "Primeiro, estancar o problema" not in html


def test_rf469_maiores_gastos_sao_os_cinco_maiores_com_nome() -> None:
    registros = carregar_registros().registros
    valores = {
        "ALUGUEL": "2.500,00",
        "AGUA": "300,00",
        "ENERGIA": "450,00",
        "GAS": "90,00",
        "INTERNET": "120,00",
        "CONDOMINIO": "800,00",
    }
    itens = tuple(
        ItemRepetido(
            item_id=f"DESP{i:03d}",
            CASO_ID="C1",
            escopo=EscopoRepeticao.ITEM_DESPESA,
            removido_em=None,
            criado_em=date(2026, 10, 1),  # type: ignore[arg-type]
            origem=f"B3.D01:{opcao}",
        )
        for i, opcao in enumerate(valores, start=1)
    )
    respostas = RespostasCaso(
        respostas=tuple(
            _resposta_item(
                ID_PERGUNTA="VALOR_DESPESA",
                item_id=item.item_id,
                valor=converter_para_dinheiro(valor),
            )
            for item, valor in zip(itens, valores.values(), strict=True)
        )
    )

    resultado = maiores_gastos(registros, respostas, itens)

    assert [nome for nome, _ in resultado] == [
        "Aluguel",
        "Condomínio",
        "Energia",
        "Água",
        "Internet",
    ]
    assert resultado[0][1] == Decimal("2500.00")
    assert len(resultado) == 5  # o gás, o menor, fica de fora


def test_rf470_quadro_de_aulas_do_deficitario() -> None:
    contexto, _html = _contexto(_snapshot_base())

    assert contexto.curso_ssd is not None
    assert [numero for numero, _titulo, _motivo in contexto.curso_ssd.aulas] == ["5", "14", "24"]


def test_rf471_deficitario_ve_que_a_ordem_provisoria_nao_e_instrucao_de_pagamento() -> None:
    """RF-471: aviso presente com ou sem ordem; o plano normal não o mostra."""
    _contexto_, html = _contexto(_snapshot_base())

    assert "Isto ainda não é uma instrução de pagamento" in html
    assert "Não antecipe pagamentos" in html
    assert "parcelas contratuais" in html

    normal = replace(
        _snapshot_base(),
        diagnostico=replace(_snapshot_base().diagnostico, MODO_ESTABILIZACAO=False),
    )
    _c, html_normal = _contexto(normal)
    assert "Isto ainda não é uma instrução de pagamento" not in html_normal
