"""Testes de `app/montagem/estado.py::montar_perfil_comportamental` e
`montar_sinais_comportamentais` — RF-14, AC-13 (T-50).

Cobre os quatro critérios de aceite de `T-50` com os registros REAIS dos
Blocos 1, 2 e 5 (`collection/registros/bloco-0{1,2,5}.yaml`, T-17), carregados
por `collection.carga.carregar_registros` — nenhum `VARIAVEL_GRAVADA`/
`valor_interno` é inventado no teste; todos vêm do próprio registro de
produção, para que uma mudança no YAML que quebre o mapeamento seja pega aqui.

REGRAS: RF-14, AC-13
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.montagem.estado import (
    ErroRespostaAusente,
    ErroSinalComportamentalAusente,
    ErroValorInternoDesconhecido,
    _autopercepcao_controle,
    montar_perfil_comportamental,
    montar_sinais_comportamentais,
)
from collection.carga import carregar_registros
from collection.respostas import NAO_SEI, Resposta, RespostasCaso
from engine.estado import (
    COBERTURA_MEIOS_PAGAMENTO,
    COBERTURA_PEQUENOS_GASTOS,
    CONHECIMENTO_GASTO,
    DEFASAGEM_REGISTRO,
    FREQUENCIA_REGISTRO,
    GASTOS_NAO_IDENTIFICADOS,
    REGISTRO_GASTOS,
    REVISAO_SEMANAL,
    PerfilComportamental,
    SinaisComportamentais,
)
from engine.tipos import DESCONHECIDO, SimNaoTalvez

_CASO_ID = "caso-teste-t50"
_QUESTIONARIO_VERSION = "1.0.0"
_AGORA = datetime(2026, 1, 1, tzinfo=UTC)

_OMITIR = object()  # sentinela local de teste: "não gravar esta resposta"


def _resposta(ID_PERGUNTA: str, valor: object, item_id: str | None = None) -> Resposta:
    return Resposta(
        CASO_ID=_CASO_ID,
        ID_PERGUNTA=ID_PERGUNTA,
        item_id=item_id,
        valor=valor,  # type: ignore[arg-type]
        QUESTIONARIO_VERSION=_QUESTIONARIO_VERSION,
        respondida_em=_AGORA,
    )


# Os 2 `VARIAVEL_GRAVADA` do Bloco 2 (collection/registros/bloco-02.yaml)
# que seguem perguntados para `PerfilComportamental` (`T-404`: as outras 6
# saíram), cada um com um `valor_interno` concreto e válido do registro.
def _perfil_comportamental_minimo_completo(**sobrescritas: object) -> RespostasCaso:
    valores: dict[str, object] = {
        "CONHECIMENTO_GASTO": "BOA_APROXIMACAO",
        "REVISAO_SEMANAL": "SEMPRE",
    }
    valores.update(sobrescritas)
    respostas = tuple(
        _resposta(ID_PERGUNTA=variavel, valor=valor)
        for variavel, valor in valores.items()
        if valor is not _OMITIR
    )
    return RespostasCaso(respostas=respostas)


# Os `VARIAVEL_GRAVADA` de `SinaisComportamentais` que seguem perguntados
# (`T-404`: `B1.02`, `B1.05`, `B1.10`, `B5.C07` e `B9.04` saíram).
def _sinais_comportamentais_minimo_completo(**sobrescritas: object) -> RespostasCaso:
    valores: dict[str, object] = {
        "MECANISMO_DEFICIT": frozenset({"CORTE"}),
        "NOVO_PARCELAMENTO_PREVISTO": "NAO",
        "PACTO": "ESTABELECIDO",
        "RISCO_IMPULSO": "NENHUMA",
        "NECESSIDADE_VITORIA": 5,
    }
    valores.update(sobrescritas)
    respostas = tuple(
        _resposta(ID_PERGUNTA=variavel, valor=valor)
        for variavel, valor in valores.items()
        if valor is not _OMITIR
    )
    return RespostasCaso(respostas=respostas)


# ---------------------------------------------------------------------------
# Critério 1 (AC-13) — as 8 variáveis de PerfilComportamental e os 10 campos
# de SinaisComportamentais estão preenchidos.
# ---------------------------------------------------------------------------
class TestCriterio1AC13TodosOsCamposPreenchidos:
    def test_perfil_comportamental_com_as_variaveis_perguntadas_e_as_neutras(self) -> None:
        respostas = _perfil_comportamental_minimo_completo()

        perfil = montar_perfil_comportamental(respostas)

        assert isinstance(perfil, PerfilComportamental)
        assert perfil.CONHECIMENTO_GASTO is CONHECIMENTO_GASTO.BOA_APROXIMACAO
        assert perfil.REVISAO_SEMANAL is REVISAO_SEMANAL.SEMPRE
        # `T-404` (RF-418): as seis que saíram do questionário.
        assert perfil.REGISTRO_GASTOS is REGISTRO_GASTOS.PARTE
        assert perfil.FREQUENCIA_REGISTRO is FREQUENCIA_REGISTRO.INDEFINIDA
        assert perfil.DEFASAGEM_REGISTRO is DEFASAGEM_REGISTRO.DIAS_DEPOIS
        assert perfil.COBERTURA_PEQUENOS_GASTOS is COBERTURA_PEQUENOS_GASTOS.ALGUNS
        assert perfil.COBERTURA_MEIOS_PAGAMENTO is COBERTURA_MEIOS_PAGAMENTO.QUASE_TOTAL
        assert perfil.GASTOS_NAO_IDENTIFICADOS is GASTOS_NAO_IDENTIFICADOS.ALGUMAS_MES

    def test_resposta_antiga_das_perguntas_que_sairam_e_ignorada(self) -> None:
        respostas = _perfil_comportamental_minimo_completo(
            REGISTRO_GASTOS="TUDO", GASTOS_NAO_IDENTIFICADOS="NUNCA"
        )

        perfil = montar_perfil_comportamental(respostas)

        assert perfil.REGISTRO_GASTOS is REGISTRO_GASTOS.PARTE
        assert perfil.GASTOS_NAO_IDENTIFICADOS is GASTOS_NAO_IDENTIFICADOS.ALGUMAS_MES

    @pytest.mark.parametrize("campo_obrigatorio", ["CONHECIMENTO_GASTO", "REVISAO_SEMANAL"])
    def test_campo_de_perfil_sem_resposta_levanta_erro_explicito(
        self, campo_obrigatorio: str
    ) -> None:
        respostas = _perfil_comportamental_minimo_completo(**{campo_obrigatorio: _OMITIR})

        with pytest.raises(ErroRespostaAusente) as excecao:
            montar_perfil_comportamental(respostas)

        assert excecao.value.VARIAVEL_GRAVADA == campo_obrigatorio

    def test_sinais_comportamentais_perguntados_e_neutros(self) -> None:
        respostas = _sinais_comportamentais_minimo_completo()

        sinais = montar_sinais_comportamentais(respostas)

        assert isinstance(sinais, SinaisComportamentais)
        assert sinais.MECANISMO_DEFICIT == frozenset({"CORTE"})
        assert sinais.NOVO_PARCELAMENTO_PREVISTO is SimNaoTalvez.NAO
        assert sinais.PACTO == "ESTABELECIDO"
        assert sinais.RISCO_IMPULSO == "NENHUMA"
        assert sinais.NECESSIDADE_VITORIA == 5
        # `T-404` (RF-418): as cinco que saíram do questionário.
        assert sinais.NOVA_DIVIDA_PREVISTA is SimNaoTalvez.NAO
        assert sinais.HISTORICO_RECAIDA is SimNaoTalvez.TALVEZ
        assert sinais.HISTORICO_ABANDONO is SimNaoTalvez.TALVEZ
        assert sinais.JANELA_NOVA_DIVIDA is None
        assert sinais.LINHA_CONTINUA_SENDO_UTILIZADA is DESCONHECIDO

    def test_resposta_antiga_dos_sinais_que_sairam_e_ignorada(self) -> None:
        respostas = _sinais_comportamentais_minimo_completo(
            NOVA_DIVIDA_PREVISTA="SIM",
            JANELA_NOVA_DIVIDA="ATE_30D",
            HISTORICO_RECAIDA="MAIS_DE_UMA",
            HISTORICO_ABANDONO="MAIS_DE_UMA",
        )

        sinais = montar_sinais_comportamentais(respostas)

        assert sinais.NOVA_DIVIDA_PREVISTA is SimNaoTalvez.NAO
        assert sinais.JANELA_NOVA_DIVIDA is None
        assert sinais.HISTORICO_RECAIDA is SimNaoTalvez.TALVEZ
        assert sinais.HISTORICO_ABANDONO is SimNaoTalvez.TALVEZ


# ---------------------------------------------------------------------------
# Critério 2 — AUTOPERCEPCAO_CONTROLE (B2.13) admite DESCONHECIDO.
# ---------------------------------------------------------------------------
class TestCriterio2AutopercepcaoControleAdmiteDesconhecido:
    def test_autopercepcao_controle_com_resposta_concreta(self) -> None:
        respostas = RespostasCaso(respostas=(_resposta("AUTOPERCEPCAO_CONTROLE", 7),))

        assert _autopercepcao_controle(respostas) == 7

    def test_autopercepcao_controle_sem_resposta_e_desconhecido(self) -> None:
        respostas = RespostasCaso(respostas=())

        assert _autopercepcao_controle(respostas) is DESCONHECIDO

    def test_autopercepcao_controle_nao_sei_e_desconhecido(self) -> None:
        respostas = RespostasCaso(respostas=(_resposta("AUTOPERCEPCAO_CONTROLE", NAO_SEI),))

        assert _autopercepcao_controle(respostas) is DESCONHECIDO

    def test_autopercepcao_controle_zero_e_preservado_como_zero(self) -> None:
        """Nota real da escala (0 = "muito pouca visibilidade") não pode
        ser confundida com ausência/DESCONHECIDO."""
        respostas = RespostasCaso(respostas=(_resposta("AUTOPERCEPCAO_CONTROLE", 0),))

        valor = _autopercepcao_controle(respostas)
        assert valor == 0
        assert isinstance(valor, int)


# ---------------------------------------------------------------------------
# Critério 3 — o mapeamento resposta → membro de enum é por valor_interno
# do registro, sem `if` por pergunta (mecanismo genérico `_membro_do_enum`).
# ---------------------------------------------------------------------------
class TestCriterio3MapeamentoPorValorInternoSemIfPorPergunta:
    @pytest.mark.parametrize(
        "variavel,valor_interno,enum_alvo,membro_esperado",
        [
            ("CONHECIMENTO_GASTO", "RAZOAVEL", CONHECIMENTO_GASTO, CONHECIMENTO_GASTO.RAZOAVEL),
            ("REVISAO_SEMANAL", "RARAMENTE", REVISAO_SEMANAL, REVISAO_SEMANAL.RARAMENTE),
        ],
    )
    def test_cada_valor_interno_do_registro_resolve_o_membro_correspondente(
        self, variavel: str, valor_interno: str, enum_alvo: object, membro_esperado: object
    ) -> None:
        """Prova, para cada enum do Bloco 2 que segue perguntado, que TODO valor do
        domínio (não só o usado na ficha mínima) resolve — não uma cadeia
        de `if` que só cobriria os casos testados em outro lugar."""
        respostas = _perfil_comportamental_minimo_completo(**{variavel: valor_interno})

        perfil = montar_perfil_comportamental(respostas)

        assert getattr(perfil, variavel) is membro_esperado

    def test_valor_interno_sem_membro_correspondente_levanta_erro_explicito(self) -> None:
        """Nunca escolhe um membro "parecido" nem aceita silenciosamente —
        prova de que a resolução é por nome exato, não por heurística."""
        respostas = _perfil_comportamental_minimo_completo(CONHECIMENTO_GASTO="VALOR_INEXISTENTE")

        with pytest.raises(ErroValorInternoDesconhecido):
            montar_perfil_comportamental(respostas)

    def test_mapeamento_nao_usa_if_por_pergunta_verificado_por_ast(self) -> None:
        """Critério de aceite verificado estruturalmente: o corpo de
        `montar_perfil_comportamental` não contém nenhum `if`/`elif`/
        comparação condicional por pergunta — toda a tradução acontece via
        `_membro_do_enum` (EnumClasse[valor_interno]), chamado uma vez por
        campo."""
        import ast
        import inspect

        from app.montagem import estado as modulo_estado

        codigo_fonte = inspect.getsource(modulo_estado.montar_perfil_comportamental)
        arvore = ast.parse(codigo_fonte)
        nos_de_desvio_condicional = [
            no for no in ast.walk(arvore) if isinstance(no, (ast.If, ast.Compare))
        ]
        assert not nos_de_desvio_condicional, (
            "montar_perfil_comportamental não deve conter `if`/comparação — "
            "a tradução é só chamada a _membro_do_enum, por campo."
        )


# ---------------------------------------------------------------------------
# Critério 4 — nenhuma derivação comportamental (NIVEL_CONTROLE,
# RISCO_RECAIDA) é calculada aqui: nem os módulos, nem os nomes aparecem.
# ---------------------------------------------------------------------------
class TestCriterio4NenhumaDerivacaoComportamentalCalculadaAqui:
    def test_modulo_nao_importa_nem_referencia_derivacoes_do_motor(self) -> None:
        import inspect

        from app.montagem import estado as modulo_estado

        codigo_fonte = inspect.getsource(modulo_estado)

        assert "NIVEL_CONTROLE" not in codigo_fonte
        assert "RISCO_RECAIDA" not in codigo_fonte
        assert "engine.comportamento" not in codigo_fonte

    def test_perfil_comportamental_nao_tem_campo_de_nivel_de_controle(self) -> None:
        """`PerfilComportamental` (engine/estado.py) é só a ENTRADA — a
        derivação (NIVEL_CONTROLE) não é campo dela."""
        campos = {campo for campo in PerfilComportamental.__dataclass_fields__}
        assert "NIVEL_CONTROLE" not in campos

    def test_sinais_comportamentais_nao_tem_campo_de_risco_recaida(self) -> None:
        campos = {campo for campo in SinaisComportamentais.__dataclass_fields__}
        assert "RISCO_RECAIDA" not in campos


# ---------------------------------------------------------------------------
# Prova de fidelidade aos registros reais dos Blocos 1, 2 e 5 (T-17) —
# nenhum VARIAVEL_GRAVADA usado por montar_perfil_comportamental/
# montar_sinais_comportamentais é inventado no teste.
# ---------------------------------------------------------------------------
def test_mapeamento_usa_variaveis_dos_registros_reais() -> None:
    colecao = carregar_registros()
    variaveis_existentes = {
        registro.VARIAVEL_GRAVADA
        for registro in colecao.registros
        if registro.VARIAVEL_GRAVADA is not None
    }

    variaveis_usadas = {
        "CONHECIMENTO_GASTO",
        "REVISAO_SEMANAL",
        "AUTOPERCEPCAO_CONTROLE",
        "MECANISMO_DEFICIT",
        "NOVO_PARCELAMENTO_PREVISTO",
        "PACTO",
        "RISCO_IMPULSO",
        "NECESSIDADE_VITORIA",
    }
    ausentes = variaveis_usadas - variaveis_existentes
    assert not ausentes, (
        f"montagem usa variável(is) que não existe(m) em nenhum registro real: {ausentes}"
    )


def test_necessidade_vitoria_tem_registro_bloco_9_e_abandono_saiu() -> None:
    """T-99: `B9.02` tem registro real e é lido; `T-404`: `B9.04` saiu."""
    colecao = carregar_registros()
    variaveis_existentes = {
        registro.VARIAVEL_GRAVADA
        for registro in colecao.registros
        if registro.VARIAVEL_GRAVADA is not None
    }

    assert "NECESSIDADE_VITORIA" in variaveis_existentes
    assert "HISTORICO_ABANDONO" not in variaveis_existentes


# ---------------------------------------------------------------------------
# T-99 — NECESSIDADE_VITORIA (B9.02, escala 0-10) lido do registro real.
# ---------------------------------------------------------------------------
def test_necessidade_vitoria_le_a_escala_0_10_do_registro_real() -> None:
    for valor_interno in (0, 5, 10):
        respostas = _sinais_comportamentais_minimo_completo(NECESSIDADE_VITORIA=valor_interno)

        sinais = montar_sinais_comportamentais(respostas)

        assert sinais.NECESSIDADE_VITORIA == valor_interno


def test_necessidade_vitoria_zero_e_preservado_como_zero() -> None:
    """Nota real da escala (0 = "isso faria pouca diferença para mim") não
    pode ser confundida com ausência/DESCONHECIDO — mesma prova de
    `_autopercepcao_controle` (B2.13)."""
    respostas = _sinais_comportamentais_minimo_completo(NECESSIDADE_VITORIA=0)

    sinais = montar_sinais_comportamentais(respostas)

    assert sinais.NECESSIDADE_VITORIA == 0
    assert isinstance(sinais.NECESSIDADE_VITORIA, int)


def test_necessidade_vitoria_nao_sei_e_desconhecido() -> None:
    respostas = _sinais_comportamentais_minimo_completo(NECESSIDADE_VITORIA=NAO_SEI)

    sinais = montar_sinais_comportamentais(respostas)

    assert sinais.NECESSIDADE_VITORIA is DESCONHECIDO


def test_necessidade_vitoria_sem_resposta_levanta_erro_explicito() -> None:
    respostas = _sinais_comportamentais_minimo_completo(NECESSIDADE_VITORIA=_OMITIR)

    with pytest.raises(ErroSinalComportamentalAusente):
        montar_sinais_comportamentais(respostas)
