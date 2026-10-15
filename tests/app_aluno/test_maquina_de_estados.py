"""Testes de comportamento de `app/casos/maquina.py` — `RF-01` (T-34).

Suíte DIFERENTE de `tests/app_aluno/test_maquina_estados_construcao.py`
(T-33): aquela prova o que a máquina PROMETE CONSTRUIR (nove estados, forma
de `Transicao`, um par recusado como amostra, ausência de estado
"reaberto"). Esta prova o COMPORTAMENTO da máquina ao longo do tempo:

1. o caminho do plano §7.1 até a entrega (`PLANO_LIBERADO`) é percorrível
   só por transições declaradas (`gatilho` nomeado a cada passo, nunca uma
   transição inventada pelo teste);
2. o produto cartesiano DOS DOZE ESTADOS — 12×12 = 144 pares, EXAUSTIVO,
   não amostrado — separa os 10 pares declarados (sucesso) dos 134
   restantes (recusa por `ErroTransicaoNaoDeclarada`, nomeando origem e
   destino);
3. `ERRO_DE_CALCULO` volta à origem de `CALCULANDO` por transição nomeada
   (`EC-06`); os estados pós-plano não têm transição alguma (`T-390`);
4. `REPROVADO_EM_REVISAO` é alcançável só a partir de `AGUARDANDO_REVISAO`,
   nunca a partir de `PLANO_LIBERADO` (`EC-12`);
5. a única saída de `REPROVADO_EM_REVISAO` é a volta à coleta
   (`devolve_ao_aluno`, `RF-113`, `T-333`);
6. `PLANO_LIBERADO` é terminal: o plano entregue é definitivo (`RF-401`,
   `RF-409`, `T-387`).

REGRAS: `RF-01`, `RF-113`
"""

from __future__ import annotations

import itertools

import pytest

from app.casos.maquina import (
    ESTADO_CASO,
    TABELA_TRANSICOES,
    ErroTransicaoNaoDeclarada,
    transicionar,
    transicoes_a_partir_de,
)

# Os pares declarados na tabela — usados para a exaustão do produto
# cartesiano. Não é uma cópia solta: é derivado da própria TABELA_TRANSICOES,
# para que o teste nunca divirja do módulo por edição manual desatualizada.
_PARES_DECLARADOS: frozenset[tuple[ESTADO_CASO, ESTADO_CASO]] = frozenset(
    (t.de, t.para) for t in TABELA_TRANSICOES
)


def test_tabela_declara_exatamente_dez_transicoes() -> None:
    """Pré-condição da exaustão: a tabela citada pela tarefa (17 linhas, 18
    desde `T-333`, 19 desde `T-336`, 21 desde `T-341`, 16 desde `T-387`, que
    desligou as cinco saídas de `PLANO_LIBERADO`/`ACOMPANHAMENTO`, e 10 desde
    `T-390`, que tirou o recálculo e os retornos de erro dos três estados
    pós-plano) tem 10 pares distintos.
    Se este número mudar, os testes abaixo continuam corretos (derivam de
    `TABELA_TRANSICOES`), mas este teste avisa explicitamente que a
    superfície declarada mudou."""
    assert len(TABELA_TRANSICOES) == 10
    assert len(_PARES_DECLARADOS) == 10


def test_caminho_completo_do_plano_e_percorrivel_so_por_transicoes_declaradas() -> None:
    """Critério 1 — o caminho `CADASTRADO → ... → PLANO_LIBERADO` do plano
    §7.1 (que desde `T-387` termina na entrega) é percorrido passo a passo, cada um por
    `transicionar(de, para)`. Se um par do caminho não estivesse na tabela,
    `transicionar` levantaria `ErroTransicaoNaoDeclarada` e o teste falharia
    — não há atalho nem transição inventada pelo teste."""
    caminho = (
        ESTADO_CASO.CADASTRADO,
        ESTADO_CASO.CONSENTIMENTO_REGISTRADO,
        ESTADO_CASO.COLETA_INICIAL,
        ESTADO_CASO.CALCULANDO,
        ESTADO_CASO.AGUARDANDO_REVISAO,
        ESTADO_CASO.PLANO_LIBERADO,
    )

    gatilhos_esperados = (
        "registra_consentimento",
        "inicia_coleta",
        "bloco_6_executa",
        "snapshot_anexado",
        "libera",
    )

    assert len(caminho) - 1 == len(gatilhos_esperados)

    for (de, para), gatilho_esperado in zip(
        itertools.pairwise(caminho), gatilhos_esperados, strict=True
    ):
        transicao = transicionar(de, para)
        assert transicao.gatilho == gatilho_esperado, (
            f"{de} → {para} deveria disparar {gatilho_esperado!r}, "
            f"disparou {transicao.gatilho!r}"
        )


@pytest.mark.parametrize("para", list(ESTADO_CASO))
def test_plano_liberado_e_terminal_nenhuma_transicao_e_aceita(para: ESTADO_CASO) -> None:
    """`RF-401`, `RF-409` (`T-387`) — o plano entregue é definitivo: de
    `PLANO_LIBERADO` NENHUM destino é aceito (nem a coleta dirigida, nem a
    confirmação do ataque, nem o acompanhamento, nem plano novo em
    `COLETA_INICIAL`, nem ele mesmo), e a tabela não tem linha de saída."""
    assert not [t for t in TABELA_TRANSICOES if t.de is ESTADO_CASO.PLANO_LIBERADO]
    assert transicoes_a_partir_de(ESTADO_CASO.PLANO_LIBERADO) == ()
    with pytest.raises(ErroTransicaoNaoDeclarada) as capturado:
        transicionar(ESTADO_CASO.PLANO_LIBERADO, para)
    assert capturado.value.de is ESTADO_CASO.PLANO_LIBERADO
    assert capturado.value.para is para


@pytest.mark.parametrize("nome", ["COLETA_DIRIGIDA", "CONFIRMACAO_ATAQUE", "ACOMPANHAMENTO"])
def test_estados_pos_plano_nao_existem_mais(nome: str) -> None:
    """`RF-413` (`T-400`): os três estados pós-plano foram apagados do enum."""
    assert nome not in ESTADO_CASO.__members__


def test_produto_cartesiano_completo_dos_nove_estados_e_exaustivo() -> None:
    """Critério 2 — EXAUSTIVO sobre os 9×9 = 81 pares (de, para), nenhuma
    amostra: os 10 pares declarados sucedem e devolvem a `Transicao`
    correta; os 71 restantes são recusados com `ErroTransicaoNaoDeclarada`
    nomeando origem e destino."""
    todos_os_pares = list(itertools.product(ESTADO_CASO, ESTADO_CASO))
    assert len(todos_os_pares) == 81  # 9 x 9, produto cartesiano completo

    pares_declarados_vistos = 0
    pares_recusados_vistos = 0

    for de, para in todos_os_pares:
        if (de, para) in _PARES_DECLARADOS:
            transicao = transicionar(de, para)
            assert transicao.de is de
            assert transicao.para is para
            pares_declarados_vistos += 1
        else:
            with pytest.raises(ErroTransicaoNaoDeclarada) as capturado:
                transicionar(de, para)
            erro = capturado.value
            assert erro.de is de
            assert erro.para is para
            pares_recusados_vistos += 1

    assert pares_declarados_vistos == 10
    assert pares_recusados_vistos == 71
    assert pares_declarados_vistos + pares_recusados_vistos == 81


def test_erro_de_calculo_volta_so_a_coleta_inicial_ec06() -> None:
    """Critério 3 (`EC-06`) — `COLETA_INICIAL` é a única origem de
    `CALCULANDO` que sobrou (`T-390` tirou o recálculo a partir dos estados
    pós-plano). `ERRO_DE_CALCULO` volta a ela por transição nomeada
    (`operador_retoma_apos_erro`) e a ida `COLETA_INICIAL → CALCULANDO`
    existe: a origem alegada é de fato uma origem real de `CALCULANDO`."""
    transicao_de_volta = transicionar(ESTADO_CASO.ERRO_DE_CALCULO, ESTADO_CASO.COLETA_INICIAL)
    assert transicao_de_volta.gatilho == "operador_retoma_apos_erro"

    transicao_de_ida = transicionar(ESTADO_CASO.COLETA_INICIAL, ESTADO_CASO.CALCULANDO)
    assert transicao_de_ida.para is ESTADO_CASO.CALCULANDO

    destinos_declarados = {
        t.para for t in TABELA_TRANSICOES if t.de is ESTADO_CASO.ERRO_DE_CALCULO
    }
    assert destinos_declarados == {ESTADO_CASO.COLETA_INICIAL}


def test_reprovado_em_revisao_e_alcancavel_a_partir_de_aguardando_revisao_ec12() -> None:
    """Critério 4, primeira metade (`EC-12`) — `AGUARDANDO_REVISAO →
    REPROVADO_EM_REVISAO` é uma transição nomeada e declarada."""
    transicao = transicionar(
        ESTADO_CASO.AGUARDANDO_REVISAO, ESTADO_CASO.REPROVADO_EM_REVISAO
    )
    assert transicao.gatilho == "reprova"


def test_reprovado_em_revisao_nao_e_alcancavel_a_partir_de_plano_liberado_ec12() -> None:
    """Critério 4, segunda metade (`EC-12`) — `PLANO_LIBERADO →
    REPROVADO_EM_REVISAO` NÃO está na tabela: uma vez liberado, o plano não
    pode ser reprovado por essa via. A tentativa é recusada."""
    par = (ESTADO_CASO.PLANO_LIBERADO, ESTADO_CASO.REPROVADO_EM_REVISAO)
    assert par not in _PARES_DECLARADOS

    with pytest.raises(ErroTransicaoNaoDeclarada) as capturado:
        transicionar(*par)

    erro = capturado.value
    assert erro.de is ESTADO_CASO.PLANO_LIBERADO
    assert erro.para is ESTADO_CASO.REPROVADO_EM_REVISAO


def test_reprovado_em_revisao_e_alcancavel_apenas_a_partir_de_aguardando_revisao() -> None:
    """Fecha o critério 4 de forma exaustiva: entre os DOZE estados
    possíveis de origem, `AGUARDANDO_REVISAO` é o ÚNICO que alcança
    `REPROVADO_EM_REVISAO` — nenhum outro estado, incluindo mas não se
    limitando a `PLANO_LIBERADO`, tem essa transição declarada."""
    origens_que_alcancam_reprovado = {
        estado
        for estado in ESTADO_CASO
        if (estado, ESTADO_CASO.REPROVADO_EM_REVISAO) in _PARES_DECLARADOS
    }
    assert origens_que_alcancam_reprovado == {ESTADO_CASO.AGUARDANDO_REVISAO}


def test_reprovado_em_revisao_sai_so_de_volta_a_coleta_rf113() -> None:
    """`RF-113`, `AC-175` (`T-333`, revisa `EC-12`): a reprovação devolve o
    caso ao aluno — a ÚNICA saída de `REPROVADO_EM_REVISAO` é
    `COLETA_INICIAL`, pelo gatilho `devolve_ao_aluno`. Nenhuma volta direta
    à fila nem liberação: o reenvio passa pelo cálculo."""
    saidas = {
        t.para: t.gatilho for t in TABELA_TRANSICOES if t.de is ESTADO_CASO.REPROVADO_EM_REVISAO
    }
    assert saidas == {ESTADO_CASO.COLETA_INICIAL: "devolve_ao_aluno"}


def test_aluno_retira_o_plano_da_conferencia_so_a_partir_de_aguardando_revisao() -> None:
    """`RF-115` (T-336): `AGUARDANDO_REVISAO → COLETA_INICIAL` pelo gatilho
    `aluno_retoma_edicao`; nenhum outro estado volta à coleta por esta via, e
    `CALCULANDO` não ganha saída (o aluno espera o cálculo terminar)."""
    transicao = transicionar(ESTADO_CASO.AGUARDANDO_REVISAO, ESTADO_CASO.COLETA_INICIAL)
    assert transicao.gatilho == "aluno_retoma_edicao"
    origens = {t.de for t in TABELA_TRANSICOES if t.gatilho == "aluno_retoma_edicao"}
    assert origens == {ESTADO_CASO.AGUARDANDO_REVISAO}
    with pytest.raises(ErroTransicaoNaoDeclarada):
        transicionar(ESTADO_CASO.CALCULANDO, ESTADO_CASO.COLETA_INICIAL)


def test_aluno_nao_refaz_o_plano_depois_da_entrega() -> None:
    """`RF-409` (T-387): o gatilho `aluno_refaz_plano` (`RF-118`, T-341) saiu da
    tabela; de nenhum estado de plano entregue ou de etapa pós-plano se volta
    a `COLETA_INICIAL` pelo aluno."""
    assert not [t for t in TABELA_TRANSICOES if t.gatilho == "aluno_refaz_plano"]
    with pytest.raises(ErroTransicaoNaoDeclarada):
        transicionar(ESTADO_CASO.PLANO_LIBERADO, ESTADO_CASO.COLETA_INICIAL)
