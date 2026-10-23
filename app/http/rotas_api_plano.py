"""API JSON do plano, da fila de revisão e do painel — `RF-50`, `RF-51`
(T-140).

As telas do plano, do revisor e do operador passam a ser React. Estas rotas
entregam os MESMOS campos que os templates Jinja2 recebiam — nem um a mais.

**O PDF continua em Jinja2, e isso é deliberado.** `report/pdf.py` renderiza
`report/templates/plano/plano.html` para gerar o PDF, e `RF-21`/`AC-14`
exigem que a redação canônica de `Q-03` exista em UM lugar só. Aquele
template deixa de servir navegador, mas continua sendo a fonte do PDF —
apagá-lo criaria uma segunda cópia do texto normativo.

**Mesmas guardas de sempre, nenhuma nova.** Plano: só o snapshot LIBERADO
(`snapshot_tem_liberacao_registrada`, a mesma de `gerar_html_do_plano_
liberado`). Revisão e painel: `exigir_papel_revisor` — `401` sem sessão,
`403` para conta que não é revisora, nunca `404` (a existência da tela do
revisor não é segredo).

REGRAS: `RF-50`, `RF-51`, `AC-25`, `AC-28`
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Any, Final, Literal, Protocol

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from app.casos.inventario import pendencias_de_inventario
from app.casos.maquina import ESTADO_CASO
from app.casos.progresso import RelatoDeProgresso, consultar_trilha_de_progresso
from app.concorrencia import duas_em_paralelo, tres_em_paralelo
from app.http.fatos_de_risco import fatos_de_risco_por_divida
from app.http.isolamento import (
    exigir_caso_da_sessao,
    exigir_papel_revisor,
    obter_repositorio_casos,
)
from app.http.jornada import parte_da_pergunta
from app.http.mensagens_de_estado import mensagem_do_estado_do_caso
from app.http.mudancas_do_plano import mudancas_entre
from app.http.rotas_coleta import _itens_por_escopo
from app.http.rotas_coleta import obter_colecao_de_registros as obter_colecao_da_coleta
from app.http.rotas_coleta import obter_repositorio_itens as obter_repositorio_itens_da_coleta
from app.http.rotas_coleta import (
    obter_repositorio_respostas as obter_repositorio_respostas_da_coleta,
)
from app.http.rotas_operador import (
    CasosDoPainel,
    ItensDoPainel,
    RespostasDoPainel,
    _relato_para_linha,
    agrupar_itens_por_escopo,
    obter_colecao_de_registros_do_painel,
    obter_repositorio_casos_do_painel,
    obter_repositorio_itens_do_painel,
    obter_repositorio_respostas_do_painel,
)
from app.http.rotas_plano import (
    ContasDosCasos,
    nome_do_dono_do_caso,
    obter_contas_dos_casos,
    obter_repositorio_snapshots,
)
from app.http.rotas_revisao import (
    obter_repositorio_casos_da_fila,
    obter_repositorio_snapshots_da_fila,
)
from app.http.serializacao_plano import (
    fontes_por_divida,
    serializar_estado_inputs,
    serializar_item_da_fila,
    serializar_linha_de_caso,
    serializar_opcoes_da_lista,
    serializar_plano,
    vocabulario_do_caso,
)
from app.revisao.comprovacao import niveis_por_ficha
from app.revisao.fila import (
    RepositorioCasosDaFila,
    listar_fila_de_revisao,
    montar_item_da_fila,
)
from app.revisao.lista_de_casos import (
    CAMPO_DE_ORDEM,
    FiltrosDaLista,
    RepositorioEventosDaLista,
    RepositorioRevisoesDaLista,
    consultar_casos,
    montar_linhas,
)
from collection.carga import ColecaoDeRegistros
from collection.respostas import RespostasCaso
from engine.portas import RepositorioSnapshots
from engine.snapshot import SnapshotOrdem
from persistencia.app_aluno.casos import RepositorioCasos
from persistencia.app_aluno.contas import (
    ContaDoCaso,
    RepositorioContasSupabase,
    listar_revisores,
)
from persistencia.app_aluno.eventos import RepositorioEventosCasoSupabase
from persistencia.app_aluno.itens import RepositorioItens
from persistencia.app_aluno.respostas import RepositorioRespostas
from persistencia.app_aluno.revisoes import RepositorioRevisoesSupabase
from persistencia.supabase.repositorio_snapshots import ErroSnapshotNaoEncontrado
from app.casos.liberacao import data_da_liberacao
from report.pdf import gerar_pdf_de_previa, snapshot_tem_liberacao_registrada
from report.plano import (
    TextosCanonicosPlano,
    VocabularioDoCaso,
    carregar_textos_canonicos,
    formatar_dinheiro_br,
    montar_contexto_estado_inputs,
    montar_contexto_plano,
    rotulo_de_codigo,
)

REGRAS: Final[tuple[str, ...]] = ("RF-50", "RF-51", "AC-25", "AC-28")

roteador = APIRouter(tags=["api-plano"])


def _bloco_deficitario(snapshot: Any) -> dict[str, object] | None:
    """`RF-452` (`T-438`) — o que o revisor confere num aluno deficitário, só
    leitura do snapshot já formatada: déficit, o "se nada mudar" do motor e as
    simulações de 5% e 10%. `None` fora do déficit. Déficit não é pendência."""
    diagnostico = snapshot.diagnostico
    if not diagnostico.MODO_ESTABILIZACAO:
        return None
    sem = snapshot.prognostico.sem_acao if snapshot.prognostico is not None else None
    return {
        "resultado_mensal": formatar_dinheiro_br(diagnostico.RESULTADO_MENSAL_ATUAL),
        "deficit": formatar_dinheiro_br(diagnostico.DEFICIT_MENSAL),
        "se_nada_mudar": None
        if sem is None
        else {
            "horizonte_meses": sem.HORIZONTE_MESES,
            "saldo_inicial": formatar_dinheiro_br(sem.SALDO_INICIAL_TOTAL),
            "saldo_no_horizonte": formatar_dinheiro_br(sem.SALDO_NO_HORIZONTE),
            "dividas_que_crescem": sem.DIVIDAS_QUE_CRESCEM,
        },
        "cenarios": None
        if snapshot.cenarios_economia is None
        else [
            {
                "percentual": f"{int(c.PERCENTUAL * 100)}%",
                "economia_mensal": formatar_dinheiro_br(c.ECONOMIA_MENSAL),
                "resultado_ajustado": formatar_dinheiro_br(c.RESULTADO_AJUSTADO),
                "situacao": c.SITUACAO,
                "executavel": c.EXECUTAVEL,
                "capacidade_de_aporte": formatar_dinheiro_br(c.CAPACIDADE_ATAQUE_ATUAL),
                "metodo": c.METODO,
                "prazo_meses": c.PRAZO_TOTAL,
                "custo_futuro_total": None
                if c.CUSTO_FUTURO_TOTAL is None
                else formatar_dinheiro_br(c.CUSTO_FUTURO_TOTAL),
                "estourou_horizonte": c.ESTOUROU_HORIZONTE,
                "saldos": [
                    {"mes": mes, "saldo": formatar_dinheiro_br(saldo)}
                    for mes, saldo in c.SALDOS_NOS_HORIZONTES
                ],
            }
            for c in snapshot.cenarios_economia
        ],
    }


def _resumo_do_caso(snapshot: Any) -> dict[str, object]:
    saldos = [d.SALDO_DEVEDOR_ATUAL for d in snapshot.estado_inputs.dividas]
    informados = [v for v in saldos if isinstance(v, Decimal)]
    return {
        "total_em_dividas": formatar_dinheiro_br(sum(informados, Decimal(0))) if informados else None,
        "total_em_dividas_parcial": len(informados) < len(saldos),
        # `RF-443`: saídas do mês = despesas + não mensais + parcelas devidas das
        # dívidas, as mesmas parcelas que o motor desconta em `RESULTADO_MENSAL_ATUAL`
        # (o "Resultado do mês" do plano). Renda − saídas = esse resultado.
        "pagamento_das_dividas": formatar_dinheiro_br(
            snapshot.diagnostico.PAGAMENTOS_MENSAIS_DEVIDOS_VIGENTES
        ),
        "saidas_totais": formatar_dinheiro_br(
            snapshot.estado_inputs.DESPESAS_OPERACIONAIS_ATUAIS
            + snapshot.estado_inputs.DESPESAS_NAO_MENSAIS_NORMALIZADAS
            + snapshot.diagnostico.PAGAMENTOS_MENSAIS_DEVIDOS_VIGENTES
        ),
    }

# A rota de prévia fica sob a raiz da conferência (nome curto: limiar de `AC-37`).
_RAIZ_DA_CONFERENCIA: Final[str] = "/revisao/caso/{CASO_ID_REVISAO}"

# Mensagens curtas de propósito — limiar de `AC-37` (T-08).
_MENSAGEM_SEM_PLANO: Final[str] = "Nenhum plano liberado ainda."


class ErroCasoDesaparecidoAposIsolamento(Exception):
    """Defensivo: `exigir_caso_da_sessao` já garantiu que o caso existe."""

    def __init__(self, caso_id: str) -> None:
        super().__init__(f"CASO_ID={caso_id!r} desapareceu após isolamento")


class EmailsDosAlunos(Protocol):
    """`T-327` — recorte de `RepositorioContasSupabase` que as telas da
    equipe usam: o e-mail do aluno por `CASO_ID`, em lote (sem N+1).
    `contas_dos_casos` (`T-331`) traz também `e_revisor`, para o painel."""

    def emails_dos_casos(self, caso_ids: tuple[str, ...]) -> dict[str, str]: ...

    def contas_dos_casos(self, caso_ids: tuple[str, ...]) -> dict[str, ContaDoCaso]: ...


def obter_emails_dos_alunos() -> EmailsDosAlunos:
    """Ponto único de injeção — sobrescrito nos testes. Só rotas de revisor
    (`exigir_papel_revisor`) dependem dele: o e-mail nunca vai a rota de
    aluno."""
    return RepositorioContasSupabase()


def obter_repositorio_eventos_da_lista() -> RepositorioEventosDaLista:
    """`T-408` — ponto de injeção da trilha em lote; sobrescrito nos testes."""
    return RepositorioEventosCasoSupabase()


def obter_repositorio_revisoes_da_lista() -> RepositorioRevisoesDaLista:
    """`T-408` — ponto de injeção das revisões em lote; sobrescrito nos testes."""
    return RepositorioRevisoesSupabase()


def obter_revisores() -> Callable[[], dict[str, str]]:
    """`T-408` — `conta_id` → e-mail de quem é revisor, para mostrar quem
    decidiu (`RF-506`); sobrescrito nos testes."""
    return lambda: {conta.conta_id: conta.email for conta in listar_revisores()}


def _vocabulario(
    colecao: ColecaoDeRegistros, respostas: RespostasCaso, snapshot: SnapshotOrdem
) -> VocabularioDoCaso:
    """`T-326` — o vocabulário do caso para as dívidas DESTE snapshot."""
    return vocabulario_do_caso(
        colecao.registros,
        respostas,
        (divida.DIVIDA_ID for divida in snapshot.estado_inputs.dividas),
    )


@roteador.get("/caso/{CASO_ID}/api/plano")
def plano_do_aluno(
    CASO_ID: Annotated[str, Depends(exigir_caso_da_sessao("CASO_ID"))],
    repositorio_casos: Annotated[RepositorioCasos, Depends(obter_repositorio_casos)],
    repositorio_snapshots: Annotated[
        RepositorioSnapshots, Depends(obter_repositorio_snapshots)
    ],
    colecao: Annotated[ColecaoDeRegistros, Depends(obter_colecao_da_coleta)],
    repositorio_respostas: Annotated[
        RepositorioRespostas, Depends(obter_repositorio_respostas_da_coleta)
    ],
    repositorio_itens: Annotated[RepositorioItens, Depends(obter_repositorio_itens_da_coleta)],
    contas: Annotated[ContasDosCasos, Depends(obter_contas_dos_casos)],
) -> JSONResponse:
    """`AC-25` — sempre o snapshot **liberado**, nunca o último calculado.

    `T-267` (`RF-92`): cada dívida da ordem leva a `fonte` de comprovação,
    derivada das respostas ATUAIS (`R9.7`) — o snapshot não a carrega e
    nenhuma conta é feita sobre ele (`AC-42`).

    O ponto de injeção é `rotas_plano.obter_repositorio_snapshots` — o
    mesmo da rota de PDF, porque é a mesma tela do aluno vista de dois
    jeitos. Dois pontos de injeção distintos fariam o plano e o PDF lerem de
    repositórios distintos num teste que sobrescreve só um dos dois, e o
    aluno veria um plano que o PDF não confirma.

    Sem plano liberado, devolve o ESTADO do caso, `plano: null` e a
    mensagem correspondente àquele estado — nunca uma tela de plano vazia
    nem um "nenhum plano liberado" genérico. O aluno em revisão lê "seu
    plano está em revisão", não uma negativa que não explica nada.

    `mensagem_do_estado_do_caso` vive em `app/http/mensagens_de_estado.py`
    com `match` exaustivo: um estado novo sem mensagem não compila."""
    caso = repositorio_casos.buscar(CASO_ID)
    if caso is None:  # pragma: no cover — defensivo
        raise ErroCasoDesaparecidoAposIsolamento(CASO_ID)

    if caso.snapshot_liberado_id is None:
        return JSONResponse(
            {
                "CASO_ID": CASO_ID,
                "plano": None,
                "estado": caso.estado.value,
                "mensagem": mensagem_do_estado_do_caso(caso.estado),
            }
        )

    try:
        snapshot = repositorio_snapshots.obter(caso.snapshot_liberado_id)
    except ErroSnapshotNaoEncontrado:
        return JSONResponse(
            {
                "CASO_ID": CASO_ID,
                "plano": None,
                "estado": caso.estado.value,
                "mensagem": mensagem_do_estado_do_caso(caso.estado),
            }
        )

    # A MESMA guarda de liberação que a rota do PDF usa — nenhuma segunda
    # checagem escrita aqui.
    if not snapshot_tem_liberacao_registrada(caso, snapshot):
        return JSONResponse(
            {
                "CASO_ID": CASO_ID,
                "plano": None,
                "estado": caso.estado.value,
                "mensagem": mensagem_do_estado_do_caso(caso.estado),
            }
        )

    textos = carregar_textos_canonicos()
    respostas, itens_por_escopo = duas_em_paralelo(
        lambda: repositorio_respostas.listar_do_caso(CASO_ID),
        lambda: _itens_por_escopo(repositorio_itens, CASO_ID),
    )
    respostas_do_caso = RespostasCaso(respostas=respostas)
    # `T-326` (`RF-111`): a dívida por "tipo — credor", nunca pelo código.
    contexto = montar_contexto_plano(
        snapshot,
        textos,
        _vocabulario(colecao, respostas_do_caso, snapshot),
        # Revisão de design: o plano chama o aluno pelo nome.
        nome_do_dono_do_caso(contas, CASO_ID),
        data_da_liberacao(CASO_ID, snapshot.SNAPSHOT_ID),
    )
    niveis = niveis_por_ficha(colecao.registros, respostas_do_caso, itens_por_escopo)
    return JSONResponse(
        {
            "CASO_ID": CASO_ID,
            "estado": caso.estado.value,
            "plano": serializar_plano(contexto, fontes_por_divida(niveis, textos), textos),
        }
    )


@roteador.get("/api/revisao/fila")
def fila_de_revisao(
    _revisor: Annotated[str, Depends(exigir_papel_revisor)],
    repositorio_casos: Annotated[RepositorioCasosDaFila, Depends(obter_repositorio_casos_da_fila)],
    repositorio_snapshots: Annotated[
        RepositorioSnapshots, Depends(obter_repositorio_snapshots_da_fila)
    ],
    emails: Annotated[EmailsDosAlunos, Depends(obter_emails_dos_alunos)],
) -> JSONResponse:
    """`AC-28` — a fila, com os dois sinais SEPARADOS.

    `entra_por_politica` (piloto 100% revisado) e `e_metodologico`
    (`REVISAO_HUMANA_OBRIGATORIA` do motor) nunca viram um booleano só: são
    fatos diferentes, e um teste estático falha se forem combinados."""
    # Mesmo caminho de `rotas_revisao.py::exibir_fila_de_revisao`: os casos
    # vêm de `listar_por_estado`, e inclui recálculos sem tratamento
    # especial — um caso liberado que voltou a `AGUARDANDO_REVISAO` é achado
    # pela MESMA consulta de estado.
    casos_ids = repositorio_casos.listar_por_estado(ESTADO_CASO.AGUARDANDO_REVISAO)
    itens = listar_fila_de_revisao(list(casos_ids), repositorio_casos, repositorio_snapshots)
    textos = carregar_textos_canonicos()
    email_por_caso = emails.emails_dos_casos(tuple(item.CASO_ID for item in itens))
    return JSONResponse(
        {
            "itens": [
                serializar_item_da_fila(item, textos, email_por_caso.get(item.CASO_ID))
                for item in itens
            ]
        }
    )


@roteador.get("/api/revisao/casos")
def casos_para_revisao(
    _revisor: Annotated[str, Depends(exigir_papel_revisor)],
    repositorio_casos: Annotated[RepositorioCasosDaFila, Depends(obter_repositorio_casos_da_fila)],
    repositorio_snapshots: Annotated[
        RepositorioSnapshots, Depends(obter_repositorio_snapshots_da_fila)
    ],
    repositorio_eventos: Annotated[
        RepositorioEventosDaLista, Depends(obter_repositorio_eventos_da_lista)
    ],
    repositorio_revisoes: Annotated[
        RepositorioRevisoesDaLista, Depends(obter_repositorio_revisoes_da_lista)
    ],
    emails: Annotated[EmailsDosAlunos, Depends(obter_emails_dos_alunos)],
    revisores_por_conta: Annotated[Callable[[], dict[str, str]], Depends(obter_revisores)],
    aba: Literal["pendentes", "entregues", "devolvidos", "todos"] = "pendentes",
    q: str | None = None,
    status: Annotated[list[ESTADO_CASO] | None, Query()] = None,
    de: date | None = None,
    ate: date | None = None,
    tipo: Literal["primeiro", "recalculo"] | None = None,
    mes_negativo: Literal["sim", "nao"] | None = None,
    metodo: str | None = None,
    motivo: str | None = None,
    revisor: str | None = None,
    parado_horas: Annotated[int | None, Query(ge=0)] = None,
    ordenar: CAMPO_DE_ORDEM | None = None,
    direcao: Literal["asc", "desc"] | None = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: int = 25,
) -> JSONResponse:
    """`RF-501` a `RF-506` — todos os casos que já chegaram ao revisor, com
    abas, filtros, ordenação e paginação no servidor. `status` repete o
    parâmetro para mais de um valor. A rota antiga `/api/revisao/fila` não
    muda."""
    if por_pagina not in (25, 50):
        raise HTTPException(status_code=422, detail="Use 25 ou 50 itens por página.")
    linhas = montar_linhas(
        datetime.now(UTC),
        repositorio_casos,
        repositorio_snapshots,
        repositorio_eventos,
        repositorio_revisoes,
        emails.contas_dos_casos,
    )
    filtros = FiltrosDaLista(
        aba=aba,
        q=q,
        status=frozenset(status or ()),
        de=de,
        ate=ate,
        tipo=tipo,
        mes_negativo=None if mes_negativo is None else mes_negativo == "sim",
        metodo=metodo,
        motivo=motivo,
        revisor=revisor,
        parado_horas=parado_horas,
    )
    resultado = consultar_casos(linhas, filtros, ordenar, direcao, pagina, por_pagina)
    textos = carregar_textos_canonicos()
    revisores = revisores_por_conta()
    return JSONResponse(
        {
            "itens": [serializar_linha_de_caso(x, textos, revisores) for x in resultado.linhas],
            "total": resultado.total,
            "pagina": pagina,
            "por_pagina": por_pagina,
            "contagens": resultado.contagens,
            "opcoes": serializar_opcoes_da_lista(textos, linhas, revisores),
        }
    )


@roteador.get("/api/revisao/caso/{CASO_ID_REVISAO}")
def caso_para_revisao(
    CASO_ID_REVISAO: str,
    _revisor: Annotated[str, Depends(exigir_papel_revisor)],
    repositorio_casos: Annotated[RepositorioCasos, Depends(obter_repositorio_casos_da_fila)],
    repositorio_snapshots: Annotated[
        RepositorioSnapshots, Depends(obter_repositorio_snapshots_da_fila)
    ],
    colecao: Annotated[ColecaoDeRegistros, Depends(obter_colecao_da_coleta)],
    repositorio_respostas: Annotated[
        RepositorioRespostas, Depends(obter_repositorio_respostas_da_coleta)
    ],
    repositorio_itens: Annotated[RepositorioItens, Depends(obter_repositorio_itens_da_coleta)],
    emails: Annotated[EmailsDosAlunos, Depends(obter_emails_dos_alunos)],
) -> JSONResponse:
    """O plano como o aluno o verá, mais o carimbo — para a tela lado a lado
    do revisor (`AC-29`).

    **O `plano` é o do aluno (`RF-121`, `AC-189`).** Mesmos `textos` fixos, mesma
    `fonte` por dívida, mesmo nome — os campos comuns
    saem idênticos aos de `plano_do_aluno`, para a tela do revisor reaproveitar
    o desenho do aluno sem uma segunda redação. Só o revisor recebe, além
    disso, `JUSTIFICATIVA_POSICAO`, o `motivo` das ações e o `ITEM_ID`
    (`para_revisor=True`).

    `mudancas` (`RF-123`, `AC-192`): o que mudou nos dados de entrada em
    relação à versão anterior; `null` na versão 1.

    O parâmetro se chama `CASO_ID_REVISAO`, não `CASO_ID`, de propósito: a
    auditoria de isolamento casa pelo nome literal, e esta rota é do
    REVISOR (protegida por papel), não do dono do caso.

    **O snapshot é o ÚLTIMO da cadeia, nunca `snapshot_liberado_id`.** É
    sobre o snapshot ainda não decidido que o revisor compara plano e
    `estado_inputs` — exigir o liberado deixaria a tela vazia exatamente
    nos casos em `AGUARDANDO_REVISAO`, que são todos os que importam aqui.
    A cadeia se busca por `caso.snapshot_raiz_id` (`OQ-11`), mesmo idioma
    de `app/revisao/fila.py:276`."""
    caso = repositorio_casos.buscar(CASO_ID_REVISAO)
    if caso is None or caso.snapshot_raiz_id is None:
        return JSONResponse({"erro": _MENSAGEM_SEM_PLANO}, status_code=404)

    historico = repositorio_snapshots.historico(caso.snapshot_raiz_id)
    if not historico:
        return JSONResponse({"erro": _MENSAGEM_SEM_PLANO}, status_code=404)

    snapshot = historico[-1]

    textos = carregar_textos_canonicos()
    respostas_brutas, itens_por_escopo = duas_em_paralelo(
        lambda: repositorio_respostas.listar_do_caso(CASO_ID_REVISAO),
        lambda: _itens_por_escopo(repositorio_itens, CASO_ID_REVISAO),
    )
    respostas_do_caso = RespostasCaso(respostas=respostas_brutas)

    anterior = _snapshot_anterior(snapshot, repositorio_snapshots)

    # `T-326` (`RF-111`): rótulos do registro e credores — o revisor lê
    # "Cheque especial — CAIXA", não `D011`; o código fica como detalhe. Com
    # versão anterior, o vocabulário cobre também as dívidas dela (uma dívida
    # removida ainda precisa de nome na lista de mudanças).
    vocabulario = vocabulario_do_caso(
        colecao.registros,
        respostas_do_caso,
        {
            divida.DIVIDA_ID
            for versao in (snapshot, anterior)
            if versao is not None
            for divida in versao.estado_inputs.dividas
        },
    )

    # `RF-121`: o plano chama o aluno pelo nome, como na tela dele.
    nome_do_aluno = _nome_do_aluno(emails, CASO_ID_REVISAO)
    # `RF-445`: na conferência o calendário parte de hoje (a liberação ainda não houve).
    contexto = montar_contexto_plano(snapshot, textos, vocabulario, nome_do_aluno, date.today())
    niveis = niveis_por_ficha(colecao.registros, respostas_do_caso, itens_por_escopo)
    item = montar_item_da_fila(CASO_ID_REVISAO, snapshot)
    # `AC-29`: plano e `estado_inputs` na MESMA resposta. O revisor compara
    # os dois lado a lado; se viessem de requisições diferentes, poderiam
    # ser de snapshots diferentes — e a comparação não provaria nada.
    estado_inputs = montar_contexto_estado_inputs(snapshot.estado_inputs, textos, vocabulario)
    mudancas = (
        None
        if anterior is None
        else mudancas_entre(
            estado_inputs,
            montar_contexto_estado_inputs(anterior.estado_inputs, textos, vocabulario),
        )
    )
    return JSONResponse(
        {
            "CASO_ID": CASO_ID_REVISAO,
            "plano": serializar_plano(
                contexto,
                fontes_por_divida(niveis, textos),
                textos,
                para_revisor=True,
                fatos_de_risco=fatos_de_risco_por_divida(
                    respostas_do_caso,
                    vocabulario,
                    (posicao.DIVIDA_ID for posicao in contexto.ordem),
                ),
            ),
            "estado_inputs": serializar_estado_inputs(estado_inputs),
            "mudancas": mudancas,
            # `T-430` (`RF-442`): soma dos saldos informados, só para o painel do
            # revisor. Saldo desconhecido não entra e marca o total como parcial.
            "resumo": _resumo_do_caso(snapshot),
            "deficitario": _bloco_deficitario(snapshot),
            "fila": serializar_item_da_fila(
                item,
                textos,
                emails.emails_dos_casos((CASO_ID_REVISAO,)).get(CASO_ID_REVISAO),
            ),
        }
    )


@roteador.get(_RAIZ_DA_CONFERENCIA + "/plano/pdf")
def previa_do_pdf_do_plano(
    CASO_ID_REVISAO: str,
    _revisor: Annotated[str, Depends(exigir_papel_revisor)],
    repositorio_casos: Annotated[RepositorioCasos, Depends(obter_repositorio_casos_da_fila)],
    repositorio_snapshots: Annotated[
        RepositorioSnapshots, Depends(obter_repositorio_snapshots_da_fila)
    ],
    colecao: Annotated[ColecaoDeRegistros, Depends(obter_colecao_da_coleta)],
    repositorio_respostas: Annotated[
        RepositorioRespostas, Depends(obter_repositorio_respostas_da_coleta)
    ],
    emails: Annotated[EmailsDosAlunos, Depends(obter_emails_dos_alunos)],
) -> Response:
    """`RF-124`, `AC-193` — a prévia do PDF que o aluno receberá, para o revisor
    abrir ANTES de liberar. Só quem tem papel de revisor (`401`/`403` pela mesma
    guarda das outras rotas da equipe); o PDF do aluno (`/caso/{id}/plano/pdf`)
    segue só do plano liberado. O snapshot é o último da cadeia, o mesmo que a
    conferência mostra."""
    caso = repositorio_casos.buscar(CASO_ID_REVISAO)
    if caso is None or caso.snapshot_raiz_id is None:
        raise HTTPException(status_code=404, detail=_MENSAGEM_SEM_PLANO)
    historico = repositorio_snapshots.historico(caso.snapshot_raiz_id)
    if not historico:
        raise HTTPException(status_code=404, detail=_MENSAGEM_SEM_PLANO)
    snapshot = historico[-1]

    textos = carregar_textos_canonicos()
    vocabulario = _vocabulario(
        colecao,
        RespostasCaso(respostas=repositorio_respostas.listar_do_caso(CASO_ID_REVISAO)),
        snapshot,
    )
    pdf = gerar_pdf_de_previa(
        snapshot, textos, vocabulario, _nome_do_aluno(emails, CASO_ID_REVISAO)
    )
    return Response(content=pdf, media_type="application/pdf")


def _snapshot_anterior(
    snapshot: SnapshotOrdem, repositorio_snapshots: RepositorioSnapshots
) -> SnapshotOrdem | None:
    """A versão anterior da cadeia, ou `None` na versão 1 (ou se ela sumiu)."""
    if snapshot.snapshot_anterior_id is None:
        return None
    try:
        return repositorio_snapshots.obter(snapshot.snapshot_anterior_id)
    except ErroSnapshotNaoEncontrado:
        return None


def _nome_do_aluno(emails: EmailsDosAlunos, caso_id: str) -> str | None:
    """O nome da compra, quando houver — personalização, nunca condição."""
    conta = emails.contas_dos_casos((caso_id,)).get(caso_id)
    return conta.nome if conta is not None else None


def _etapa_do_caso(
    relato: RelatoDeProgresso, colecao: ColecaoDeRegistros, textos: TextosCanonicosPlano
) -> str:
    """`RF-112` — o estado do caso por rótulo e, na coleta, a parte da trilha
    (`RF-100`) da próxima pergunta em branco, que `relato` já traz."""
    etapa = rotulo_de_codigo(textos.rotulos_de_codigos, relato.estado.value)
    if relato.estado is ESTADO_CASO.COLETA_INICIAL and relato.proxima_pergunta is not None:
        parte = parte_da_pergunta(colecao.registros, relato.proxima_pergunta.ID)
        if parte is not None:
            return f"{etapa} · {parte}"
    return etapa


@roteador.get("/api/operador/painel")
def painel_do_operador(
    _revisor: Annotated[str, Depends(exigir_papel_revisor)],
    colecao: Annotated[ColecaoDeRegistros, Depends(obter_colecao_de_registros_do_painel)],
    repositorio_casos: Annotated[CasosDoPainel, Depends(obter_repositorio_casos_do_painel)],
    repositorio_respostas: Annotated[
        RespostasDoPainel, Depends(obter_repositorio_respostas_do_painel)
    ],
    repositorio_itens: Annotated[ItensDoPainel, Depends(obter_repositorio_itens_do_painel)],
    emails: Annotated[EmailsDosAlunos, Depends(obter_emails_dos_alunos)],
) -> JSONResponse:
    """`RF-35` — quem está onde, sem nenhum valor financeiro.

    Só etapa, pendência e tempo desde a última atividade: é critério de
    aceite de `T-102` que esta tela nunca exiba dinheiro do aluno. A
    montagem reusa `consultar_trilha_de_progresso` — nenhuma trilha nova
    calculada aqui.

    **Três consultas, não `1 + 3N` — `T-187`.** Antes desta tarefa, cada
    caso do piloto custava três consultas próprias (`buscar`,
    `listar_do_caso` de respostas, idem de itens) — com N casos, N vezes a
    viagem de rede até o banco. `buscar_varios`/`listar_de_varios_casos`
    trazem TUDO de uma vez; o `for` abaixo só organiza dados que já estão
    em memória, sem tocar o banco de novo.

    **As três consultas em massa, em paralelo — `T-191`.** Nenhuma das três
    usa o resultado da outra (todas só precisam de `caso_ids`) — rodar em
    sequência pagava ~484ms de distância Boston↔São Paulo (`T-187`) três
    vezes por nada."""
    agora = datetime.now(UTC)
    caso_ids = repositorio_casos.listar_todos()
    casos_por_id, respostas_por_caso, itens_por_caso = tres_em_paralelo(
        lambda: repositorio_casos.buscar_varios(caso_ids),
        lambda: repositorio_respostas.listar_de_varios_casos(caso_ids),
        lambda: repositorio_itens.listar_de_varios_casos(caso_ids, incluir_removidos=False),
    )
    # `T-327` (`RF-111` e): uma consulta para todas as contas, não uma por
    # caso. `T-331` (`RF-112`): a mesma consulta diz quem é revisor — todo
    # cadastro cria caso, e conta promovida a revisor não é aluno.
    conta_por_caso = emails.contas_dos_casos(tuple(caso_ids))
    textos = carregar_textos_canonicos()

    linhas = []
    for caso_id in caso_ids:
        caso = casos_por_id.get(caso_id)
        if caso is None:  # pragma: no cover — defensivo: removido entre as duas consultas
            continue
        conta = conta_por_caso.get(caso_id)
        if conta is not None and conta.e_revisor:
            continue
        respostas = RespostasCaso(respostas=respostas_por_caso.get(caso_id, ()))
        itens = agrupar_itens_por_escopo(itens_por_caso.get(caso_id, ()))
        relato = consultar_trilha_de_progresso(caso, colecao.registros, respostas, itens)
        linha = _relato_para_linha(relato, agora)
        linhas.append(
            {
                "CASO_ID": linha.CASO_ID,
                "email_do_aluno": conta.email if conta is not None else None,
                # `T-332` (`RF-112`): o nome do comprador na Hotmart; `None` → "—".
                "nome_do_aluno": conta.nome if conta is not None else None,
                "estado": linha.estado.value,
                # `T-331` (`RF-112`): a etapa por rótulo — o cliente não traduz.
                "etapa": _etapa_do_caso(relato, colecao, textos),
                "aguardando_revisao": linha.aguardando_revisao,
                "tempo_desde_ultima_atividade": linha.tempo_desde_ultima_atividade,
                # `T-248` (RF-35, NFR de observabilidade da Rodada 9): o
                # bloqueio por inventário como motivo NOMEADO — só o código
                # da pendência, nunca contagem nem valor.
                "bloqueio_inventario": [
                    p.tipo.value
                    for p in pendencias_de_inventario(colecao.registros, respostas, itens)
                ],
            }
        )
    return JSONResponse({"linhas": linhas})
