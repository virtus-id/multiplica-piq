"""Quem recebe a parcela estimada de 24 meses — `T-526` a `T-529`.

`planejar_pagamentos` com o motor de verdade (parâmetros de arquivo), sem tocar
`engine/`. Mapeamento nos campos de pagamento: hipótese adotada do spike `T-523`.

REGRAS: `RF-534`, `RF-535`, `RF-537`, `EC-75`, `OQ-84`, `AC-546`, `AC-547`
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.montagem.calculo_divida import calcular_parcela
from app.montagem.conversao import converter_para_dinheiro as d
from app.montagem.conversao import converter_para_taxa as t
from app.montagem.estado import montar_estado_financeiro
from app.montagem.premissas import PremissasDaDivida
from app.montagem.prioridade import (
    Montar,
    PlanoDePagamentos,
    ResultadoDaPassagem,
    Rodar,
    limitar_capacidade_ao_caixa,
    planejar_pagamentos,
)
from collection.registro import EscopoRepeticao
from collection.respostas import NAO_SEI, RespostasCaso
from engine.estado import Divida, EstadoFinanceiro
from engine.motor import calcular_plano
from engine.tipos import DESCONHECIDO, SISTEMA_AMORTIZACAO, DinheiroTalvez
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.app_aluno.fixtures.caso_completo import DATA_REFERENCIA, PARAMETROS_EXTERNOS_PADRAO
from tests.app_aluno.test_montagem_divida_calculada import _caso, _itens, _por_escopo
from tests.app_aluno.test_plano_ponta_a_ponta import _T02_D001, _T02_D002

_PARCELA = "PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)"
PRICE = SISTEMA_AMORTIZACAO.PRICE
_PARAMETROS = FonteParametrosArquivo().carregar("1.0.1")


def _sem_pagamento(base: dict[str, object], **extra: object) -> dict[str, object]:
    return {**base, _PARCELA: NAO_SEI, "PRAZO_RESTANTE_MESES": NAO_SEI, **extra}


def _fichas(
    **por_item: dict[str, object],
) -> tuple[RespostasCaso, dict[EscopoRepeticao, tuple[str, ...]]]:
    return _caso(por_item), _por_escopo(_itens(tuple(por_item)))


def _montar(respostas: RespostasCaso) -> Montar:
    def montar(
        dividas: tuple[Divida, ...], fora: tuple[PremissasDaDivida, ...]
    ) -> EstadoFinanceiro:
        return montar_estado_financeiro(
            respostas,
            DATA_REFERENCIA=DATA_REFERENCIA,
            dividas=dividas,
            dividas_pendentes=fora,
            **PARAMETROS_EXTERNOS_PADRAO,  # type: ignore[arg-type]
        )

    return montar


def _rodar_o_motor(estado: EstadoFinanceiro) -> ResultadoDaPassagem:
    snapshot = calcular_plano(estado, _PARAMETROS)
    return ResultadoDaPassagem(
        snapshot.DIVIDA_ALVO_ATUAL, snapshot.diagnostico.RESULTADO_CAIXA_OBSERVADO
    )


def _planejar(
    fichas: tuple[RespostasCaso, dict[EscopoRepeticao, tuple[str, ...]]],
    rodar: Rodar = _rodar_o_motor,
) -> PlanoDePagamentos:
    respostas, itens = fichas
    return planejar_pagamentos(respostas, itens, _montar(respostas), rodar)


def _paga(divida: Divida) -> Decimal:
    pagamento = divida.PAGAMENTO_MENSAL_EFETIVO
    assert isinstance(pagamento, Decimal)
    return pagamento


def _por_id(plano: PlanoDePagamentos) -> dict[str, Divida]:
    return {x.DIVIDA_ID: x for x in plano.estado.dividas}


def _duas_sem_pagamento(
    minimo_1: object = d("60"), minimo_2: object = d("80")
) -> tuple[RespostasCaso, dict[EscopoRepeticao, tuple[str, ...]]]:
    return _fichas(
        D001=_sem_pagamento(_T02_D001, PAGAMENTO_MINIMO_DIVIDA=minimo_1),
        D002=_sem_pagamento(_T02_D002, PAGAMENTO_MINIMO_DIVIDA=minimo_2),
    )


def test_ac546_so_a_prioritaria_recebe_a_parcela_estimada() -> None:
    plano = _planejar(_duas_sem_pagamento())
    dividas = _por_id(plano)

    assert plano.prioritaria == "D001"  # maior taxa (10% contra 2%)
    assert plano.hipotese is False
    assert plano.passagens == 2
    assert _paga(dividas["D001"]) > d("60")  # a estimada de 24 meses sobre R$ 1.800,00 a 10%
    assert _paga(dividas["D002"]) == d("80")  # o mínimo
    # habitual ausente: devido 0 nas duas (ressalva a), nunca DESCONHECIDO
    assert dividas["D001"].PARCELA_CONTRATUAL == dividas["D002"].PARCELA_CONTRATUAL == d("0")


def test_ec75_trocar_a_prioritaria_migra_a_parcela() -> None:
    antes = _planejar(_duas_sem_pagamento())
    # D002 passa a ter a maior taxa: a parcela estimada migra para ela
    caro = {**_T02_D002, "TAXA_DIVIDA": t("15")}
    depois = _planejar(
        _fichas(
            D001=_sem_pagamento(_T02_D001, PAGAMENTO_MINIMO_DIVIDA=d("60")),
            D002=_sem_pagamento(caro, PAGAMENTO_MINIMO_DIVIDA=d("80")),
        )
    )
    assert (antes.prioritaria, depois.prioritaria) == ("D001", "D002")
    novas = _por_id(depois)
    assert _paga(novas["D001"]) == d("60")
    assert _paga(novas["D002"]) > d("80")


def test_oq84_nao_prioritaria_sem_minimo_e_sem_habitual_fica_pendente() -> None:
    plano = _planejar(_duas_sem_pagamento(minimo_1=NAO_SEI, minimo_2=NAO_SEI))
    assert plano.prioritaria == "D001"
    assert plano.sem_minimo == ("D002",)
    assert [x.DIVIDA_ID for x in plano.estado.dividas] == ["D001"]
    assert plano.estado.INVENTARIO_COMPLETO is False  # plano provisório, nunca zero


def test_sem_divida_estimavel_o_motor_nao_roda() -> None:
    chamadas: list[object] = []

    def espia(estado: EstadoFinanceiro) -> ResultadoDaPassagem:
        chamadas.append(estado)
        return _rodar_o_motor(estado)

    plano = _planejar(_fichas(D001=dict(_T02_D001), D002=dict(_T02_D002)), espia)
    assert chamadas == []
    assert (plano.passagens, plano.prioritaria, plano.hipotese) == (0, None, False)


def test_alvo_oscilante_termina_em_ate_tres_passagens_e_marca_hipotese() -> None:
    """Empate oscilante (`EC-75`): a alvo troca a cada passagem; fica na passagem 1."""
    alvos = iter(["D001", "D002", "D001", "D002"])
    chamadas: list[int] = []

    def oscila(estado: EstadoFinanceiro) -> ResultadoDaPassagem:
        chamadas.append(1)
        return ResultadoDaPassagem(next(alvos), d("1000"))

    plano = _planejar(_duas_sem_pagamento(), oscila)
    assert len(chamadas) <= 3
    assert plano.passagens <= 3
    assert (plano.hipotese, plano.prioritaria) == (True, None)
    # ficou na passagem 1: todas no mínimo
    assert all(x.PAGAMENTO_MENSAL_EFETIVO in (d("60"), d("80")) for x in plano.estado.dividas)


def test_falha_do_motor_cai_para_uma_passagem_e_marca_hipotese() -> None:
    chamadas: list[int] = []

    def falha_na_segunda(estado: EstadoFinanceiro) -> ResultadoDaPassagem:
        chamadas.append(1)
        if len(chamadas) == 2:
            raise RuntimeError("falha de teste")
        return _rodar_o_motor(estado)

    plano = _planejar(_duas_sem_pagamento(), falha_na_segunda)
    assert plano.hipotese is True
    assert plano.prioritaria is None
    assert {x.PAGAMENTO_MENSAL_EFETIVO for x in plano.estado.dividas} == {d("60"), d("80")}


def test_sem_executar_o_motor_monta_so_a_passagem_1() -> None:
    respostas, itens = _duas_sem_pagamento()
    plano = planejar_pagamentos(respostas, itens, _montar(respostas))
    assert plano.passagens == 0
    assert {x.PAGAMENTO_MENSAL_EFETIVO for x in plano.estado.dividas} == {d("60"), d("80")}


# --- RESSALVA (b): ponto único do teto de capacidade ------------------------------------


def _estado_com_capacidade(valor: DinheiroTalvez) -> EstadoFinanceiro:
    respostas, itens = _duas_sem_pagamento()
    estado = planejar_pagamentos(respostas, itens, _montar(respostas)).estado
    import dataclasses

    return dataclasses.replace(estado, CAPACIDADE_ATAQUE_DECLARADA=valor)


def test_teto_da_capacidade_so_desce_ate_o_caixa() -> None:
    estado = _estado_com_capacidade(d("5000"))
    assert limitar_capacidade_ao_caixa(estado, d("2554,76")).CAPACIDADE_ATAQUE_DECLARADA == d(
        "2554,76"
    )
    # nunca sobe
    assert limitar_capacidade_ao_caixa(estado, d("9000")) is estado
    # caixa negativo: capacidade 0, não negativa
    assert limitar_capacidade_ao_caixa(estado, d("-145,24")).CAPACIDADE_ATAQUE_DECLARADA == d("0")


def test_teto_da_capacidade_nao_toca_declarada_desconhecida() -> None:
    estado = _estado_com_capacidade(DESCONHECIDO)
    assert limitar_capacidade_ao_caixa(estado, d("100")) is estado


def test_plano_com_estimada_limita_a_capacidade_ao_caixa_observado() -> None:
    plano = _planejar(_duas_sem_pagamento())
    caixa = calcular_plano(plano.estado, _PARAMETROS).diagnostico.RESULTADO_CAIXA_OBSERVADO
    declarada = plano.estado.CAPACIDADE_ATAQUE_DECLARADA
    assert isinstance(declarada, Decimal)
    assert declarada <= max(caixa, d("0")) or plano.capacidade_limitada is False


@pytest.mark.parametrize("habitual", [None, d("0")])
def test_ac547_habitual_ausente_ou_zero_preserva_o_alerta_de_crescimento(
    habitual: Decimal | None,
) -> None:
    """Falta igual aos juros: a parcela estimada não esconde a dívida que cresce."""
    ficha = _sem_pagamento(_T02_D001, PAGAMENTO_MINIMO_DIVIDA=d("60"))
    if habitual is not None:
        ficha[_PARCELA] = habitual
    plano = _planejar(
        _fichas(D001=ficha, D002=_sem_pagamento(_T02_D002, PAGAMENTO_MINIMO_DIVIDA=d("80")))
    )
    diag = calcular_plano(plano.estado, _PARAMETROS).diagnostico
    crescem = {x.DIVIDA_ID: x for x in diag.DIVIDAS_QUE_CRESCEM}
    assert "D001" in crescem
    assert crescem["D001"].FALTA_DE_JUROS == crescem["D001"].JUROS_DO_MES


# --- T-528: executor com mais de uma passagem ----------------------------------------------


def test_avaliar_passagem_so_le_alvo_e_caixa_sem_gravar_nada() -> None:
    from app.motor.executor import avaliar_passagem

    respostas, itens = _duas_sem_pagamento()
    base = planejar_pagamentos(respostas, itens, _montar(respostas)).estado
    alvo, caixa = avaliar_passagem(base, _PARAMETROS)
    snapshot = calcular_plano(base, _PARAMETROS)
    assert (alvo, caixa) == (
        snapshot.DIVIDA_ALVO_ATUAL,
        snapshot.diagnostico.RESULTADO_CAIXA_OBSERVADO,
    )


def test_planejar_com_limite_devolve_o_definitivo_ou_cai_para_o_provisorio() -> None:
    import asyncio
    import time

    from app.motor.executor import planejar_com_limite_async

    respostas, itens = _duas_sem_pagamento()
    provisorio = planejar_pagamentos(respostas, itens, _montar(respostas)).estado
    definitivo = _planejar((respostas, itens)).estado

    def falha() -> EstadoFinanceiro:
        raise RuntimeError("falha de teste")

    def lenta() -> EstadoFinanceiro:
        time.sleep(0.3)
        return definitivo

    async def rodar() -> tuple[EstadoFinanceiro, EstadoFinanceiro, EstadoFinanceiro]:
        return (
            await planejar_com_limite_async(lambda: definitivo, provisorio),
            await planejar_com_limite_async(falha, provisorio),
            await planejar_com_limite_async(lenta, provisorio, tempo_limite_segundos=0.05),
        )

    ok, com_falha, estourou = asyncio.run(rodar())
    assert ok is definitivo
    assert com_falha is provisorio  # falha na segunda passagem ⇒ uma passagem
    assert estourou is provisorio  # nunca deixa o caso preso em `CALCULANDO`


def test_ec75_marca_estimado_acompanha_so_a_dividas_que_paga_a_estimada() -> None:
    """`EC-75`/`AC-546`: a não prioritária paga o mínimo; sua linha de pagamento não
    pode ser marcada `estimado` para o revisor, nem avisar "24 meses" sobre ela."""
    from datetime import date

    from app.http.serializacao_plano import vocabulario_do_caso
    from app.montagem.premissas import premissas_da_ficha
    from report.plano import (
        carregar_textos_canonicos,
        montar_contexto_estado_inputs,
        montar_contexto_plano,
    )

    fichas = _duas_sem_pagamento()
    respostas, itens = fichas
    plano = _planejar(fichas)
    snapshot = calcular_plano(plano.estado, _PARAMETROS)
    vocabulario = vocabulario_do_caso(
        (), respostas, ["D001", "D002"], (), premissas_da_ficha(respostas, itens)
    )
    textos = carregar_textos_canonicos()

    estado = montar_contexto_estado_inputs(snapshot.estado_inputs, textos, vocabulario)
    marcas = {
        div.DIVIDA_ID: {c.codigo: c.marca for c in div.campos if c.marca} for div in estado.dividas
    }
    assert marcas["D001"].get("PAGAMENTO_MENSAL_EFETIVO") == "estimado"  # a prioritária
    assert "PAGAMENTO_MENSAL_EFETIVO" not in marcas["D002"]  # paga o mínimo declarado

    contexto = montar_contexto_plano(snapshot, textos, vocabulario, None, date(2026, 11, 5))
    assert sum("24 meses" in aviso for aviso in contexto.avisos_gerais) == 1


@pytest.mark.parametrize(
    "tipo",
    [
        "CARTAO_ROTATIVO",
        "CHEQUE_ESPECIAL",
        "CARTAO_PARCELADO",
        "PESSOAL",
        "CONSIGNADO",
        "FIN_VEICULO",
        "FIN_IMOBILIARIO",
    ],
)
def test_ac543_a_base_de_24_meses_vale_em_todas_as_modalidades(tipo: str) -> None:
    """`AC-543`/`EC-72`: saldo e taxa, sem parcela e sem prazo ⇒ a estimada de 24 meses
    (R$ 528,72 sobre R$ 10.000,00 a 2%) paga a única dívida, qualquer que seja o tipo."""
    ficha = _sem_pagamento(
        {
            "TIPO_DIVIDA": tipo,
            "SALDO_DEVEDOR_ATUAL": d("10.000,00"),
            "TAXA_DIVIDA": t("2"),
            "PERIODICIDADE_TAXA_DIVIDA": "MENSAL",
            "PESO_EMOCIONAL": 5,
        }
    )
    plano = _planejar(_fichas(D001=ficha))
    assert _paga(_por_id(plano)["D001"]) == d("528,72")


@pytest.mark.parametrize(
    ("informado", "esperado"),
    [
        ({_PARCELA: d("600,00"), "PRAZO_RESTANTE_MESES": NAO_SEI}, d("600,00")),
        ({_PARCELA: d("0,00"), "PRAZO_RESTANTE_MESES": NAO_SEI}, d("528,72")),
        (
            {_PARCELA: NAO_SEI, "PRAZO_RESTANTE_MESES": 36},
            calcular_parcela(d("10000"), t("2"), 36, PRICE),
        ),
    ],
)
def test_ac544_a_informacao_do_aluno_prevalece_sobre_os_24_meses(
    informado: dict[str, object], esperado: Decimal
) -> None:
    ficha = {
        "TIPO_DIVIDA": "PESSOAL",
        "SALDO_DEVEDOR_ATUAL": d("10.000,00"),
        "TAXA_DIVIDA": t("2"),
        "PERIODICIDADE_TAXA_DIVIDA": "MENSAL",
        "PESO_EMOCIONAL": 5,
        **informado,
    }
    pago = _paga(_por_id(_planejar(_fichas(D001=ficha)))["D001"])
    assert pago == esperado
