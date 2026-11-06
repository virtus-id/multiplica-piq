"""Regressões dos achados da revisão de `calculo-de-divida` (sem rastro de AC próprio).

REGRAS: `RF-514`, `RF-515`, `RF-518`, `RF-527`, `RF-538`, `OQ-84`, `OQ-95`
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.http.rotas_calculadora import CorpoDaCalculadora
from app.http.serializacao_plano import vocabulario_do_caso
from app.montagem.calculo_divida import (
    CODIGO_ERRO_DE_CALCULO,
    CODIGO_ERRO_DE_ENTRADA,
    ErroDeCalculo,
    ErroDeEntrada,
    calcular_saldo,
    calcular_taxa,
    validar_entrada,
)
from app.montagem.conversao import converter_para_dinheiro as d
from app.montagem.conversao import converter_para_taxa as t
from app.montagem.premissas import campos_resolvidos, premissas_da_ficha
from app.revisao.comprovacao import pendencias_de_homologacao
from collection.carga import carregar_registros
from collection.registro import EscopoRepeticao
from collection.respostas import NAO_SEI
from engine.tipos import SISTEMA_AMORTIZACAO
from report.plano import carregar_textos_canonicos, montar_contexto_plano
from tests.app_aluno.test_avisos_de_pagamento import _PARCELA, _plano
from tests.app_aluno.test_montagem_divida_calculada import _ficha

PRICE, SAC = SISTEMA_AMORTIZACAO.PRICE, SISTEMA_AMORTIZACAO.SAC


def test_avisos_de_pagamento_so_com_premissas_no_vocabulario() -> None:
    snapshot, vocabulario, contexto = _plano({_PARCELA: d("150,00")})
    assert "não cobre os juros" in " ".join(contexto.avisos_gerais)
    sem = vocabulario_do_caso((), _ficha("D001", {}), ["D001"])  # montagem do aluno
    assert not sem.com_premissas
    aluno = montar_contexto_plano(
        snapshot, carregar_textos_canonicos(), sem, None, date(2026, 11, 5)
    )
    assert not aluno.avisos_gerais


def test_taxa_calculada_nao_deixa_periodicidade_ausente_na_homologacao() -> None:
    ficha = {
        "SALDO_DEVEDOR_ATUAL": d("10.000,00"),
        _PARCELA: d("528,72"),
        "PRAZO_RESTANTE_MESES": 24,
        "TAXA_DIVIDA": NAO_SEI,
        "PERIODICIDADE_TAXA_DIVIDA": "DESCONHECIDO",
    }
    respostas = _ficha("D001", ficha)
    itens = {EscopoRepeticao.DIVIDA_ID: ("D001",)}
    resolvidas = campos_resolvidos(respostas, itens)
    assert ("D001", "PERIODICIDADE_TAXA_DIVIDA") in resolvidas
    pendencias = pendencias_de_homologacao(
        carregar_registros().registros, respostas, itens, resolvidas
    )
    assert ("D001", "B5.D06") not in [(p.item_id, p.ID_PERGUNTA) for p in pendencias]


def test_divida_excluida_por_falta_de_minimo_chega_ao_revisor() -> None:
    from tests.app_aluno.test_prioridade import _duas_sem_pagamento, _planejar

    respostas, itens = _duas_sem_pagamento(minimo_1=NAO_SEI, minimo_2=NAO_SEI)
    plano = _planejar((respostas, itens))
    assert plano.sem_minimo == ("D002",)
    vocabulario = vocabulario_do_caso(
        (),
        respostas,
        ["D001"],
        (),
        premissas_da_ficha(respostas, itens),
        sem_minimo=plano.sem_minimo,
    )
    assert vocabulario.dividas_pendentes == (("D002", ("PAGAMENTO_MINIMO_DIVIDA",)),)
    assert vocabulario.plano_parcial


def test_sac_taxa_zero_com_divisao_inexata_como_o_price() -> None:
    for sistema in (PRICE, SAC):
        assert calcular_taxa(d("1.000,00"), d("333,33"), 3, sistema) == t("0")


def test_saldo_calculado_zero_e_sem_convergencia() -> None:
    with pytest.raises(ErroDeCalculo) as erro:
        calcular_saldo(d("0,01"), t("100"), 1, PRICE)
    assert erro.value.codigo is CODIGO_ERRO_DE_CALCULO.SEM_CONVERGENCIA


def test_teto_de_saldo_e_parcela() -> None:
    enorme = "9" * 40
    with pytest.raises(ErroDeEntrada) as erro:
        validar_entrada(saldo=enorme)
    assert erro.value.codigo is CODIGO_ERRO_DE_ENTRADA.SALDO_ACIMA_DO_MAXIMO
    with pytest.raises(ErroDeEntrada) as erro:
        validar_entrada(parcela="1.000.000.000,01")
    assert erro.value.codigo is CODIGO_ERRO_DE_ENTRADA.PARCELA_ACIMA_DO_MAXIMO
    assert validar_entrada(saldo="1.000.000.000,00").saldo == d("1.000.000.000,00")


def test_corpo_com_texto_gigante_e_invalido() -> None:
    with pytest.raises(ValidationError):
        CorpoDaCalculadora.model_validate(
            {"sistema": "PRICE", "periodicidade": "MENSAL", "saldo": "9" * 65}
        )
