"""Rotas da calculadora da dívida — `RF-518`, `RF-519`, `RF-524`, `RF-525`,
`RF-529`, `RF-530`, `AC-529`, `AC-530`, `EC-77` (`T-503` a `T-505`).

`POST /caso/{CASO_ID}/calculadora/previa` **não grava nada** (`PD-09`): o
servidor recalcula tudo a cada chamada e o front só exibe. Erro de negócio
(entrada recusada, cálculo sem resultado) é `200` com `estado: ERRO` e
`valores` vazio, para a tela apagar o resultado antigo (`RF-519`, `AC-529`).
O resumo (prazo, 1ª parcela, último pagamento, total de juros) existe só aqui
(`RF-529`).

`POST /caso/{CASO_ID}/divida/{item_id}/calculadora/confirmar` valida tudo
antes de gravar e grava a marca `CONFERENCIA_DA_DIVIDA` por último: falha no
meio deixa a pergunta composta aberta e a confirmação é idempotente (plano,
5.2). O que o aluno digitou é gravado como digitou; desconhecido, ou campo
escolhido para recalcular, grava `NAO_SEI`, nunca `0`. O valor calculado
**não** é gravado: é derivado a cada leitura por `resolver_divida` (`PD-06`).

Hipótese declarada: `INFORMACAO_A_RECALCULAR` leva a impressão dos valores
**como ficam gravados** (campo escolhido já `NAO_SEI`), a mesma que
`resolver_divida` recalcula ao ler; assim mudar qualquer valor depois
invalida a escolha (`EC-70`).

Textos ao aluno vêm de `app/montagem/textos/calculadora.yaml` (`AC-37`).

REGRAS: `RF-518`, `RF-519`, `RF-520`, `RF-523`, `RF-524`, `RF-525`, `RF-529`,
`RF-530`, `AC-529`, `AC-530`, `EC-77`
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Annotated, Any, Final, Literal

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.casos.maquina import ErroConsentimentoNaoRegistrado
from app.http.edicao import exigir_coleta_editavel
from app.http.isolamento import exigir_caso_da_sessao, obter_repositorio_casos
from app.http.rotas_coleta import (
    _MENSAGEM_FALHA_SALVAR,
    _agora,
    _itens_e_rotulos,
    _resposta_de_erro,
    _serializar_proxima,
    obter_colecao_de_registros,
    obter_repositorio_itens,
    obter_repositorio_respostas,
)
from app.montagem.calculo_divida import (
    CAMPO_DA_DIVIDA,
    CODIGO_ERRO_DE_CALCULO,
    COMPATIBILIDADE,
    EntradaDaDivida,
    ErroDeCalculo,
    ErroDeEntrada,
    calcular_parcela,
    calcular_prazo,
    calcular_saldo,
    calcular_taxa,
    conferir_compatibilidade,
    cronograma,
    taxa_na_periodicidade,
    total_de_juros,
    validar_entrada,
)
from app.montagem.cenario_conservador import escolher_hipotese
from app.montagem.conversao import converter_para_taxa
from app.montagem.entrada import avisos_da_gravacao
from app.montagem.premissas import (
    _SEM_ESCOLHA,
    _VARIAVEL_DO_CAMPO,
    _VARIAVEL_ESCOLHA,
    _VARIAVEL_PERIODICIDADE,
    _VARIAVEL_SISTEMA,
    MARCA_DO_VALOR,
    PRAZO_BASE_ESTIMATIVA_MESES,
    impressao_dos_valores,
)
from collection.carga import ColecaoDeRegistros
from collection.registro import EscopoRepeticao
from collection.respostas import NAO_SEI, Resposta, RespostasCaso, ValorResposta
from engine.tipos import SISTEMA_AMORTIZACAO, Dinheiro, Taxa
from persistencia.app_aluno.casos import RepositorioCasos
from persistencia.app_aluno.itens import RepositorioItens
from persistencia.app_aluno.respostas import (
    ErroCasoInexistenteParaResposta,
    ErroGravacaoResposta,
    RepositorioRespostas,
)
from report.plano import formatar_dinheiro_br, formatar_taxa_br

REGRAS: Final[tuple[str, ...]] = ("RF-518", "RF-519", "RF-524", "RF-525", "RF-529", "RF-530")

roteador = APIRouter(prefix="/caso", tags=["calculadora"])

CAMINHO_TEXTOS_CALCULADORA: Final[Path] = (
    Path(__file__).parent.parent / "montagem" / "textos" / "calculadora.yaml"
)

_LOGGER: Final[logging.Logger] = logging.getLogger("app.http.rotas_calculadora")

# Mensagens curtas de propósito (`AC-37`, limiar de 40 caracteres).
_MENSAGEM_CORPO_INVALIDO: Final[str] = "Corpo da requisição inválido."
_MENSAGEM_DIVIDA_INEXISTENTE: Final[str] = "Dívida não encontrada neste caso."
_MENSAGEM_FALHA_INTERNA: Final[str] = "Não foi possível calcular."

# Em duas partes: o literal inteiro passaria do limiar de `AC-37` (40 caracteres).
_ROTA_CONFIRMAR: Final[str] = "/{CASO_ID}/divida/{item_id}" + "/calculadora/confirmar"
_ID_DA_PERGUNTA: Final[str] = "B5.CALC01"
_VARIAVEL_MARCA: Final[str] = "CONFERENCIA_DA_DIVIDA"
_CONFIRMADA: Final[str] = "CONFIRMADA"
_PERIODICIDADE_DESCONHECIDA: Final[str] = "DESCONHECIDA"  # opção "Não sei a taxa" de `B5.D06`

# Evento de observabilidade por falha (`T-505`, `PD-15`): sem dado do aluno.
_EVENTO_DO_ERRO: Final[dict[CODIGO_ERRO_DE_CALCULO, str]] = {
    CODIGO_ERRO_DE_CALCULO.SEM_CONVERGENCIA: "CALCULADORA_SEM_CONVERGENCIA",
    CODIGO_ERRO_DE_CALCULO.TAXA_ACIMA_DO_TETO: "CALCULADORA_TETO_DE_TAXA",
    CODIGO_ERRO_DE_CALCULO.NAO_REDUZ_SALDO: "CALCULADORA_NAO_REDUZ_SALDO",
}

_ORDEM: Final[tuple[CAMPO_DA_DIVIDA, ...]] = (
    CAMPO_DA_DIVIDA.SALDO,
    CAMPO_DA_DIVIDA.PARCELA,
    CAMPO_DA_DIVIDA.TAXA,
    CAMPO_DA_DIVIDA.PRAZO,
)

type _Valor = Dinheiro | Taxa | int


_TAMANHO_MAXIMO_DO_TEXTO = 64  # `OQ-95`: texto maior que isso é corpo inválido (400)


class CorpoDaCalculadora(BaseModel):
    """`null`/`""` = desconhecido. Texto na grafia brasileira (`RF-530`)."""

    model_config = ConfigDict(extra="forbid")

    sistema: Literal["PRICE", "SAC"]
    periodicidade: Literal["MENSAL", "ANUAL"]
    saldo: str | None = Field(default=None, max_length=_TAMANHO_MAXIMO_DO_TEXTO)
    parcela: str | None = Field(default=None, max_length=_TAMANHO_MAXIMO_DO_TEXTO)
    taxa: str | None = Field(default=None, max_length=_TAMANHO_MAXIMO_DO_TEXTO)
    prazo: str | None = Field(default=None, max_length=_TAMANHO_MAXIMO_DO_TEXTO)
    recalcular: Literal["SALDO", "PARCELA", "TAXA", "PRAZO"] | None = None


async def _ler_corpo(request: Request) -> CorpoDaCalculadora:
    """`400` para corpo que não é JSON ou não tem a forma do contrato."""
    try:
        return CorpoDaCalculadora.model_validate(await request.json())
    except (ValueError, ValidationError) as erro:
        raise HTTPException(status_code=400, detail=_MENSAGEM_CORPO_INVALIDO) from erro


@cache
def _textos() -> dict[str, dict[str, str]]:
    with CAMINHO_TEXTOS_CALCULADORA.open(encoding="utf-8") as arquivo:
        return {str(k): dict(v) for k, v in yaml.safe_load(arquivo).items()}


@dataclass(frozen=True, slots=True)
class _Avaliacao:
    resposta: dict[str, Any]
    erro: str | None  # mensagem quando `estado == ERRO`
    entrada: EntradaDaDivida | None  # a validada, como digitada (taxa mensal)
    escolhido: CAMPO_DA_DIVIDA | None  # recálculo aplicado (`RF-525`)


# --- Formatação (o servidor formata; o front não faz conta) ---------------------------


def _texto_e_entrada(
    campo: CAMPO_DA_DIVIDA, valor: _Valor, periodicidade: Literal["MENSAL", "ANUAL"]
) -> tuple[str, str]:
    if campo is CAMPO_DA_DIVIDA.PRAZO:
        return str(valor), str(valor)
    assert isinstance(valor, Decimal)
    if campo is CAMPO_DA_DIVIDA.TAXA:
        # `formatar_taxa_br` escreve sempre "a.m."; a periodicidade é a do aluno.
        percentual = formatar_taxa_br(valor).removesuffix(" a.m.")
        unidade = " a.a." if periodicidade == "ANUAL" else " a.m."
        return percentual + unidade, percentual.removesuffix("%")
    texto = formatar_dinheiro_br(valor)
    return texto, texto.removeprefix("R$ ")


def _valor_calculado(
    campo: CAMPO_DA_DIVIDA,
    valor: _Valor,
    marca: MARCA_DO_VALOR,
    periodicidade: Literal["MENSAL", "ANUAL"],
) -> dict[str, str]:
    texto, entrada = _texto_e_entrada(campo, valor, periodicidade)
    return {
        "texto": texto,
        "entrada": entrada,
        "marca": marca.value,
        "rotulo": _textos()["marcas"][marca.value],
    }


def _resposta(
    estado: str,
    *,
    campo_calculado: CAMPO_DA_DIVIDA | None = None,
    valores: dict[str, dict[str, str]] | None = None,
    teorico: dict[str, str] | None = None,
    alternativas: tuple[CAMPO_DA_DIVIDA, ...] = (),
    resumo: dict[str, Any] | None = None,
    erros: list[dict[str, str]] | None = None,
    mensagem: str | None = None,
    parcela_estimada: dict[str, str] | None = None,
    hipotese_conservadora: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "estado": estado,
        "campo_calculado": campo_calculado.value if campo_calculado else None,
        "valores": valores or {},
        "teorico": teorico,
        "alternativas": [campo.value for campo in alternativas],
        "resumo": resumo,
        "parcela_estimada": parcela_estimada,
        "hipotese_conservadora": hipotese_conservadora,
        "erros": erros or [],
        "mensagem": mensagem if mensagem is not None else _textos()["estados"].get(estado),
    }


def _registrar_evento(codigo: CODIGO_ERRO_DE_CALCULO) -> None:
    evento = _EVENTO_DO_ERRO.get(codigo)
    if evento is not None:
        _LOGGER.warning(evento, extra={"evento": evento})  # `PD-15`: nenhum dado do aluno


# --- Avaliação (prévia e confirmação usam a mesma) -------------------------------------


def _d(valor: _Valor | None) -> Decimal:
    assert isinstance(valor, Decimal)
    return valor


def _n(valor: _Valor | None) -> int:
    assert isinstance(valor, int)
    return valor


def _calcular(
    campo: CAMPO_DA_DIVIDA,
    internos: dict[CAMPO_DA_DIVIDA, _Valor | None],
    sistema: SISTEMA_AMORTIZACAO,
    periodicidade: Literal["MENSAL", "ANUAL"],
) -> tuple[_Valor, _Valor]:
    """O campo desconhecido a partir dos outros três: `(exibição, interno)`.
    Só a taxa difere (exibida na periodicidade do aluno, interna mensal)."""
    saldo, parcela = internos[CAMPO_DA_DIVIDA.SALDO], internos[CAMPO_DA_DIVIDA.PARCELA]
    mensal, prazo = internos[CAMPO_DA_DIVIDA.TAXA], internos[CAMPO_DA_DIVIDA.PRAZO]
    if campo is CAMPO_DA_DIVIDA.SALDO:
        valor: _Valor = calcular_saldo(_d(parcela), _d(mensal), _n(prazo), sistema)
    elif campo is CAMPO_DA_DIVIDA.PARCELA:
        valor = calcular_parcela(_d(saldo), _d(mensal), _n(prazo), sistema)
    elif campo is CAMPO_DA_DIVIDA.PRAZO:
        valor = calcular_prazo(_d(saldo), _d(parcela), _d(mensal), sistema)
    else:
        valor = calcular_taxa(_d(saldo), _d(parcela), _n(prazo), sistema)
        return taxa_na_periodicidade(valor, periodicidade), valor
    return valor, valor


def _erro_de_calculo(erro: ErroDeCalculo) -> _Avaliacao:
    _registrar_evento(erro.codigo)
    mensagem = _textos()["erros_de_calculo"][erro.codigo.value]
    return _Avaliacao(_resposta("ERRO", mensagem=mensagem), mensagem, None, None)


def _parcela_estimada(
    internos: dict[CAMPO_DA_DIVIDA, _Valor | None],
    desconhecidos: list[CAMPO_DA_DIVIDA],
    sistema: SISTEMA_AMORTIZACAO,
) -> dict[str, str] | None:
    """`RF-532`, `RF-533`: saldo e taxa conhecidos, sem parcela e sem prazo ⇒ a
    parcela de 24 meses, em linha à parte e marcada (nunca no campo digitado).
    Com prazo ou pagamento informado nada é estimado e o texto não cita 24
    meses (`RF-536`)."""
    if desconhecidos != [CAMPO_DA_DIVIDA.PARCELA, CAMPO_DA_DIVIDA.PRAZO]:
        return None
    try:
        valor = calcular_parcela(
            _d(internos[CAMPO_DA_DIVIDA.SALDO]),
            _d(internos[CAMPO_DA_DIVIDA.TAXA]),
            PRAZO_BASE_ESTIMATIVA_MESES,
            sistema,
        )
    except ErroDeCalculo:
        return None
    textos = _textos()
    return {
        "texto": formatar_dinheiro_br(valor),
        "marca": MARCA_DO_VALOR.ESTIMADO.value,
        "rotulo": textos["marcas"][MARCA_DO_VALOR.ESTIMADO.value],
        "hipotese": textos["estimativa"]["hipotese_24_meses"],
    }


def _hipotese_conservadora(
    entrada: EntradaDaDivida, periodicidade: Literal["MENSAL", "ANUAL"]
) -> dict[str, str] | None:
    """`RF-538`, `RF-539`: valores incompatíveis e nenhum recálculo escolhido ⇒ o
    saldo e a taxa que o plano usará, marcados `hipótese`. Parcela e prazo da
    hipótese não aparecem: não governam o plano."""
    if (
        entrada.saldo is None
        or entrada.parcela is None
        or entrada.taxa_mensal is None
        or entrada.prazo is None
    ):
        return None
    hipotese = escolher_hipotese(
        entrada.saldo,
        entrada.parcela,
        entrada.taxa_mensal,
        entrada.prazo,
        entrada.sistema,
    )
    if hipotese is None:
        return None
    textos = _textos()
    return {
        "saldo": _texto_e_entrada(CAMPO_DA_DIVIDA.SALDO, hipotese.saldo, periodicidade)[0],
        "taxa": _texto_e_entrada(
            CAMPO_DA_DIVIDA.TAXA,
            taxa_na_periodicidade(hipotese.taxa_mensal, periodicidade),
            periodicidade,
        )[0],
        "marca": MARCA_DO_VALOR.HIPOTESE.value,
        "rotulo": textos["marcas"][MARCA_DO_VALOR.HIPOTESE.value],
        "aviso": textos["conservadora"]["aviso"],
    }


def _taxa_digitada(corpo: CorpoDaCalculadora, entrada: EntradaDaDivida) -> Taxa | None:
    if entrada.taxa_mensal is None or corpo.taxa is None:
        return None
    return converter_para_taxa(corpo.taxa)


def _avaliar(corpo: CorpoDaCalculadora) -> _Avaliacao:
    """Tabela-verdade do plano (4.4) aplicada ao que foi enviado. Nenhuma
    etapa grava; erro devolve `valores` vazio (`RF-519`)."""
    periodicidade = corpo.periodicidade
    sistema = SISTEMA_AMORTIZACAO[corpo.sistema]
    try:
        entrada = validar_entrada(
            corpo.saldo,
            corpo.parcela,
            corpo.taxa,
            corpo.prazo,
            periodicidade=periodicidade,
            sistema=sistema,
        )
    except ErroDeEntrada as erro:
        mensagem = _textos()["erros_de_entrada"][erro.codigo.value]
        detalhe = {"campo": erro.campo.value, "codigo": erro.codigo.value, "mensagem": mensagem}
        return _Avaliacao(_resposta("ERRO", erros=[detalhe]), mensagem, None, None)

    # A taxa que o aluno vê é a digitada na periodicidade dele; a que entra
    # na conta é a mensal normalizada.
    taxa_digitada = _taxa_digitada(corpo, entrada)
    internos: dict[CAMPO_DA_DIVIDA, _Valor | None] = {
        CAMPO_DA_DIVIDA.SALDO: entrada.saldo,
        CAMPO_DA_DIVIDA.PARCELA: entrada.parcela,
        CAMPO_DA_DIVIDA.TAXA: entrada.taxa_mensal,
        CAMPO_DA_DIVIDA.PRAZO: entrada.prazo,
    }
    exibicao: dict[CAMPO_DA_DIVIDA, _Valor | None] = {
        **internos,
        CAMPO_DA_DIVIDA.TAXA: taxa_digitada,
    }
    desconhecidos = [campo for campo in _ORDEM if internos[campo] is None]
    escolhido: CAMPO_DA_DIVIDA | None = None

    def valores(calculado: CAMPO_DA_DIVIDA | None) -> dict[str, dict[str, str]]:
        return {
            campo.value: _valor_calculado(
                campo,
                v,
                MARCA_DO_VALOR.CALCULADO if campo is calculado else MARCA_DO_VALOR.INFORMADO,
                periodicidade,
            )
            for campo, v in exibicao.items()
            if v is not None
        }

    if not desconhecidos:
        assert taxa_digitada is not None
        compatibilidade, teorica = conferir_compatibilidade(entrada, taxa_digitada, periodicidade)
        if compatibilidade is COMPATIBILIDADE.INCOMPATIVEL:
            if corpo.recalcular is None:
                texto, _ = _texto_e_entrada(CAMPO_DA_DIVIDA.PARCELA, teorica, periodicidade)
                teorico = {"campo": CAMPO_DA_DIVIDA.PARCELA.value, "texto": texto}
                resposta = _resposta(
                    "INCOMPATIVEL",
                    valores=valores(None),
                    teorico=teorico,
                    alternativas=_ORDEM,
                    hipotese_conservadora=_hipotese_conservadora(entrada, periodicidade),
                )
                return _Avaliacao(resposta, None, entrada, None)
            escolhido = CAMPO_DA_DIVIDA[corpo.recalcular]  # `RF-525`
            internos[escolhido] = exibicao[escolhido] = None
            desconhecidos = [escolhido]

    if len(desconhecidos) > 1:
        estado = "SEM_CALCULO" if len(desconhecidos) == len(_ORDEM) else "PENDENTE"
        estimada = _parcela_estimada(internos, desconhecidos, sistema)
        resposta = _resposta(estado, valores=valores(None), parcela_estimada=estimada)
        return _Avaliacao(resposta, None, entrada, None)

    calculado = desconhecidos[0] if desconhecidos else None
    if calculado is not None:
        try:
            exibicao[calculado], internos[calculado] = _calcular(
                calculado, internos, sistema, periodicidade
            )
        except ErroDeCalculo as erro:
            return _erro_de_calculo(erro)

    try:
        linhas = cronograma(
            _d(internos[CAMPO_DA_DIVIDA.SALDO]),
            _d(internos[CAMPO_DA_DIVIDA.PARCELA]),
            _d(internos[CAMPO_DA_DIVIDA.TAXA]),
            _n(internos[CAMPO_DA_DIVIDA.PRAZO]),
            sistema,
        )
    except ErroDeCalculo as erro:
        return _erro_de_calculo(erro)
    resumo = {
        "prazo": len(linhas),
        "primeira_parcela": formatar_dinheiro_br(linhas[0].pagamento),
        "ultimo_pagamento": formatar_dinheiro_br(linhas[-1].pagamento),
        "total_de_juros": formatar_dinheiro_br(total_de_juros(linhas)),
    }
    resposta = _resposta(
        "CALCULADO" if calculado is not None else "CONFERIDO",
        campo_calculado=calculado,
        valores=valores(calculado),
        resumo=resumo,
    )
    return _Avaliacao(resposta, None, entrada, escolhido)


# --- Rotas -------------------------------------------------------------------------------


@roteador.post("/{CASO_ID}/calculadora/previa")
def previa_da_calculadora(
    CASO_ID: Annotated[str, Depends(exigir_caso_da_sessao("CASO_ID"))],
    corpo: Annotated[CorpoDaCalculadora, Depends(_ler_corpo)],
) -> JSONResponse:
    """`RF-519`, `AC-529`, `EC-77`: sem estado e sem gravação (`PD-09`)."""
    try:
        avaliacao = _avaliar(corpo)
    except Exception:  # noqa: BLE001 — `EC-77`: falha interna vira 503, sem dado no log
        _LOGGER.error("calculadora: falha interna")
        return JSONResponse({"erro": _MENSAGEM_FALHA_INTERNA}, status_code=503)
    return JSONResponse(avaliacao.resposta)


@roteador.post(_ROTA_CONFIRMAR)
def confirmar_calculadora(
    item_id: str,
    request: Request,
    CASO_ID: Annotated[str, Depends(exigir_caso_da_sessao("CASO_ID"))],
    corpo: Annotated[CorpoDaCalculadora, Depends(_ler_corpo)],
    colecao: Annotated[ColecaoDeRegistros, Depends(obter_colecao_de_registros)],
    repositorio: Annotated[RepositorioRespostas, Depends(obter_repositorio_respostas)],
    repositorio_itens: Annotated[RepositorioItens, Depends(obter_repositorio_itens)],
    repositorio_casos: Annotated[RepositorioCasos, Depends(obter_repositorio_casos)],
) -> JSONResponse:
    """`RF-518`, `RF-520`, `RF-525`, `AC-530`: valida tudo, depois grava;
    `CONFERENCIA_DA_DIVIDA` é a última escrita."""
    exigir_coleta_editavel(CASO_ID, repositorio_casos)  # `RF-114`
    itens = repositorio_itens.listar_do_caso(CASO_ID, incluir_removidos=False)
    if not any(i.item_id == item_id and i.escopo is EscopoRepeticao.DIVIDA_ID for i in itens):
        return _resposta_de_erro(request, _MENSAGEM_DIVIDA_INEXISTENTE, 404)

    try:
        avaliacao = _avaliar(corpo)
    except Exception:  # noqa: BLE001 — `EC-77`
        _LOGGER.error("calculadora: falha interna")
        return _resposta_de_erro(request, _MENSAGEM_FALHA_INTERNA, 503)
    if avaliacao.resposta["estado"] == "ERRO":
        # `RF-518`/`RF-519`: nada é gravado.
        corpo_do_erro = {"erro": avaliacao.erro, "erros": avaliacao.resposta["erros"]}
        return JSONResponse(corpo_do_erro, status_code=422)

    assert avaliacao.entrada is not None
    gravar = _gravacao(corpo, avaliacao.entrada, avaliacao.escolhido)
    versao = colecao.QUESTIONARIO_VERSION
    try:
        for variavel, valor in (*gravar, (_VARIAVEL_MARCA, _CONFIRMADA)):
            repositorio.gravar(
                Resposta(
                    CASO_ID=CASO_ID,
                    ID_PERGUNTA=variavel,
                    item_id=item_id,
                    valor=valor,
                    QUESTIONARIO_VERSION=versao,
                    respondida_em=_agora(),
                )
            )
    except ErroConsentimentoNaoRegistrado:
        return _resposta_de_erro(request, _MENSAGEM_FALHA_SALVAR, 400)
    except (ErroGravacaoResposta, ErroCasoInexistenteParaResposta):
        return _resposta_de_erro(request, _MENSAGEM_FALHA_SALVAR, 503)

    respostas = RespostasCaso(respostas=repositorio.listar_do_caso(CASO_ID))
    itens_por_escopo, rotulos = _itens_e_rotulos(repositorio_itens, CASO_ID, colecao)
    avisos = {
        a.codigo: a
        for variavel in (
            _VARIAVEL_DO_CAMPO[CAMPO_DA_DIVIDA.SALDO],
            _VARIAVEL_DO_CAMPO[CAMPO_DA_DIVIDA.PARCELA],
        )
        for a in avisos_da_gravacao(variavel, item_id, respostas)
    }
    return JSONResponse(
        {
            "ID_PERGUNTA": _ID_DA_PERGUNTA,
            "proxima": _serializar_proxima(CASO_ID, colecao, respostas, itens_por_escopo, rotulos),
            "avisos": [
                {"codigo": a.codigo, "mensagem": a.mensagem, "ID_PERGUNTA": _ID_DA_PERGUNTA}
                for a in avisos.values()
            ],
        }
    )


def _gravacao(
    corpo: CorpoDaCalculadora, entrada: EntradaDaDivida, escolhido: CAMPO_DA_DIVIDA | None
) -> tuple[tuple[str, ValorResposta], ...]:
    """O que vai para `respostas`, já validado por `_avaliar`. Digitado fica
    como digitado (`AC-530`); desconhecido ou escolhido para recalcular vira
    `NAO_SEI`. A impressão da escolha é a dos valores como ficam gravados."""
    taxa_digitada = _taxa_digitada(corpo, entrada)
    digitados: dict[CAMPO_DA_DIVIDA, ValorResposta] = {
        CAMPO_DA_DIVIDA.SALDO: entrada.saldo if entrada.saldo is not None else NAO_SEI,
        CAMPO_DA_DIVIDA.PARCELA: entrada.parcela if entrada.parcela is not None else NAO_SEI,
        CAMPO_DA_DIVIDA.TAXA: taxa_digitada if taxa_digitada is not None else NAO_SEI,
        CAMPO_DA_DIVIDA.PRAZO: entrada.prazo if entrada.prazo is not None else NAO_SEI,
    }
    if escolhido is not None:
        digitados[escolhido] = NAO_SEI
    taxa_desconhecida = digitados[CAMPO_DA_DIVIDA.TAXA] is NAO_SEI
    periodicidade = _PERIODICIDADE_DESCONHECIDA if taxa_desconhecida else corpo.periodicidade
    escolha = _SEM_ESCOLHA
    if escolhido is not None:
        impressao = impressao_dos_valores(
            digitados[CAMPO_DA_DIVIDA.SALDO],
            digitados[CAMPO_DA_DIVIDA.PARCELA],
            digitados[CAMPO_DA_DIVIDA.TAXA],
            digitados[CAMPO_DA_DIVIDA.PRAZO],
            entrada.sistema,
            periodicidade,
        )
        escolha = f"{escolhido.value}|{impressao}"
    return (
        (_VARIAVEL_DO_CAMPO[CAMPO_DA_DIVIDA.SALDO], digitados[CAMPO_DA_DIVIDA.SALDO]),
        (_VARIAVEL_DO_CAMPO[CAMPO_DA_DIVIDA.PARCELA], digitados[CAMPO_DA_DIVIDA.PARCELA]),
        (_VARIAVEL_PERIODICIDADE, periodicidade),
        (_VARIAVEL_DO_CAMPO[CAMPO_DA_DIVIDA.TAXA], digitados[CAMPO_DA_DIVIDA.TAXA]),
        (_VARIAVEL_DO_CAMPO[CAMPO_DA_DIVIDA.PRAZO], digitados[CAMPO_DA_DIVIDA.PRAZO]),
        (_VARIAVEL_SISTEMA, corpo.sistema),
        (_VARIAVEL_ESCOLHA, escolha),
    )
