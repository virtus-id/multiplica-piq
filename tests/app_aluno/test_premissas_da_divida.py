"""`resolver_divida` — tabela-verdade, recálculo e invalidação.

`T-486` a `T-490` (`RF-525`, `RF-526`, `RF-527`, `RF-528`, `EC-62`, `EC-70`,
`EC-71`, `AC-536`, `AC-537`, `AC-538`).

REGRAS: `RF-525`, `RF-526`, `RF-527`, `RF-528`
"""

from __future__ import annotations

import itertools
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.montagem.calculo_divida import CAMPO_DA_DIVIDA, calcular_parcela
from app.montagem.conversao import converter_para_dinheiro as d
from app.montagem.conversao import converter_para_taxa as t
from app.montagem.premissas import (
    MARCA_DO_VALOR,
    SITUACAO_DA_DIVIDA,
    PremissasDaDivida,
    campos_dispensados,
    dividas_pendentes,
    impressao_dos_valores,
    resolver_divida,
)
from collection.registro import EscopoRepeticao
from collection.respostas import NAO_SEI, Resposta, RespostasCaso, ValorResposta
from engine.tipos import SISTEMA_AMORTIZACAO

F = CAMPO_DA_DIVIDA
M = MARCA_DO_VALOR
PRICE = SISTEMA_AMORTIZACAO.PRICE
SAC = SISTEMA_AMORTIZACAO.SAC

_VARIAVEL = {
    F.SALDO: "SALDO_DEVEDOR_ATUAL",
    F.PARCELA: "PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)",
    F.TAXA: "TAXA_DIVIDA",
    F.PRAZO: "PRAZO_RESTANTE_MESES",
}
_QUANDO = datetime(2026, 11, 4, tzinfo=UTC)


def _respostas(
    *itens: tuple[str, dict[str, ValorResposta]],
) -> RespostasCaso:
    return RespostasCaso(
        tuple(
            Resposta("C1", variavel, item, valor, "1.3.0", _QUANDO)
            for item, variaveis in itens
            for variavel, valor in variaveis.items()
        )
    )


_SALDO = d("10000")
_PARCELA = d("528,72")
_TAXA = t("2")


def _ficha(
    *,
    saldo: ValorResposta = _SALDO,
    parcela: ValorResposta = _PARCELA,
    taxa: ValorResposta = _TAXA,
    prazo: ValorResposta = 24,
    sistema: str = "PRICE",
    periodicidade: str = "MENSAL",
    escolha: str | None = None,
) -> dict[str, ValorResposta]:
    ficha: dict[str, ValorResposta] = {
        _VARIAVEL[F.SALDO]: saldo,
        _VARIAVEL[F.PARCELA]: parcela,
        _VARIAVEL[F.TAXA]: taxa,
        _VARIAVEL[F.PRAZO]: prazo,
        "SISTEMA_AMORTIZACAO": sistema,
        "PERIODICIDADE_TAXA_DIVIDA": periodicidade,
    }
    if escolha is not None:
        ficha["INFORMACAO_A_RECALCULAR"] = escolha
    return ficha


def _resolver(ficha: dict[str, ValorResposta]) -> PremissasDaDivida:
    return resolver_divida(_respostas(("D1", ficha)), "D1")


def _impressao(ficha: dict[str, ValorResposta], sistema: SISTEMA_AMORTIZACAO) -> str:
    return impressao_dos_valores(
        ficha[_VARIAVEL[F.SALDO]],
        ficha[_VARIAVEL[F.PARCELA]],
        ficha[_VARIAVEL[F.TAXA]],
        ficha[_VARIAVEL[F.PRAZO]],
        sistema,
        str(ficha["PERIODICIDADE_TAXA_DIVIDA"]),
    )


# --- T-489: tabela-verdade, 2^4 x Price/SAC --------------------------------------------

_BASE = {F.SALDO: d("10000"), F.TAXA: t("2"), F.PRAZO: 24}
_COMBINACOES = [
    (sistema, desconhecidos)
    for sistema in (PRICE, SAC)
    for tamanho in range(5)
    for desconhecidos in itertools.combinations((F.SALDO, F.PARCELA, F.TAXA, F.PRAZO), tamanho)
]


def _id(par: tuple[SISTEMA_AMORTIZACAO, tuple[F, ...]]) -> str:
    sistema, desconhecidos = par
    return f"{sistema.value}-nao-sei-em-{'+'.join(c.value for c in desconhecidos) or 'nenhum'}"


@pytest.mark.parametrize("par", _COMBINACOES, ids=_id)
def test_ac537_ac538_tabela_verdade(par: tuple[SISTEMA_AMORTIZACAO, tuple[F, ...]]) -> None:
    sistema, desconhecidos = par
    parcela = calcular_parcela(d("10000"), t("2"), 24, sistema)
    todos = {**_BASE, F.PARCELA: parcela}
    ficha = _ficha(parcela=parcela, sistema=sistema.value)
    for campo in desconhecidos:
        ficha[_VARIAVEL[campo]] = NAO_SEI

    premissas = _resolver(ficha)

    assert premissas.sistema is sistema
    if set(desconhecidos) == {F.PARCELA, F.PRAZO}:
        # `RF-532` (Fase 2): saldo e taxa sem parcela e sem prazo deixam de ser `PENDENTE`.
        assert premissas.situacao is SITUACAO_DA_DIVIDA.COMPLETA
        assert premissas.faltas == ()
        assert premissas.valores[F.PARCELA].marca is M.ESTIMADO
        assert premissas.valores[F.PRAZO].marca is M.PENDENTE
        return
    faltas_esperadas = tuple(c for c in (F.SALDO, F.PARCELA, F.TAXA) if c in desconhecidos)
    for campo in (F.SALDO, F.PARCELA, F.TAXA, F.PRAZO):
        valor = premissas.valores[campo]
        if campo not in desconhecidos:
            assert (valor.marca, valor.valor) == (M.INFORMADO, todos[campo])
        elif len(desconhecidos) <= 1 or (campo is F.PRAZO and len(desconhecidos) == 1):
            assert valor.marca is M.CALCULADO
            assert valor.valor is not None
        else:
            # "não sei" nunca vira 0 (AC-537)
            assert (valor.marca, valor.valor) == (M.PENDENTE, None)

    if len(desconhecidos) <= 1:
        assert premissas.situacao is SITUACAO_DA_DIVIDA.COMPLETA
        assert premissas.faltas == ()
        assert premissas.taxa_mensal_normalizada is not None
    else:
        assert premissas.situacao is SITUACAO_DA_DIVIDA.PENDENTE
        assert premissas.faltas == faltas_esperadas
    if desconhecidos == (F.PARCELA,):
        assert premissas.valores[F.PARCELA].valor == parcela  # AC-538
    if desconhecidos == (F.SALDO,):
        assert abs(Decimal(str(premissas.valores[F.SALDO].valor)) - d("10000")) <= d(
            "0,5"
        )  # parcela arredondada para cima
    if desconhecidos == (F.TAXA,):
        assert abs(Decimal(str(premissas.valores[F.TAXA].valor)) - t("2")) <= t("0,001")
    if desconhecidos == (F.PRAZO,):
        assert premissas.valores[F.PRAZO].valor == 24


def test_ac537_nao_sei_no_saldo_sozinho_e_calculado_nao_zero() -> None:
    ficha = _ficha()
    ficha[_VARIAVEL[F.SALDO]] = NAO_SEI
    valor = _resolver(ficha).valores[F.SALDO]
    assert valor.marca is M.CALCULADO
    assert valor.valor != 0
    assert ficha[_VARIAVEL[F.SALDO]] is NAO_SEI  # a resposta fica intacta


def test_ec62_divida_sem_nenhuma_resposta_e_pendente() -> None:
    premissas = resolver_divida(_respostas(("D1", {})), "D1")
    assert premissas.situacao is SITUACAO_DA_DIVIDA.PENDENTE
    assert premissas.faltas == (F.SALDO, F.PARCELA, F.TAXA)
    assert all(v.valor is None and v.marca is M.PENDENTE for v in premissas.valores.values())
    assert premissas.taxa_mensal_normalizada is None
    assert premissas.sistema is PRICE  # padrao (RF-523)


def test_oq92_parcela_zero_e_resposta_valida_fora_da_conta() -> None:
    # S, T ok e P = 0,00: completa para o motor; o prazo não sai de uma parcela zero.
    ficha = _ficha(parcela=d("0"), prazo=NAO_SEI)
    premissas = _resolver(ficha)
    assert premissas.situacao is SITUACAO_DA_DIVIDA.COMPLETA
    assert (premissas.valores[F.PARCELA].valor, premissas.valores[F.PARCELA].marca) == (
        d("0"),
        M.INFORMADO,
    )
    assert (premissas.valores[F.PRAZO].valor, premissas.valores[F.PRAZO].marca) == (
        None,
        M.PENDENTE,
    )
    # nunca calcula saldo ou taxa a partir de uma parcela zero
    sem_saldo = _resolver(_ficha(parcela=d("0"), saldo=NAO_SEI))
    assert sem_saldo.situacao is SITUACAO_DA_DIVIDA.PENDENTE
    assert sem_saldo.faltas == (F.SALDO,)
    # quatro informados com parcela 0,00: incompatível (OQ-92)
    quatro = _resolver(_ficha(parcela=d("0")))
    assert quatro.situacao is SITUACAO_DA_DIVIDA.INCOMPATIVEL


def test_valor_gravado_invalido_nao_e_sobrescrito_por_calculo() -> None:
    premissas = _resolver(_ficha(saldo=d("-5")))
    assert premissas.situacao is SITUACAO_DA_DIVIDA.PENDENTE
    assert premissas.faltas == (F.SALDO,)
    assert premissas.valores[F.SALDO].marca is M.PENDENTE


def test_taxa_zero_informada_e_valida() -> None:
    premissas = _resolver(_ficha(taxa=t("0"), parcela=d("416,67")))
    assert premissas.valores[F.TAXA].marca is M.INFORMADO
    assert premissas.taxa_mensal_normalizada == 0


def test_parcela_que_nao_reduz_o_saldo_deixa_o_campo_pendente() -> None:
    # S=10000, i=2%, P=150, prazo desconhecido: sem prazo, e o prazo nao vai ao motor.
    premissas = _resolver(_ficha(parcela=d("150"), prazo=NAO_SEI))
    assert premissas.situacao is SITUACAO_DA_DIVIDA.COMPLETA
    assert premissas.valores[F.PRAZO].valor is None
    # Taxa que seria negativa: S/n > P, taxa desconhecida.
    sem_solucao = _resolver(_ficha(parcela=d("400"), taxa=NAO_SEI))
    assert sem_solucao.situacao is SITUACAO_DA_DIVIDA.PENDENTE
    assert sem_solucao.faltas == (F.TAXA,)


def test_taxa_anual_e_devolvida_na_periodicidade_gravada() -> None:
    ficha = _ficha(taxa=t("26,82"), periodicidade="ANUAL", parcela=NAO_SEI)
    premissas = _resolver(ficha)
    assert premissas.taxa_na_periodicidade == t("26,82")
    assert premissas.taxa_mensal_normalizada is not None
    assert abs(premissas.taxa_mensal_normalizada - t("2")) <= t("0,01")
    # taxa calculada volta ao ano
    ficha = _ficha(taxa=NAO_SEI, periodicidade="ANUAL")
    premissas = _resolver(ficha)
    taxa = premissas.valores[F.TAXA]
    assert taxa.marca is M.CALCULADO
    assert taxa.valor == premissas.taxa_na_periodicidade
    assert abs(Decimal(str(taxa.valor)) - t("26,82")) <= t("0,01")
    assert premissas.taxa_mensal_normalizada is not None
    assert abs(premissas.taxa_mensal_normalizada - t("2")) <= t("0,001")


# --- T-488: pendentes e campos resolvidos ------------------------------------------------


def _ficha_nao_sei(*campos: F) -> dict[str, ValorResposta]:
    ficha = _ficha()
    for campo in campos:
        ficha[_VARIAVEL[campo]] = NAO_SEI
    return ficha


def test_pendentes_na_ordem_da_ficha_e_ec62_quatro_nao_sei() -> None:
    respostas = _respostas(
        ("D3", _ficha_nao_sei(F.SALDO, F.PARCELA, F.TAXA, F.PRAZO)),
        ("D2", _ficha()),
        ("D1", _ficha_nao_sei(F.SALDO, F.TAXA)),
    )
    itens = {EscopoRepeticao.DIVIDA_ID: ("D1", "D2", "D3")}
    pendentes = dividas_pendentes(respostas, itens)
    assert [p.DIVIDA_ID for p in pendentes] == ["D1", "D3"]
    assert dividas_pendentes(respostas, {}) == ()


def test_campos_dispensados_calculados_e_os_que_faltam_na_pendente() -> None:
    respostas = _respostas(
        ("D1", _ficha_nao_sei(F.PARCELA)),
        ("D2", _ficha_nao_sei(F.SALDO, F.TAXA)),
    )
    itens = {EscopoRepeticao.DIVIDA_ID: ("D1", "D2")}
    resolvidos = campos_dispensados(respostas, itens)
    assert ("D1", _VARIAVEL[F.PARCELA]) in resolvidos
    # `OQ-89`: o que falta na pendente não bloqueia (fora do plano, apontada ao aluno)
    assert ("D2", _VARIAVEL[F.SALDO]) in resolvidos and ("D2", _VARIAVEL[F.TAXA]) in resolvidos
    assert ("D1", _VARIAVEL[F.SALDO]) not in resolvidos  # informado não aparece


# --- T-490 / T-487: recálculo, invalidação e troca de sistema ----------------------------


def _com_escolha(campo: str, **ficha: ValorResposta) -> dict[str, ValorResposta]:
    base = _ficha(**ficha)  # type: ignore[arg-type]
    sistema = SAC if base["SISTEMA_AMORTIZACAO"] == "SAC" else PRICE
    base["INFORMACAO_A_RECALCULAR"] = f"{campo}|{_impressao(base, sistema)}"
    return base


def test_ac536_escolher_parcela_no_caso_do_ac534() -> None:
    ficha = _com_escolha("PARCELA", parcela=d("400"))
    premissas = _resolver(ficha)
    assert premissas.recalcular_escolhido is F.PARCELA
    assert premissas.situacao is SITUACAO_DA_DIVIDA.COMPLETA
    parcela = premissas.valores[F.PARCELA]
    assert (parcela.valor, parcela.marca, parcela.original) == (
        d("528,72"),
        M.CALCULADO,
        d("400"),
    )
    for campo, esperado in ((F.SALDO, d("10000")), (F.TAXA, t("2")), (F.PRAZO, 24)):
        assert (premissas.valores[campo].valor, premissas.valores[campo].marca) == (
            esperado,
            M.INFORMADO,
        )
    assert ficha["PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)"] == d("400")


def test_ac536_escolher_taxa_deixa_os_outros_tres_intactos() -> None:
    ficha = _com_escolha("TAXA", parcela=d("600"))
    premissas = _resolver(ficha)
    assert premissas.recalcular_escolhido is F.TAXA
    taxa = premissas.valores[F.TAXA]
    assert taxa.marca is M.CALCULADO
    assert taxa.original == t("2")
    assert taxa.valor is not None and Decimal(str(taxa.valor)) > t("2")
    assert premissas.taxa_mensal_normalizada == taxa.valor
    assert premissas.valores[F.PARCELA].valor == d("600")
    assert premissas.valores[F.PARCELA].marca is M.INFORMADO
    assert premissas.valores[F.SALDO].valor == d("10000")
    assert premissas.valores[F.PRAZO].valor == 24


def test_ac536_sem_escolha_ou_nenhuma_mantem_originais_e_sinalizacao() -> None:
    for escolha in (None, "NENHUMA", "lixo", "PARCELA|"):
        premissas = _resolver(_ficha(parcela=d("400"), escolha=escolha))
        assert premissas.situacao is SITUACAO_DA_DIVIDA.INCOMPATIVEL
        assert premissas.parcela_teorica == d("528,72")
        assert premissas.recalcular_escolhido is None
        assert premissas.valores[F.PARCELA].valor == d("400")
        # `RF-538`: sem escolha, saldo e taxa viram hipótese; parcela e prazo seguem informados.
        assert premissas.valores[F.SALDO].marca is M.HIPOTESE
        assert premissas.valores[F.TAXA].marca is M.HIPOTESE
        assert premissas.valores[F.PARCELA].marca is M.INFORMADO
        assert premissas.valores[F.PRAZO].marca is M.INFORMADO


def test_escolha_sem_solucao_cai_para_os_originais() -> None:
    # AC-534 com "taxa": P = 400 < S/n, a taxa seria negativa (RF-519).
    premissas = _resolver(_com_escolha("TAXA", parcela=d("400")))
    assert premissas.situacao is SITUACAO_DA_DIVIDA.INCOMPATIVEL
    assert premissas.recalcular_escolhido is None
    assert premissas.valores[F.TAXA].marca is M.HIPOTESE  # `RF-538`


@pytest.mark.parametrize(
    "mudanca",
    [
        {"saldo": d("10000,01")},
        {"parcela": d("401")},
        {"taxa": t("2,01")},
        {"prazo": 25},
        {"sistema": "SAC"},
        {"periodicidade": "ANUAL"},
    ],
    ids=["saldo", "parcela", "taxa", "prazo", "sistema", "periodicidade"],
)
def test_ec70_ec71_mudar_valor_ou_sistema_invalida_a_escolha_sem_escrita(
    mudanca: dict[str, ValorResposta],
) -> None:
    antes = _com_escolha("PARCELA", parcela=d("400"))
    escolha_gravada = antes["INFORMACAO_A_RECALCULAR"]
    depois = {**antes}
    chaves = {
        "saldo": _VARIAVEL[F.SALDO],
        "parcela": _VARIAVEL[F.PARCELA],
        "taxa": _VARIAVEL[F.TAXA],
        "prazo": _VARIAVEL[F.PRAZO],
        "sistema": "SISTEMA_AMORTIZACAO",
        "periodicidade": "PERIODICIDADE_TAXA_DIVIDA",
    }
    for nome, valor in mudanca.items():
        depois[chaves[nome]] = valor
    respostas = _respostas(("D1", depois))
    copia = respostas.respostas

    premissas = resolver_divida(respostas, "D1")

    assert premissas.recalcular_escolhido is None
    assert premissas.valores[F.PARCELA].marca is not M.CALCULADO
    assert respostas.respostas == copia  # nenhuma escrita
    assert depois["INFORMACAO_A_RECALCULAR"] == escolha_gravada


def test_ec70_mudar_um_valor_remove_o_calculado_do_dependente() -> None:
    ficha = _ficha(parcela=NAO_SEI)
    antes = _resolver(ficha).valores[F.PARCELA]
    assert antes.marca is M.CALCULADO
    ficha[_VARIAVEL[F.TAXA]] = t("3")
    depois = _resolver(ficha).valores[F.PARCELA]
    assert depois.marca is M.CALCULADO
    assert depois.valor != antes.valor  # nada guardado: acompanha a resposta
    # informar a parcela tira o CALCULADO do campo
    ficha[_VARIAVEL[F.PARCELA]] = d("700")
    informado = _resolver(ficha).valores[F.PARCELA]
    assert (informado.marca, informado.valor) == (M.INFORMADO, d("700"))


def test_ec71_trocar_o_sistema_recalcula_sem_resquicio_do_anterior() -> None:
    price = _resolver(_ficha(parcela=NAO_SEI, sistema="PRICE")).valores[F.PARCELA]
    sac = _resolver(_ficha(parcela=NAO_SEI, sistema="SAC")).valores[F.PARCELA]
    assert price.valor == d("528,72")
    assert sac.valor == calcular_parcela(d("10000"), t("2"), 24, SAC)
    assert sac.valor != price.valor
    voltou = _resolver(_ficha(parcela=NAO_SEI, sistema="PRICE")).valores[F.PARCELA]
    assert voltou == price


# --- T-519: o revisor recebe só a marca por campo (`RF-528`, `OQ-87`, `AC-540`) ----------


def test_revisor_recebe_so_a_marca_por_campo_da_divida() -> None:
    from app.http.serializacao_plano import serializar_estado_inputs, vocabulario_do_caso
    from report.plano import carregar_textos_canonicos, montar_contexto_estado_inputs
    from tests.app_aluno.test_pendencias_do_relatorio import _snapshot_base

    estado = _snapshot_base().estado_inputs
    divida_id = estado.dividas[0].DIVIDA_ID
    respostas = _respostas((divida_id, _ficha_nao_sei(F.PARCELA)))
    premissas = (resolver_divida(respostas, divida_id),)
    vocabulario = vocabulario_do_caso((), respostas, [divida_id], (), premissas)

    textos = carregar_textos_canonicos()
    payload = serializar_estado_inputs(montar_contexto_estado_inputs(estado, textos, vocabulario))

    campos = {c["codigo"]: c for c in payload["dividas"][0]["campos"]}
    assert campos["PARCELA_CONTRATUAL"]["marca"] == "calculado"
    # digitado e o que a calculadora não tocou: sem marca (AC-540)
    assert "marca" not in campos["SALDO_DEVEDOR_ATUAL"]
    assert "marca" not in campos["TAXA_EFETIVA_MENSAL_NORMALIZADA"]
    # PD-14: só `nome`, `valor`, `codigo` e `marca`; nada de fórmula, juros ou cronograma
    assert all(
        set(c) <= {"nome", "valor", "codigo", "marca"} for c in payload["dividas"][0]["campos"]
    )
    assert not any("marca" in c for c in payload["campos"])  # só campos da dívida
    # segunda dívida do snapshot, sem premissas: nenhuma marca
    assert not any("marca" in c for c in payload["dividas"][1]["campos"])


# --- T-526: parcela estimada de 24 meses (Fase 2) ----------------------------------------


@pytest.mark.parametrize("sistema", [PRICE, SAC])
def test_ac543_estimada_sem_parcela_nem_prazo_vale_em_qualquer_sistema(
    sistema: SISTEMA_AMORTIZACAO,
) -> None:
    premissas = _resolver(_ficha(parcela=NAO_SEI, prazo=NAO_SEI, sistema=sistema.value))
    esperada = calcular_parcela(d("10000"), t("2"), 24, sistema)
    assert premissas.parcela_estimada is not None
    assert (premissas.parcela_estimada.valor, premissas.parcela_estimada.prazo_base) == (
        esperada,
        24,
    )
    assert premissas.parcela_estimada.habitual_ausente is True
    assert (premissas.valores[F.PARCELA].valor, premissas.valores[F.PARCELA].marca) == (
        esperada,
        M.ESTIMADO,
    )
    assert premissas.situacao is SITUACAO_DA_DIVIDA.COMPLETA


def test_ac543_dez_mil_a_dois_por_cento_da_528_72_estimado() -> None:
    premissas = _resolver(_ficha(parcela=NAO_SEI, prazo=NAO_SEI))
    assert premissas.parcela_estimada is not None
    assert premissas.parcela_estimada.valor == d("528,72")


def test_ac544_habitual_positivo_e_prazo_informado_prevalecem() -> None:
    # habitual 600: informado, nada a estimar
    com_habitual = _resolver(_ficha(parcela=d("600"), prazo=NAO_SEI))
    assert com_habitual.parcela_estimada is None
    assert com_habitual.valores[F.PARCELA].marca is M.INFORMADO
    # prazo 36: a calculadora da Fase 1 calcula a parcela sobre 36 meses
    com_prazo = _resolver(_ficha(parcela=NAO_SEI, prazo=36))
    assert com_prazo.parcela_estimada is None
    assert com_prazo.valores[F.PARCELA].marca is M.CALCULADO
    assert com_prazo.valores[F.PARCELA].valor == calcular_parcela(d("10000"), t("2"), 36, PRICE)


def test_ac544_e_ec73_habitual_zero_volta_aos_24_meses_sem_virar_estimado_no_campo() -> None:
    premissas = _resolver(_ficha(parcela=d("0"), prazo=NAO_SEI))
    assert premissas.parcela_estimada is not None
    assert premissas.parcela_estimada.valor == d("528,72")
    assert premissas.parcela_estimada.habitual_ausente is False  # zero declarado
    assert premissas.valores[F.PARCELA].marca is M.INFORMADO  # o campo digitado não muda


def test_estimada_exige_saldo_e_taxa_conhecidos() -> None:
    assert _resolver(_ficha(saldo=NAO_SEI, parcela=NAO_SEI, prazo=NAO_SEI)).parcela_estimada is None
    assert _resolver(_ficha(taxa=NAO_SEI, parcela=NAO_SEI, prazo=NAO_SEI)).parcela_estimada is None


def test_minimo_nao_sei_ou_ausente_e_none_nunca_zero() -> None:
    assert _resolver(_ficha()).pagamento_minimo is None
    assert _resolver({**_ficha(), "PAGAMENTO_MINIMO_DIVIDA": NAO_SEI}).pagamento_minimo is None
    assert _resolver({**_ficha(), "PAGAMENTO_MINIMO_DIVIDA": d("80")}).pagamento_minimo == d("80")
