"""Serialização do plano, da fila de revisão e do painel — `RF-50`, `RF-51`
(T-140).

**Por que este módulo existe.** As telas do plano, da revisão e do operador
passam a ser React (`RF-50`: nenhuma tela fora do template do protótipo).
O servidor deixa de renderizar HTML para elas e passa a entregar os MESMOS
campos que os templates recebiam — nada a mais, nada a menos.

**O que NÃO muda: `report/templates/plano/plano.html` continua existindo.**
Ele não é servido a navegador nenhum a partir daqui, mas `report/pdf.py`
renderiza aquele mesmo arquivo para gerar o PDF. `RF-21`/`AC-14` exigem que
a redação canônica de `Q-03` viva em UM lugar só, compartilhado por tela e
PDF; apagá-lo criaria uma segunda cópia do texto normativo — exatamente o
que aquele critério proíbe. O texto continua saindo de lá: é
`ContextoPlano.titulo`/`corpo`, montado por `report/plano.py` a partir de
`textos-canonicos.yaml`, e é isso que este módulo transporta.

**Lei nº 3 intacta.** Todo valor aqui é leitura de campo de um
`ContextoPlano` já montado — nenhuma aritmética, nenhuma derivação. Se uma
tela precisasse de um número que não é campo do contexto, a resposta seria
Open Question ao especialista, nunca uma conta nova nesta camada.

REGRAS: `RF-50`, `RF-51`, `RF-21`, `AC-14`, `AC-16`
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Final

from app.casos.inventario import credor_da_ficha
from app.http.rotas_calculo import _respostas_do_calculo
from app.montagem.entrada import resumo_das_despesas
from app.revisao.comprovacao import NivelDaFicha
from app.revisao.fila import ItemFila
from app.revisao.lista_de_casos import LinhaDoCaso
from collection.registro import RegistroPergunta
from collection.respostas import RespostasCaso
from report.plano import (
    ContextoCampo,
    ContextoEstadoInputs,
    ContextoPlano,
    TextosCanonicosPlano,
    VocabularioDoCaso,
    rotulo_de_codigo,
    rotulo_do_motivo_de_recalculo,
)

REGRAS: Final[tuple[str, ...]] = ("RF-50", "RF-51", "RF-21", "AC-14", "AC-16")


#: `B5.E01` (`RF-412`): a variável do registro e as respostas que dizem "atrasada".
_SITUACAO_DO_PAGAMENTO: Final[str] = "DIVIDA_EM_DIA / DIVIDA_ATRASADA"
_SITUACOES_ATRASADAS: Final[frozenset[str]] = frozenset({"VENCIDO", "PARCIAL"})


def rotulo_do_nivel(nivel: NivelDaFicha, textos: TextosCanonicosPlano) -> str:
    """`RF-91` — o rótulo do nível, de `textos-canonicos.yaml`; fonte sem
    resposta é "não informado", nunca um nível presumido."""
    chave = nivel.nivel.value if nivel.nivel is not None else "NAO_INFORMADO"
    return textos.rotulos_de_comprovacao.get(chave, chave)


def fontes_por_divida(
    niveis: tuple[NivelDaFicha, ...], textos: TextosCanonicosPlano
) -> dict[str, str]:
    """`RF-92` (`T-267`) — `item_id` → rótulo da fonte dos DADOS da dívida:
    a primeira pergunta de fonte da ficha, na ordem dos registros (a do
    Bloco 5; as de proposta vêm depois)."""
    fontes: dict[str, str] = {}
    for nivel in niveis:
        fontes.setdefault(nivel.item_id, rotulo_do_nivel(nivel, textos))
    return fontes


def vocabulario_do_caso(
    registros: tuple[RegistroPergunta, ...],
    respostas: RespostasCaso,
    dividas: Iterable[str],
) -> VocabularioDoCaso:
    """`RF-111` (`T-326`) — o que `report/` precisa para dar nome às coisas:
    o `rotulo` de cada opção do registro, por `VARIAVEL_GRAVADA` (a primeira
    pergunta que grava a variável vence), e o credor de cada dívida — o
    mesmo de `T-324`. Só leitura de registro e de resposta."""
    rotulos: dict[str, dict[str, str]] = {}
    for registro in registros:
        if registro.VARIAVEL_GRAVADA is None:
            continue
        opcoes = rotulos.setdefault(registro.VARIAVEL_GRAVADA, {})
        for opcao in registro.opcoes:
            if opcao.valor_interno is not None:
                opcoes.setdefault(opcao.valor_interno, opcao.rotulo)
    dividas = tuple(dividas)
    credores = {
        divida: credor
        for divida in dividas
        if (credor := credor_da_ficha(respostas, divida)) is not None
    }
    # `RF-412`: só respostas, transportadas; o texto e a frase de
    # responsabilidade são montados em `report/`.
    declaradas = respostas.valor("QUANTIDADE_DIVIDAS_DECLARADA_INICIAL")
    return VocabularioDoCaso(
        rotulos_de_opcao=rotulos,
        credores=credores,
        dividas_atrasadas=frozenset(
            d
            for d in dividas
            if respostas.valor_no_item(d, _SITUACAO_DO_PAGAMENTO) in _SITUACOES_ATRASADAS
        ),
        dividas_com_garantia=frozenset(
            d for d in dividas if respostas.valor_no_item(d, "POSSUI_GARANTIA") == "SIM"
        ),
        fichas_faltando=isinstance(declaradas, int) and declaradas > len(dividas),
        # as mesmas respostas que o motor leu (`B3.04A` só vale com `B3.04` = Sim)
        resumo_das_despesas=resumo_das_despesas(_respostas_do_calculo(registros, respostas)),
    )


def serializar_plano(
    contexto: ContextoPlano,
    fontes: Mapping[str, str] | None = None,
    textos: TextosCanonicosPlano | None = None,
    *,
    para_revisor: bool = False,
    fatos_de_risco: Mapping[str, Sequence[tuple[str, str]]] | None = None,
) -> dict[str, Any]:
    """`ContextoPlano` → JSON, campo a campo.

    `titulo` e `corpo` são a redação canônica carregada de
    `textos-canonicos.yaml` — transportada verbatim, jamais reescrita aqui
    (`AC-14`: caractere por caractere).

    O carimbo de versão (`ENGINE_VERSION`/`PARAMETROS_VERSION`) acompanha a
    saída, como `AC-16` exige — uma tela sem carimbo é uma tela que não diz
    de qual cálculo veio.

    `fontes` (`T-267`, `RF-92`): `DIVIDA_ID` → rótulo da fonte de
    comprovação, derivado das respostas (não do snapshot); `None` quando a
    dívida não tem ficha ativa.

    `para_revisor` (`T-305`): só o revisor recebe `JUSTIFICATIVA_POSICAO`
    e (`T-326`) o motivo técnico de cada ação.

    `T-326` (`RF-111`): a dívida vai por `nome` ("tipo — credor"); o
    `DIVIDA_ID` segue como identificador. `metodo` e `cenario` são rótulos.

    `textos` (plano amigável, 2026-10-03) — só para os textos FIXOS que não
    variam por caso (título de seções, explicação do Mês 1, dúvidas comuns,
    nota de rodapé): nenhum deles é campo de `ContextoPlano`, porque não
    dependem do snapshot. `None` omite essas chaves do payload (compatível
    com chamadores que ainda não as usam, como a tela do revisor)."""
    fontes = fontes or {}
    fatos_de_risco = fatos_de_risco or {}
    return {
        "titulo": contexto.titulo,
        "corpo": contexto.corpo,
        "ordem": [
            {
                "posicao": posicao.posicao,
                "indice": posicao.indice,
                "total": posicao.total,
                "DIVIDA_ID": posicao.DIVIDA_ID,
                "nome": posicao.nome,
                # `JUSTIFICATIVA_POSICAO` é o texto de AUDITORIA do motor —
                # o revisor precisa dele para refazer a decisão (`AC-29`).
                # `explicacao` (T-177) é o mesmo "porquê" dito ao ALUNO.
                # `T-305`: o texto técnico não sai para o aluno.
                **(
                    {"JUSTIFICATIVA_POSICAO": posicao.JUSTIFICATIVA_POSICAO}
                    if para_revisor
                    else {}
                ),
                "explicacao": posicao.explicacao,
                # `T-354`: a nota de incômodo que o aluno deu e o aviso de
                # que a ordem seguiu o critério do método (nota alta).
                "incomodo": posicao.incomodo,
                "aviso_incomodo": posicao.aviso_incomodo,
                # `RF-412`: avisos do que o aluno declarou (atraso, garantia).
                "avisos": list(posicao.avisos),
                # `T-354`: o que o aluno respondeu sobre atraso, cobrança
                # judicial e garantia — só o revisor, só respostas, sem
                # selo de "crítica" calculado (Lei nº 3).
                **(
                    {
                        "fatos_de_risco": [
                            {"nome": nome, "valor": valor}
                            for nome, valor in fatos_de_risco.get(posicao.DIVIDA_ID, ())
                        ]
                    }
                    if para_revisor
                    else {}
                ),
                # `T-304` (`DE-08`): lido do cronograma; `None` = não disponível.
                "mes_de_quitacao": posicao.mes_de_quitacao,
                "mes_de_quitacao_rotulo": posicao.mes_de_quitacao_rotulo,
                # Revisão de design: os números fixos de toda dívida
                # (deve hoje, parcela, juros), lidos e formatados.
                "fatos": [{"rotulo": rotulo, "valor": valor} for rotulo, valor in posicao.fatos],
                "fonte": fontes.get(posicao.DIVIDA_ID),
                "valores_de_apoio": [
                    {"rotulo": rotulo, "valor": valor}
                    for rotulo, valor in posicao.valores_de_apoio
                ],
            }
            for posicao in contexto.ordem
        ],
        "PRAZO_TOTAL": contexto.PRAZO_TOTAL,
        # Plano amigável — inteiro cru, só para a geometria dos gráficos no
        # cliente (ver "Regra de geometria" em `report/templates/plano/
        # visuais.html`); nunca exibido como número.
        "PRAZO_TOTAL_INT": contexto.PRAZO_TOTAL_INT,
        "CUSTO_FUTURO_TOTAL": contexto.CUSTO_FUTURO_TOTAL,
        "valor_mensal_destinado": contexto.valor_mensal_destinado,
        "ENGINE_VERSION": contexto.ENGINE_VERSION,
        "PARAMETROS_VERSION": contexto.PARAMETROS_VERSION,
        "metodo": contexto.metodo,
        "cenario": contexto.rotulo_do_cenario,
        "acoes": [
            {
                "DIVIDA_ID": acao.DIVIDA_ID,
                "nome_divida": acao.nome_divida,
                "descricao": acao.descricao,
                "prioridade_excepcional": acao.prioridade_excepcional,
                **({"motivo": acao.motivo} if para_revisor else {}),
            }
            for acao in contexto.acoes
        ],
        "pendencias": None
        if contexto.pendencias is None
        else {
            "inventario_incompleto": contexto.pendencias.inventario_incompleto,
            "campos_faltantes_por_divida": [
                {"DIVIDA_ID": divida, "nome": nome, "campos": list(campos)}
                for divida, nome, campos in contexto.pendencias.campos_faltantes_por_divida
            ],
        },
        "MODO_ESTABILIZACAO": contexto.MODO_ESTABILIZACAO,
        "RESULTADO_CAIXA_OBSERVADO": contexto.RESULTADO_CAIXA_OBSERVADO,
        "FALTA_CORTAR": contexto.FALTA_CORTAR,
        "reserva_mobilizavel": {
            # `AC-70`: reserva desconhecida é ESTADO explícito, nunca
            # `R$ 0,00` e nunca campo omitido.
            "pendente_de_decisao": contexto.reserva_mobilizavel.pendente_de_decisao,
            "valor": contexto.reserva_mobilizavel.valor,
        },
        # `T-276` (RF-98, AC-152): seção à parte, lida do snapshot pelo
        # contexto — nenhum campo acima vem daqui.
        "cenario_adicional": None
        if contexto.cenario_adicional is None
        else {
            "rotulo": contexto.cenario_adicional.rotulo,
            "explicacao": contexto.cenario_adicional.explicacao,
            "PRAZO_TOTAL": contexto.cenario_adicional.PRAZO_TOTAL,
            "CUSTO_FUTURO_TOTAL": contexto.cenario_adicional.CUSTO_FUTURO_TOTAL,
            "ordem": list(contexto.cenario_adicional.ordem),
            "itens": [
                {
                    # `T-306`/`T-326` — o `ITEM_ID` (`EXT001`) continua só
                    # como detalhe para o revisor; o aluno nunca lê um
                    # código. Sem nome próprio para o recurso no motor, o
                    # rótulo é genérico ("o valor extra que você nos
                    # contou"), igual ao usado em `jornada`.
                    **({"ITEM_ID": item.ITEM_ID} if para_revisor else {}),
                    "mes": item.mes,
                    "mes_rotulo": item.mes_rotulo,
                    "valor": item.valor,
                }
                for item in contexto.cenario_adicional.itens
            ],
        },
        "nao_projetados": [
            {"ITEM_ID": item_id, "motivo": motivo} for item_id, motivo in contexto.nao_projetados
        ],
        # Plano amigável (2026-10-03) — campos novos da "consultoria
        # individual", lidos de `ContextoPlano` sem nenhum cálculo.
        # Revisão de design (2026-10-03) — personalização: primeiro nome e
        # os números do mês do aluno, todos lidos e já formatados.
        "nome_do_aluno": contexto.nome_do_aluno,
        "ponto_de_partida": None
        if contexto.ponto_de_partida is None
        else {
            "renda": contexto.ponto_de_partida.renda,
            "gastos": contexto.ponto_de_partida.gastos,
            "gastos_ocasionais": contexto.ponto_de_partida.gastos_ocasionais,
            "parcelas": contexto.ponto_de_partida.parcelas,
            "valor_extra": contexto.ponto_de_partida.valor_extra,
            "quantidade_de_dividas": contexto.ponto_de_partida.quantidade_de_dividas,
            # `RF-412` (`B3.DF02`): fixo × variável e o resultado mensal.
            "contribuicao_familiar": contexto.ponto_de_partida.contribuicao_familiar,
            "despesas_tipo_fixo": contexto.ponto_de_partida.despesas_tipo_fixo,
            "despesas_tipo_variavel": contexto.ponto_de_partida.despesas_tipo_variavel,
            "despesas_nao_classificadas": contexto.ponto_de_partida.despesas_nao_classificadas,
            "despesas_mensais_totais": contexto.ponto_de_partida.despesas_mensais_totais,
        },
        "avisos_gerais": list(contexto.avisos_gerais),
        "como_funciona": list(contexto.como_funciona),
        # `T-352`/`T-353`: o curso de entrada e o aviso de plano sem valor
        # extra — texto fixo, escolhido por lookup (nenhuma conta).
        # `RF-77`/`RF-78`: os três caminhos, já em texto — só leitura.
        "prognostico": None
        if contexto.prognostico is None
        else {
            "titulo": contexto.prognostico.titulo,
            "introducao": contexto.prognostico.introducao,
            "eixo_inicio": contexto.prognostico.eixo_inicio,
            "eixo_fim": contexto.prognostico.eixo_fim,
            "caminhos": [
                {
                    "cor": caminho.cor,
                    "titulo": caminho.titulo,
                    "veredito": caminho.veredito,
                    "nota": caminho.nota,
                    "marcador": caminho.marcador,
                    "destaques": [
                        {"rotulo": rotulo, "valor": valor} for rotulo, valor in caminho.destaques
                    ],
                    "mes_fim": caminho.mes_fim,
                    "escala": caminho.escala,
                    "marcos": [
                        {
                            "mes": mes,
                            "numero": numero,
                            "rotulo": caminho.marcos_rotulos[i] if caminho.marcos_rotulos else "",
                        }
                        for i, (mes, numero) in enumerate(caminho.marcos)
                    ],
                    "itens": list(caminho.itens),
                    "economia": caminho.economia,
                    "rotulo_curto": caminho.rotulo_curto,
                }
                for caminho in contexto.prognostico.caminhos
            ],
            "detalhes": [
                {
                    "cor": plano.cor,
                    "titulo": plano.titulo,
                    "meses": [
                        {
                            "rotulo": mes.rotulo,
                            "ancora": mes.ancora,
                            "divida_da_vez": None
                            if mes.divida_da_vez is None
                            else {
                                "numero": mes.divida_da_vez[0],
                                "nome": mes.divida_da_vez[1],
                            },
                            "valor_extra": mes.valor_extra,
                            "saldo": mes.saldo,
                            "quitadas": [
                                {"numero": numero, "nome": nome} for numero, nome in mes.quitadas
                            ],
                            "quitas": list(mes.quitas),
                            "pagina": None
                            if mes.pagina is None
                            else {
                                "numero": mes.pagina.numero,
                                "de_total": mes.pagina.de_total,
                                "total_pagar": mes.pagina.total_pagar,
                                "extra_aplicado": mes.pagina.extra_aplicado,
                                "divida_apos": mes.pagina.divida_apos,
                                "linhas": [
                                    {
                                        "nome": linha.nome,
                                        "saldo_antes": linha.saldo_antes,
                                        "juros": linha.juros,
                                        "habitual": linha.habitual,
                                        "extra": linha.extra,
                                        "total": linha.total,
                                        "saldo_depois": linha.saldo_depois,
                                        "quita": linha.quita,
                                    }
                                    for linha in mes.pagina.linhas
                                ],
                                "inicio": mes.pagina.inicio,
                                "juros": mes.pagina.juros,
                                "pagamentos": mes.pagina.pagamentos,
                                "restante": mes.pagina.restante,
                                "habitual_total": mes.pagina.habitual_total,
                                "extra_total": mes.pagina.extra_total,
                                "quitacao": mes.pagina.quitacao,
                            },
                            "primeira_quitacao": mes.primeira_quitacao,
                            "ultimo": mes.ultimo,
                        }
                        for mes in plano.meses
                    ],
                }
                for plano in contexto.prognostico.detalhes
            ],
        },
        # `T-375`: "Quando cada dívida termina", dentro de "Seu plano em números".
        "quando_termina": None
        if contexto.quando_termina is None
        else {
            "colunas": list(contexto.quando_termina.colunas),
            "cores": list(contexto.quando_termina.cores),
            "linhas": [
                {"numero": numero, "nome": nome, "meses": list(celulas)}
                for numero, nome, celulas in contexto.quando_termina.linhas
            ],
        },
        "curso_ssd": None
        if contexto.curso_ssd is None
        else {
            "apresentacao_titulo": contexto.curso_ssd.apresentacao_titulo,
            "apresentacao": list(contexto.curso_ssd.apresentacao),
            "introducao_titulo": contexto.curso_ssd.introducao_titulo,
            "introducao": contexto.curso_ssd.introducao,
            "quadro_titulo": contexto.curso_ssd.quadro_titulo,
            "aulas": [
                {"numero": numero, "titulo": titulo, "motivo": motivo}
                for numero, titulo, motivo in contexto.curso_ssd.aulas
            ],
            "melhorar_titulo": contexto.curso_ssd.melhorar_titulo,
            "melhorar_intro": contexto.curso_ssd.melhorar_intro,
            "melhorar": [
                {"texto": texto, "aula": aula} for texto, aula in contexto.curso_ssd.melhorar
            ],
        },
        "aviso_sem_valor_extra": contexto.aviso_sem_valor_extra,
        "pendencias_acionaveis": [
            {
                "DIVIDA_ID": pendencia.DIVIDA_ID,
                "nome_divida": pendencia.nome_divida,
                "rotulo": pendencia.rotulo,
                "onde_achar": pendencia.onde_achar,
                # `ID_PERGUNTA` (maiúsculo): mesma convenção de chave de
                # DETALHE já usada pelo payload de decisão (`T-328`) — um
                # código, nunca texto principal.
                "ID_PERGUNTA": pendencia.id_pergunta,
            }
            for pendencia in contexto.pendencias_acionaveis
        ],
        # Textos fixos que não variam por caso — só quando `textos` é
        # passado (compatível com chamadores que ainda não os usam).
        **(
            {
                "explicacao_mes_1": textos.explicacao_mes_1,
                "como_funciona_titulo": textos.como_funciona_titulo,
                # Rótulo "Mês" e afins (também usados no cenário adicional).
                "grade_meses_textos": dict(textos.grade_meses),
                # Revisão de design — cabeçalho, títulos das seções, resumo,
                # ponto de partida, passos do Mês 1, quadros de "Como
                # funciona" e cartão de cada dívida.
                "cabecalho_textos": dict(textos.cabecalho),
                "secoes": dict(textos.secoes),
                "resumo_textos": dict(textos.resumo),
                "prognostico_textos": dict(textos.prognostico),
                "ponto_de_partida_textos": dict(textos.ponto_de_partida),
                "como_funciona_rotulos": list(textos.como_funciona_rotulos),
                "dividas_textos": dict(textos.textos_das_dividas),
                "reserva_explicacao": textos.reserva_explicacao,
                "duvidas": [
                    {"pergunta": pergunta, "resposta": resposta}
                    for pergunta, resposta in textos.duvidas
                ],
                "sobre_este_plano": textos.sobre_este_plano,
            }
            if textos is not None
            else {}
        ),
    }


def serializar_item_da_fila(
    item: ItemFila, textos: TextosCanonicosPlano, email_do_aluno: str | None = None
) -> dict[str, Any]:
    """Uma linha da fila de revisão.

    `T-327` (`RF-111` e): `email_do_aluno` identifica o caso para a equipe;
    `None` (conta sem e-mail) faz a tela cair no `CASO_ID`.

    `T-326` (`RF-111`): `metodo`, `status_metodo` e `motivo` são os rótulos
    que a tela mostra; os códigos e o `MOTIVO_RECALCULO` do motor seguem
    como detalhe.

    `entra_por_politica` e `e_metodologico` seguem SEPARADOS — um teste
    estático falha se forem combinados num único booleano. São coisas
    diferentes: a política do piloto (100% revisado) e o campo
    `REVISAO_HUMANA_OBRIGATORIA` que o motor levantou.
    """
    snapshot = item.snapshot
    return {
        "CASO_ID": item.CASO_ID,
        "email_do_aluno": email_do_aluno,
        "SNAPSHOT_ID": snapshot.SNAPSHOT_ID,
        "versao": snapshot.versao,
        "DATA_REFERENCIA": snapshot.DATA_REFERENCIA.isoformat(),
        "MOTIVO_RECALCULO": snapshot.MOTIVO_RECALCULO,
        "EVENTO_RECALCULO": (
            snapshot.EVENTO_RECALCULO.value
            if snapshot.EVENTO_RECALCULO is not None
            and hasattr(snapshot.EVENTO_RECALCULO, "value")
            else snapshot.EVENTO_RECALCULO
        ),
        "METODO_RECOMENDADO_PIQ": (
            snapshot.METODO_RECOMENDADO_PIQ.value
            if hasattr(snapshot.METODO_RECOMENDADO_PIQ, "value")
            else str(snapshot.METODO_RECOMENDADO_PIQ)
        ),
        "STATUS_METODO": (
            snapshot.STATUS_METODO.value
            if hasattr(snapshot.STATUS_METODO, "value")
            else str(snapshot.STATUS_METODO)
        ),
        "metodo": rotulo_de_codigo(
            textos.rotulos_de_codigos, snapshot.METODO_RECOMENDADO_PIQ.value
        ),
        "status_metodo": rotulo_de_codigo(textos.rotulos_de_codigos, snapshot.STATUS_METODO.value),
        # `T-330`: o método vale para o caso inteiro — o critério vai uma
        # vez, no destaque, nunca repetido por posição.
        "criterio_metodo": textos.criterio_do_metodo.get(
            snapshot.METODO_RECOMENDADO_PIQ.value, ""
        ),
        "motivo": rotulo_do_motivo_de_recalculo(snapshot, textos),
        "entra_por_politica": item.entra_por_politica,
        "e_metodologico": item.e_metodologico,
        "ENGINE_VERSION": snapshot.ENGINE_VERSION,
        "PARAMETROS_VERSION": snapshot.PARAMETROS_VERSION,
    }


def serializar_linha_de_caso(
    linha: LinhaDoCaso, textos: TextosCanonicosPlano, revisores: Mapping[str, str]
) -> dict[str, Any]:
    """`RF-502` (T-408) — uma linha da tabela do revisor, com rótulos humanos
    do servidor. Os códigos ficam só em `status`.

    `entra_por_politica` e `e_metodologico` seguem SEPARADOS (`AC-28`): a
    política do piloto (100% revisado) e o campo `REVISAO_HUMANA_OBRIGATORIA`
    do motor são fatos diferentes."""
    rotulos = textos.rotulos_de_codigos
    snapshot = linha.item.snapshot
    return {
        "CASO_ID": linha.CASO_ID,
        "nome": linha.nome,
        "email_do_aluno": linha.email,
        "chegou_em": linha.chegou_em.isoformat(),
        "chegada_aproximada": linha.chegada_aproximada,
        "tempo_na_fila_horas": linha.tempo_na_fila_horas,
        "atrasado": linha.atrasado,
        "status": linha.status.value,
        "status_rotulo": rotulo_de_codigo(rotulos, f"FILA_{linha.status.value}"),
        "tipo": "recalculo" if linha.e_recalculo else "primeiro",
        "tipo_rotulo": rotulo_de_codigo(
            rotulos, "FILA_TIPO_RECALCULO" if linha.e_recalculo else "FILA_TIPO_PRIMEIRO"
        ),
        "motivo_rotulo": rotulo_de_codigo(rotulos, linha.motivo),
        "mes_negativo": linha.mes_negativo,
        "situacao_mes_rotulo": rotulo_de_codigo(
            rotulos, "FILA_MES_NEGATIVO" if linha.mes_negativo else "FILA_MES_POSITIVO"
        ),
        "dividas": linha.dividas,
        "metodo": rotulo_de_codigo(rotulos, linha.metodo),
        "status_metodo": rotulo_de_codigo(rotulos, snapshot.STATUS_METODO.value),
        "entra_por_politica": linha.item.entra_por_politica,
        "e_metodologico": linha.item.e_metodologico,
        "revisor": (
            revisores.get(linha.revisor) or rotulo_de_codigo(rotulos, "FILA_REVISOR_DESCONHECIDO")
            if linha.revisor is not None
            else None
        ),
        "decidido_em": linha.decidido_em.isoformat() if linha.decidido_em else None,
    }


def serializar_opcoes_da_lista(
    textos: TextosCanonicosPlano, linhas: Iterable[LinhaDoCaso], revisores: Mapping[str, str]
) -> dict[str, list[dict[str, str]]]:
    """Os valores que a tela oferece nos filtros de método, motivo e revisor:
    `codigo` volta como parâmetro de consulta, `rotulo` é o que se lê."""
    rotulos = textos.rotulos_de_codigos
    visiveis = list(linhas)

    def _opcoes(codigos: Iterable[str]) -> list[dict[str, str]]:
        return [
            {"codigo": c, "rotulo": rotulo_de_codigo(rotulos, c)} for c in sorted(set(codigos))
        ]

    return {
        "metodos": _opcoes(linha.metodo for linha in visiveis),
        "motivos": _opcoes(linha.motivo for linha in visiveis),
        "revisores": [
            {
                "codigo": c,
                "rotulo": revisores.get(c)
                or rotulo_de_codigo(rotulos, "FILA_REVISOR_DESCONHECIDO"),
            }
            for c in sorted({linha.revisor for linha in visiveis if linha.revisor})
        ],
    }


def serializar_estado_inputs(contexto: ContextoEstadoInputs) -> dict[str, Any]:
    """`AC-29` — os `estado_inputs` que produziram o snapshot, para a tela
    de comparação do revisor.

    **Transporte, nunca formatação.** Cada `valor` já vem pronto de
    `montar_contexto_estado_inputs`, que passou por
    `_formatar_valor_ou_desconhecido` — é lá que se decide como um campo
    desconhecido aparece, e é lá que `DESCONHECIDO` deixa de poder virar
    `0` ou string vazia (`AC-08`/`GAB-03`). Reformatar aqui criaria uma
    segunda regra de exibição, divergente da primeira.

    Nenhum campo é omitido: o revisor compara o plano contra o estado
    COMPLETO, e um campo ausente da tela é um campo que ninguém confere.
    """
    def campos(lista: Iterable[ContextoCampo]) -> list[dict[str, str]]:
        # `T-326`: `nome` é o rótulo; `codigo`, o nome técnico (detalhe).
        return [{"nome": c.nome, "valor": c.valor, "codigo": c.codigo} for c in lista]

    return {
        "campos": campos(contexto.campos),
        "perfil_comportamental": campos(contexto.perfil_comportamental),
        "sinais_comportamentais": campos(contexto.sinais_comportamentais),
        "dividas": [
            {"DIVIDA_ID": d.DIVIDA_ID, "nome": d.nome, "campos": campos(d.campos)}
            for d in contexto.dividas
        ],
    }
