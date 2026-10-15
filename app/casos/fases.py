"""As cinco fases do aluno — `RF-61`, `AC-89`, `EC-25` (T-146).

O protótipo validado `PIQ Meu Plano` decide o que a tela Início mostra a
partir de uma **fase**, não do estado bruto do caso: `renderInicio` tem cinco
ramos (`coleta`, `revisao`, `reprovado`, `plano`, `acompanhamento`), enquanto
`app/casos/maquina.py::ESTADO_CASO` tem nove membros. Este módulo é o mapa
entre os dois, e nada além disso.

**Por que uma fase, e não o estado direto.** O estado é a verdade da máquina —
`CALCULANDO` e `AGUARDANDO_REVISAO` são transições distintas, com guardas
distintas, e a máquina precisa dessa distinção. A fase é a verdade do **aluno**:
nos dois casos a resposta à pergunta "o que eu faço agora?" é a mesma, *é com a
gente, você não faz nada*. Colapsar os nove em cinco é o que permite a tela
Início oferecer **uma** próxima etapa (`RF-58`) em vez de expor a máquina de
estados a quem não precisa dela.

**Módulo puro.** Sem I/O, sem FastAPI, sem `engine/`, sem `persistencia/` —
mesma disciplina de `app/casos/progresso.py` e de
`app/http/mensagens_de_estado.py`. A única dependência é o próprio enum de
estados.

## A trava do `match` exaustivo

`fase_do_estado` não tem `case _`. Isso é deliberado e é o mecanismo central
de `AC-89`: um membro novo em `ESTADO_CASO` sem fase declarada **não compila**
sob `mypy --strict`, em vez de cair num default silencioso que mandaria o aluno
para a tela errada. É o mesmo padrão já provado em `mensagens_de_estado.py`.

## Nenhuma fase nova — as duas tentações recusadas

`ENCERRADO` **não** vira uma sexta fase. Ele é `ACOMPANHAMENTO` com a lista de
ações vazia. Uma fase existe para responder *o que o aluno faz agora*; o
encerramento não muda essa resposta, muda o conteúdo do cartão — e
`mensagem_do_estado_do_caso` já produz *"Seu caso foi encerrado."*.

`ERRO_DE_CALCULO` **não** vira uma tela de erro. Ele é `REVISAO`, e o aluno lê
*"Seu plano está em nova análise."* — o texto que `mensagens_de_estado.py` já
produz para esse estado. Expor erro técnico a um aluno endividado e inseguro é
escopo extra e é dano: ele não pode agir sobre a falha, e saber dela só
acrescenta medo. A falha é observável pelo operador, que é quem pode agir.

## `PLANO_LIBERADO` — sem exceção desde T-387

Com o plano definitivo (`RF-409`) a fase é função só do estado.

REGRAS: `RF-58`, `RF-61`, `AC-81`, `AC-89`, `EC-25`
"""

from __future__ import annotations

from enum import Enum
from typing import Final

from app.casos.maquina import ESTADO_CASO

REGRAS: Final[tuple[str, ...]] = ("RF-58", "RF-61", "AC-81", "AC-89", "EC-25")


class FASE_INICIO(Enum):
    """As cinco fases de `renderInicio` no protótipo validado.

    Os valores são os do protótipo, caractere por caractere — eles atravessam
    a fronteira HTTP no campo `fase` de `GET /caso/{CASO_ID}/inicio` e o
    cliente os consome como união de literais."""

    COLETA = "coleta"
    REVISAO = "revisao"
    REPROVADO = "reprovado"
    PLANO = "plano"
    ACOMPANHAMENTO = "acompanhamento"


def fase_do_estado(estado: ESTADO_CASO) -> FASE_INICIO:
    """`RF-61` — a fase do aluno para um `ESTADO_CASO`, por leitura pura.

    **`match` EXAUSTIVO, sem `case _`** — a trava de `AC-89`: membro novo sem
    fase declarada não passa no `mypy --strict`. Mesma disciplina de
    `app/http/mensagens_de_estado.py::mensagem_do_estado_do_caso`.

    `PLANO_LIBERADO` devolve `PLANO` aqui e só isso (`RF-409`, T-387): sem
    acompanhamento depois do plano, nada corrige essa fase."""
    match estado:
        # --- coleta: o aluno tem perguntas a responder ---
        case ESTADO_CASO.CADASTRADO:
            # Ainda não consentiu. A próxima etapa é o consentimento, que do
            # ponto de vista do aluno é o começo da coleta — não uma fase
            # própria: ele não distingue "registrar consentimento" de
            # "começar a responder", e nem precisa.
            return FASE_INICIO.COLETA
        case ESTADO_CASO.CONSENTIMENTO_REGISTRADO:
            return FASE_INICIO.COLETA
        case ESTADO_CASO.COLETA_INICIAL:
            # O caso canônico do protótipo: "62 de 195".
            return FASE_INICIO.COLETA

        # --- revisão: é com a equipe, o aluno não faz nada ---
        case ESTADO_CASO.CALCULANDO:
            # O aluno vê "estamos montando o seu plano". A FASE é a mesma de
            # `AGUARDANDO_REVISAO` — *você não precisa fazer nada* —; o que
            # muda é só o destino (a tela do `.pulse`).
            return FASE_INICIO.REVISAO
        case ESTADO_CASO.ERRO_DE_CALCULO:
            # Ver a nota do cabeçalho: o erro técnico nunca chega ao aluno.
            # `mensagem_do_estado_do_caso` já diz "Seu plano está em nova
            # análise.", que é verdade e é acionável — para a equipe.
            return FASE_INICIO.REVISAO
        case ESTADO_CASO.AGUARDANDO_REVISAO:
            return FASE_INICIO.REVISAO

        # --- reprovado: a equipe pediu ajuste ---
        case ESTADO_CASO.REPROVADO_EM_REVISAO:
            return FASE_INICIO.REPROVADO

        # --- plano ---
        case ESTADO_CASO.PLANO_LIBERADO:
            # `RF-409` (T-387): o plano entregue é definitivo, a fase é sempre
            # esta.
            return FASE_INICIO.PLANO

        # --- encerrado ---
        case ESTADO_CASO.ENCERRADO:
            # Ver a nota do cabeçalho: não é uma sexta fase. É acompanhamento
            # com ações vazias e a mensagem de encerramento.
            return FASE_INICIO.ACOMPANHAMENTO

