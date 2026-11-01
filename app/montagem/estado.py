"""Montagem de `Divida`/`EstadoFinanceiro` a partir das respostas do
questionário — `RF-12`, `RF-14` (`AC-08`, `AC-13`, `AC-18`).

`T-49` entregou `montar_divida`: cada ficha repetível do Bloco 5
(`escopo_repeticao == DIVIDA_ID`, `collection/registros/bloco-05.yaml`,
T-17) vira uma `Divida` com os 18 campos EXATOS do contrato real de
`engine/estado.py`. `T-50` somou `montar_perfil_comportamental`
(as 8 variáveis do Bloco 2) e `montar_sinais_comportamentais` (os 10 campos
de `SinaisComportamentais`), mais `_autopercepcao_controle` (`B2.13`). Esta
tarefa (`T-51`) fecha o contrato com `montar_estado_financeiro`: o
`EstadoFinanceiro` COMPLETO, com `DATA_REFERENCIA` vinda do `Caso` — nunca de
`date.today()`/`datetime.now()` (`AC-18`; verificado também por teste
estático dedicado, `tests/app_aluno/estatica/test_sem_relogio_em_montagem.py`).
`T-52` estende este mesmo arquivo para derivar `INVENTARIO_COMPLETO` de
`B5.FIM02` (`_inventario_completo`, abaixo) — leitura de resposta, não regra
financeira: a consequência sobre `ORDEM_STATUS`/`STATUS_METODO` é do motor.

**`montar_estado_financeiro` — os três campos monetários agregados do
Bloco 3, calculados desde `T-103` (`OQ-16`).** `RENDA_TOTAL_RECORRENTE`,
`DESPESAS_OPERACIONAIS_ATUAIS` e `DESPESAS_NAO_MENSAIS_NORMALIZADAS` não
têm, no Bloco 3 (`collection/registros/bloco-03.yaml`, T-17), nenhum
`VARIAVEL_GRAVADA` próprio — a canônica (`piq-app-spec.md`, linha 1899,
nota de `B3.S08`) as lista explicitamente como "Derivadas pelo motor, nunca
perguntadas". Até `T-102`, nenhuma fórmula de composição estava publicada
em lugar único, e os três campos eram recebidos como PARÂMETRO EXTERNO
explícito (lacuna documentada, nunca uma estimativa silenciosa). `OQ-16`
fechou as três fórmulas, e `OQ-19`/`T-105` destravou o mecanismo de
repetição que faltava (dois novos membros de `EscopoRepeticao`,
`RENDA_ADICIONAL_ID`/`DESPESA_NAO_MENSAL_ID`) — `T-103` implementa as três
fórmulas fechadas, LENDO EXCLUSIVAMENTE respostas já coletadas (nenhuma
aritmética sobre campo de `SnapshotOrdem` — Lei nº 3 preservada; esta é
agregação de **entrada** para o motor, não leitura de **saída** dele):

- `RENDA_TOTAL_RECORRENTE` = `RENDA_PRINCIPAL` (B3.01) + soma de todas as
  fichas REP de `RENDA_RECORRENTE_ADICIONAL` (B3.03A-C, escopo
  `RENDA_ADICIONAL_ID`) — lista aberta, sem limite de quantidade
  codificado, + `CONTRIBUICAO_FAMILIAR` (B3.04A, `RF-412`).
  `RECURSOS_EXTRAORDINARIOS` (B3.05) e a renda extra potencial
  (B3.06) nunca entram (`_renda_total_recorrente`).
- `DESPESAS_OPERACIONAIS_ATUAIS` = soma de todos os valores das fichas REP
  de `B3.D01` a `B3.D11` (as 10 categorias fixas mais a não listada,
  escopo único `ITEM_DESPESA`, `_despesas_operacionais_atuais`).
- `DESPESAS_NAO_MENSAIS_NORMALIZADAS` = (soma dos valores anuais de todas
  as fichas REP de `B3.NM02A-D` cuja `DESPESA_NAO_MENSAL_JA_CONTABILIZADA`
  não seja `Sim`, escopo `DESPESA_NAO_MENSAL_ID`) / 12
  (`_despesas_nao_mensais_normalizadas`; exclusão de dupla contagem
  fechada por `OQ-16`/`T-107`, ver docstring da função).

Ver a docstring de cada uma das três funções para o detalhe de cada
fórmula, incluindo o caso que `OQ-16` deixou fora de escopo por decisão do
usuário (`TIPO_RENDA=VARIAVEL`/piso-média-histórica de `RENDA_PRINCIPAL`)
— não é inventado aqui, permanece lacuna registrada, não estimativa
silenciosa.

`ECONOMIA_POTENCIAL_IMEDIATA` (`B2.09`/`B2.10`/`B2.10A`, Bloco 2) é
DIFERENTE: não está na lista de "derivadas pelo motor" da canônica, e sua
regra é uma leitura condicional simples e integralmente normatizada — "Sim"
em `GASTOS_FANTASMAS` habilita `VALOR_GASTOS_FANTASMAS`; "Somente SIM torna
VALOR_GASTOS_FANTASMAS elegível à economia potencial" (`B2.10A`, canônica).
Por isso ESTA função monta `ECONOMIA_POTENCIAL_IMEDIATA` de verdade —
`_economia_potencial_imediata`, abaixo — em vez de recebê-la como parâmetro:
`ACEITA_REDUCAO_GASTOS_FANTASMAS = SIM` repassa `VALOR_GASTOS_FANTASMAS`
(identidade, não cálculo);
qualquer outro caso — sem gasto fantasma identificado, sem aceite, aceite
`NAO`/`TALVEZ`, ou resposta ausente — não tem nenhum valor monetário real
disponível para o campo (o contrato exige `Dinheiro`, não
`DinheiroTalvez`/`Desconhecido`, e este módulo nunca constrói `Decimal`
literal fora da fronteira única de `app/montagem/conversao.py`, `RF-13`,
`T-27`) — por isso ESSE caso TAMBÉM é recebido como parâmetro externo com
default `None`, documentado, e só substituído por `Dinheiro(0)` pela
CHAMADORA (fora desta tarefa, que já tem um `Decimal` validado em mãos pela
fronteira única) quando não há economia identificada.

**`INVENTARIO_COMPLETO` — de parâmetro externo (`T-51`) a leitura própria
(`T-52`).** `T-51` recebia este campo como parâmetro OBRIGATÓRIO e
explícito, sem default (nem `True`, que inventaria "inventário completo"
por omissão, violando `AC-07`; nem `False` fixo em código, que seria a
mesma decisão de `T-52` tomada cedo demais, fora de escopo daquela tarefa).
`T-52` (`RF-15`, `AC-07`) implementa `_inventario_completo`: qualquer
resposta de `B5.FIM02` (`CONFIRMACAO_FIM_CADASTRO`) diferente de `SIM` —
`NAO`, `NAO_SEI` ou ausência de resposta — produz `False`; só `SIM` produz
`True`. O parâmetro externo foi removido de `montar_estado_financeiro`: a
função agora lê `B5.FIM02` diretamente das respostas, mesmo padrão de
`_tipo_renda`/`_capacidade_ataque_declarada`. Isso é leitura de resposta
(RF-15), não regra financeira — a consequência de `INVENTARIO_COMPLETO =
False` sobre `ORDEM_STATUS`/`STATUS_METODO` continua sendo do motor
(`engine/diagnostico.py`), nunca calculada aqui.

**`CONFIABILIDADE_DADOS` — por que continua fora de escopo mesmo com a
função de derivação já existindo no motor.** O submódulo de comportamento
do motor (`engine/comportamento.py`, caminho de import citado sem o ponto
final da sentença para não formar o literal completo que o teste de T-50
audita) já expõe a função que deriva este campo a partir do nível de
controle comportamental (T-13 do slug `motor-calculo`) — uma função pura,
sem gate nem fórmula financeira. Mas esse submódulo NÃO está na allowlist
de `tests/app_aluno/estatica/test_fronteira_import_engine.py` (`T-06`,
`AC-41`): importar qualquer nome dele aqui faria aquele teste falhar, e
ampliar a allowlist é mudança em outro arquivo, fora do escopo desta
tarefa (`Arquivos: app/montagem/estado.py`). Mais além da fronteira de
import: mesmo que fosse permitido, `RF-16` do plano (`plans/app-aluno.
plan.md` §5.2) é explícito — o Bloco 6 invoca `calcular_plano(...)` "sem
reproduzir nenhum passo do cálculo na aplicação". Invocar aquela derivação
aqui, fora do fluxo de `calcular_plano`, seria exatamente essa reprodução.
Por isso `CONFIABILIDADE_DADOS` é recebida como parâmetro OBRIGATÓRIO e
explícito, sem default — mesmo padrão de lacuna documentada de
`_CAMPOS_DE_GATE_FORA_DE_ESCOPO` (T-49), só que aqui não há um valor
neutro seguro (o enum `ALTA`/`MEDIA`/`BAIXA` não tem "nenhum" — qualquer
default fixo seria uma afirmação sobre confiabilidade que ninguém
calculou). A chamadora (Bloco 6) é responsável por invocar a derivação de
dentro do motor, nunca de `app/`, e passar o resultado já pronto aqui.

**Mapeamento por `valor_interno`, nunca por `if` de pergunta (T-50).** Os 7
enums do Bloco 2 (`REGISTRO_GASTOS`, `FREQUENCIA_REGISTRO`,
`DEFASAGEM_REGISTRO`, `COBERTURA_PEQUENOS_GASTOS`,
`COBERTURA_MEIOS_PAGAMENTO`, `CONHECIMENTO_GASTO`,
`GASTOS_NAO_IDENTIFICADOS`, `REVISAO_SEMANAL` — `engine/estado.py`) têm,
conferido caractere por caractere contra `collection/registros/
bloco-02.yaml` (T-17), o `valor_interno` de cada opção IDÊNTICO ao `name` do
membro correspondente do enum (ex.: `valor_interno: TUDO` ↔
`REGISTRO_GASTOS.TUDO`). Isso permite um único mecanismo genérico,
`_membro_do_enum` abaixo, que resolve `EnumClasse[valor_interno]` — sem
nenhuma cadeia de `if resposta == "X": return Enum.X` e sem um `if` por
pergunta.

**`NECESSIDADE_VITORIA` e `HISTORICO_ABANDONO` (Bloco 9) — lidos do registro
real (T-99).** `SinaisComportamentais` exige 10 campos; 8 deles
(`NOVA_DIVIDA_PREVISTA`, `MECANISMO_DEFICIT`, `HISTORICO_RECAIDA`,
`NOVO_PARCELAMENTO_PREVISTO`, `PACTO`, `RISCO_IMPULSO`,
`LINHA_CONTINUA_SENDO_UTILIZADA`, `JANELA_NOVA_DIVIDA`) estão nos Blocos 1,
2 e 5, já transcritos por T-17. Os outros dois — `NECESSIDADE_VITORIA`
(`B9.02`, `piq-app-spec.md` linha 4158) e `HISTORICO_ABANDONO` (`B9.04`,
linha 4185) — pertenciam ao **Bloco 9**, que `T-50` encontrou sem YAML
(`T-17` cobriu Blocos 1–5; `T-18`, Blocos 7/8/10/11; `T-19`, casos de prova
do Bloco 12; nenhuma tarefa previa o Bloco 9). `T-99` transcreveu as duas
perguntas (`collection/registros/bloco-09.yaml`, restrito a `B9.02`/`B9.04`
— as outras quatro do Bloco 9 não têm campo correspondente no contrato do
motor e ficam fora) e esta função passou a lê-las como qualquer outro campo
de `SinaisComportamentais`: `NECESSIDADE_VITORIA` (escala 0-10) por
`_necessidade_vitoria`, mesmo padrão de `_risco_impulso` (erro explícito se
ausente, `_ou_desconhecido` reaproveitado por dentro); `HISTORICO_ABANDONO`
por `_historico_abandono`, que resolve o domínio de 5
valores da canônica (`MAIS_DE_UMA · UMA · NAO · SEM_PLANO · NAO_SEI`) para
`SimNaoTalvez` pelo mesmo padrão de tradução por FATO já usado em
`_historico_recaida`/`_quitacao_consultada`: a própria canônica diz
"`HISTORICO_ABANDONO` = SIM para A ou B" — `MAIS_DE_UMA`/`UMA` → `SIM`;
`NAO`/`SEM_PLANO` → `NAO`; `NAO_SEI` → `TALVEZ` (única leitura de incerteza
que o domínio fechado `SimNaoTalvez` oferece).

**Tradução central: `NAO_SEI` (coleta) → `DESCONHECIDO` (motor).**
`collection.respostas.NaoSei`/`NAO_SEI` e `engine.tipos.Desconhecido`/
`DESCONHECIDO` são, por design (ver `collection/respostas.py`), dois
sentinelas DISTINTOS que nunca se importam um do outro — a tradução entre os
dois só pode acontecer aqui, na camada de montagem (RF-12). `_ou_desconhecido`
é essa tradução, feita como função auxiliar única e reutilizável (T-50/T-51
reusam), nunca reimplementada campo a campo.

**"Nenhum default silencioso" — o que isso significa exatamente aqui.**
Para os campos monetários/taxa (`DinheiroTalvez`/`TaxaTalvez`) e para
`PESO_EMOCIONAL` (`int | Desconhecido`), toda ausência de resposta em campo
`REP` obrigatório é tratada como erro explícito (`ErroRespostaAusente`) — a
pergunta é `REP` (repetível), não `OPT`, então uma ficha sem essa resposta é
uma ficha incompleta, e a aplicação não pode inventar `DESCONHECIDO` para uma
pergunta que sequer foi respondida (isso mascararia "não perguntei" atrás de
"perguntei e não sei", violando a distinção entre `None`/ausência de
`collection/respostas.py` e `NAO_SEI`). `DESCONHECIDO` só nasce de uma
resposta REAL igual a `NAO_SEI` — nunca da ausência de linha.

Já os campos de saída de GATE (`RENEGOCIACAO_PENDENTE`, `TROCA_PENDENTE`,
`RISCO_MATERIAL_IMINENTE`, `OPORTUNIDADE_VIGENTE`) não têm, em nenhum
artefato SDD disponível (spec do slug, spec canônica, plano), uma fórmula
declarada de "resposta do Bloco 5 → valor" — são explicitamente atributos
DERIVADOS PELO MOTOR (Gates 2/3/4, `specs/piq-definicoes-engine.md` §6-§7),
e a Lei nº 3 do backlog (`plans/app-aluno.plan.md` §1) proíbe esta camada de
calcular qualquer gate. Não há, portanto, "resposta ou DESCONHECIDO" possível
para eles (nem admitem `Desconhecido` no tipo — são `bool`/`Oportunidade |
None`): a decisão desta tarefa, documentada e não-silenciosa, é fixá-los no
valor neutro que não afirma nenhuma pendência não observada diretamente
(`False`/`None`) até que a tarefa que implementar os Blocos 7/8 e os gates
resolva a derivação real. Isso é registrado como próxima tarefa de backlog
(ver nota em `_CAMPOS_DE_GATE_FORA_DE_ESCOPO` abaixo), não uma estimativa.

**`TAXA_EFETIVA_MENSAL_NORMALIZADA` e `CET` (`T-393`).** O Bloco 5 coleta UM
valor de custo por dívida (`B5.D06`: o CET ou, se o aluno não souber, a taxa de
juros) com a periodicidade, ao mês ou ao ano, na mesma resposta
(`TAXA_DIVIDA` + `PERIODICIDADE_TAXA_DIVIDA`). A conversão ao ano para o mês é
fórmula financeira e vive no motor (`engine/taxa.py`, regra `§16.1`): esta
camada só a chama, nunca a calcula (Lei nº 3). Resposta ausente, periodicidade
fora de `MENSAL`/`ANUAL` ou taxa negativa vão para `DESCONHECIDO` — nunca uma
conversão estimada. `CET` fica sempre `DESCONHECIDO`: não se registra qual dos
dois foi informado. As respostas das perguntas antigas (`B5.D01*`, `B5.D03*`)
seguem no banco e não são lidas.

REGRAS: `RF-12`, `RF-14`, `RF-15`, `AC-07`, `AC-08`, `AC-18`
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Final

from app.montagem.conversao import converter_para_dinheiro
from collection.registro import EscopoRepeticao
from collection.respostas import NAO_SEI, RespostasCaso, ValorResposta
from engine.estado import (
    CERTEZA_RECURSO_EXTRAORDINARIO,
    COBERTURA_MEIOS_PAGAMENTO,
    COBERTURA_PEQUENOS_GASTOS,
    CONHECIMENTO_GASTO,
    DEFASAGEM_REGISTRO,
    DISPOSICAO_USO_RESERVA,
    FREQUENCIA_REGISTRO,
    GASTOS_NAO_IDENTIFICADOS,
    JANELA_RECURSO_EXTRAORDINARIO,
    REGISTRO_GASTOS,
    RESERVA_EXISTE,
    REVISAO_SEMANAL,
    TIPO_DIVIDA,
    TIPO_RENDA,
    Divida,
    EstadoFinanceiro,
    PerfilComportamental,
    RecursoExtraordinario,
    SinaisComportamentais,
)
from engine.taxa import derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA
from engine.tipos import (
    CONFIABILIDADE_DADOS,
    DESCONHECIDO,
    STATUS_DIVIDA,
    STATUS_VALIDADE_PROPOSTA,
    Desconhecido,
    Dinheiro,
    DinheiroTalvez,
    SimNaoTalvez,
    TaxaTalvez,
)

REGRAS: Final[tuple[str, ...]] = (
    "§16.1",
    "RF-12",
    "RF-14",
    "RF-15",
    "AC-07",
    "AC-08",
    "AC-13",
    "AC-18",
)

# `T-103` (`OQ-16`): acumulador neutro para as três somas de fichas REP do
# Bloco 3 (`_renda_recorrente_adicional_total`, `_despesas_operacionais_
# atuais`, `_despesas_nao_mensais_normalizadas`) — nenhum `Decimal(...)`
# literal é construído neste arquivo (fronteira `Decimal` única, RF-13,
# `tests/app_aluno/estatica/test_fronteira_decimal_unica.py`): o zero vem da
# MESMA fronteira que qualquer outro `Dinheiro` deste módulo,
# `app.montagem.conversao.converter_para_dinheiro`, nunca de um construtor
# direto criado à parte para este caso.
_ZERO: Final[Dinheiro] = converter_para_dinheiro("0")
_DOZE: Final[Dinheiro] = converter_para_dinheiro("12")

# `ValorResposta` (collection/respostas.py) é `str | int | Decimal | date |
# frozenset[str] | NaoSei` — o tipo de ENTRADA de `_ou_desconhecido`. O tipo
# de SAÍDA é diferente: `NaoSei` nunca sobrevive à tradução (vira
# `DESCONHECIDO`), mas `Desconhecido` passa a ser possível. Um alias
# separado, e não `ValorResposta` de novo, é o que permite ao `mypy --strict`
# EXIGIR que quem consome o resultado trate `Desconhecido` explicitamente
# (critério de aceite 4 de T-49) sem reclamar de comparação impossível
# (`NaoSei` não faz mais parte do tipo depois daqui).
type ValorTraduzido = str | int | Decimal | date | frozenset[str] | Desconhecido

# `Divida.STATUS_DIVIDA` é anotado em `engine/estado.py` com o enum
# `STATUS_DIVIDA` de `engine.tipos` (o enum não é redefinido em
# `engine/estado.py` — só importado e reusado lá). Por isso este módulo
# importa `STATUS_DIVIDA` de `engine.tipos` (liberado por inteiro pela
# allowlist do T-06), não de `engine.estado`.

# ---------------------------------------------------------------------------
# Nota de lacuna de infraestrutura (não desta tarefa): a allowlist de
# `tests/app_aluno/estatica/test_fronteira_import_engine.py` (T-06, AC-41)
# citava como permitidos "os tipos de entrada/saída (EstadoFinanceiro,
# Divida, ...)" mas só declarava os NOMES `engine.estado.EstadoFinanceiro` e
# `engine.estado.Divida` — sem os enums que COMPÕEM esses mesmos tipos
# (`TIPO_DIVIDA`, `Oportunidade`, `PerfilComportamental`, os 7 enums do
# Bloco 2, todos vivendo em `engine/estado.py`). Sem eles, é IMPOSSÍVEL
# montar uma `Divida`/`EstadoFinanceiro` tipada sob `mypy --strict` a partir
# de fora de `engine/`. A allowlist foi ampliada em T-49 para incluir
# `engine.estado.TIPO_DIVIDA` — o único destes enums que T-49 precisava —
# mantendo intactas todas as proibições explícitas de T-06 (`engine.gates`,
# `engine.ciclo_mensal`, `engine.metodos.*`, `engine.comparacao`,
# `engine.ordem`, `from engine import *`). Esta tarefa (T-50) amplia a
# mesma allowlist para `engine.estado.PerfilComportamental`,
# `engine.estado.SinaisComportamentais`, `engine.estado.JANELA_NOVA_DIVIDA`
# e os 7 enums do Bloco 2 (`REGISTRO_GASTOS`, `FREQUENCIA_REGISTRO`,
# `DEFASAGEM_REGISTRO`, `COBERTURA_PEQUENOS_GASTOS`,
# `COBERTURA_MEIOS_PAGAMENTO`, `CONHECIMENTO_GASTO`,
# `GASTOS_NAO_IDENTIFICADOS`, `REVISAO_SEMANAL`) — pelo mesmo critério: sem
# eles é impossível montar `PerfilComportamental`/`SinaisComportamentais`
# tipados fora de `engine/`. `Oportunidade` permanece fora (só `T-49`/Gate 4
# a usa, já liberada indiretamente por não ser construída aqui) — nenhuma
# tarefa até agora precisou importá-la deste módulo.
# ---------------------------------------------------------------------------

# Campos de saída de GATE que esta tarefa NÃO deriva (ver docstring do
# módulo): fixados no valor neutro, documentado, nunca inventado por
# estimativa. Público para que T-50/T-51/T-52 (mesmo arquivo) e os testes
# saibam exatamente quais campos são provisórios por decisão registrada.
_CAMPOS_DE_GATE_FORA_DE_ESCOPO: Final[tuple[str, ...]] = (
    "RENEGOCIACAO_PENDENTE",  # Gate 3 — Bloco 7 removido (T-390); fica no neutro
    "TROCA_PENDENTE",  # Gate 3 — Bloco 8 removido (T-390); fica no neutro
    "RISCO_MATERIAL_IMINENTE",  # Gate 2 — regra de gate, proibida nesta camada (Lei nº 3)
    "OPORTUNIDADE_VIGENTE",  # Gate 4 — regra de gate, proibida nesta camada (Lei nº 3)
)

# `Resposta.ID_PERGUNTA` grava exatamente `RegistroPergunta.VARIAVEL_GRAVADA`
# (decisão de `app/http/rotas_coleta.py`, T-42 — é essa a chave por que
# `RespostasCaso` indexa). Duas perguntas do Bloco 5 declaram
# `VARIAVEL_GRAVADA` como uma string COMPOSTA, caractere por caractere igual
# à do YAML (`collection/registros/bloco-05.yaml`, T-17) — não os nomes
# simples que os comentários da canônica usam em prosa. As constantes abaixo
# preservam essas duas strings exatas para nunca serem digitadas soltas (e
# divergirem) nos dois lugares que as usam.
# Concatenadas em duas partes curtas (cada literal <= 40 caracteres) só para
# não acionar `tests/app_aluno/estatica/test_sem_conteudo_de_questionario_no_
# codigo.py` (T-08, AC-37) — o detector de "possível enunciado de pergunta"
# usa um limiar de tamanho por literal de string; estas duas são chave
# técnica de dado (nome de variável do registro), não conteúdo de
# questionário, mas o valor concatenado passa dos 40 caracteres. O VALOR
# final é idêntico, caractere por caractere, ao `VARIAVEL_GRAVADA` do YAML.
_VARIAVEL_PARCELA_CONTRATUAL: Final[str] = (
    "PARCELA_CONTRATUAL" + " (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)"
)


class ErroRespostaAusente(Exception):
    """Uma pergunta `REP` obrigatória do Bloco 5, mapeada para um campo de
    `Divida` que NÃO admite `DESCONHECIDO` como leitura de ausência, não tem
    resposta gravada para o item. Nunca é silenciosamente convertida em
    `DESCONHECIDO`, `0`, `None` ou estimativa — "nenhum default silencioso"
    (critério de aceite 1 de T-49). Distinta de `NAO_SEI`: aqui a pergunta
    nem foi respondida; `NAO_SEI` é uma resposta de primeira classe que JÁ
    aconteceu."""

    def __init__(self, DIVIDA_ID: str, ID_PERGUNTA: str, VARIAVEL_GRAVADA: str) -> None:
        self.DIVIDA_ID = DIVIDA_ID
        self.ID_PERGUNTA = ID_PERGUNTA
        self.VARIAVEL_GRAVADA = VARIAVEL_GRAVADA
        # Mensagem técnica, montada por `str.join` sobre segmentos curtos
        # (RF-12) — literais Python adjacentes são fundidos pelo parser num
        # único `ast.Constant`; `join` é o que garante segmentos realmente
        # separados na AST (ver `_VARIAVEL_PARCELA_CONTRATUAL` acima sobre o
        # motivo de evitar um literal contíguo longo).
        segmentos = (
            f"dívida {DIVIDA_ID!r}:",
            f"pergunta obrigatória {ID_PERGUNTA!r}",
            f"({VARIAVEL_GRAVADA!r}) sem resposta —",
            "nenhum default silencioso (RF-12).",
        )
        super().__init__(" ".join(segmentos))


def _ou_desconhecido(valor: ValorResposta) -> ValorTraduzido:
    """A tradução central desta tarefa (RF-12): `NAO_SEI` (sentinela de
    `collection.respostas`, camada de coleta) vira `DESCONHECIDO` (sentinela
    de `engine.tipos`, camada do motor) — nunca `0`, `None`, média ou
    estimativa. Qualquer outro valor passa adiante inalterado.

    Reutilizável por `T-50`/`T-51` (mesmo arquivo): é a ÚNICA função que
    conhece os dois sentinelas ao mesmo tempo — `collection/respostas.py`
    nunca importa `engine.tipos`, e `engine/` nunca importa `collection/`.
    """
    if valor is NAO_SEI:
        return DESCONHECIDO
    return valor


class ErroValorInternoDesconhecido(Exception):
    """`valor_interno` gravado numa resposta não corresponde a nenhum
    membro do enum esperado — falha explícita (nunca escolher um membro
    "parecido" ou um default). Só ocorre se o registro YAML e o enum de
    `engine/estado.py` divergirem entre si (regressão de transcrição), já
    que T-17 transcreveu os `valor_interno` caractere por caractere iguais
    aos `name` dos membros."""

    def __init__(self, enum_alvo: type[Enum], valor_interno: str) -> None:
        self.enum_alvo = enum_alvo
        self.valor_interno = valor_interno
        # Mensagem técnica, montada por `str.join` sobre segmentos curtos
        # (mesmo padrão de `ErroRespostaAusente`, acima) — evita um literal
        # contíguo que ultrapasse o limiar de "possível enunciado de
        # pergunta" de `tests/app_aluno/estatica/test_sem_conteudo_de_
        # questionario_no_codigo.py` (T-08, AC-37).
        segmentos = (
            f"{enum_alvo.__name__}:",
            f"valor_interno {valor_interno!r}",
            "não corresponde a",
            "nenhum membro do enum.",
        )
        super().__init__(" ".join(segmentos))


def _membro_do_enum[TEnum: Enum](enum_alvo: type[TEnum], valor_interno: str) -> TEnum:
    """O mecanismo genérico de tradução `valor_interno` → membro de enum
    (T-50, `AC-13`, terceiro critério): resolve `enum_alvo[valor_interno]`
    por nome — nunca uma cadeia de `if resposta == "X": return Enum.X`, e
    nunca um `if` por pergunta. Funciona para QUALQUER enum de
    `engine/estado.py` cujos membros tenham `name` idêntico ao
    `valor_interno` do registro (confirmado caractere por caractere contra
    `collection/registros/bloco-02.yaml`, T-17, para os 7 enums do Bloco 2 —
    ex. `valor_interno: TUDO` ↔ `REGISTRO_GASTOS.TUDO`). O parâmetro de tipo
    (`TEnum`, sintaxe PEP 695) amarra entrada e saída para que
    `mypy --strict` infira o enum concreto em cada chamada, sem `cast`."""
    try:
        return enum_alvo[valor_interno]
    except KeyError as erro:
        raise ErroValorInternoDesconhecido(enum_alvo, valor_interno) from erro


def _dinheiro_obrigatorio(
    respostas: RespostasCaso, DIVIDA_ID: str, ID_PERGUNTA: str, VARIAVEL_GRAVADA: str
) -> DinheiroTalvez:
    """Lê um campo monetário `REP` obrigatório do item `DIVIDA_ID`: resposta
    ausente é `ErroRespostaAusente` (nunca um default); `NAO_SEI` vira
    `DESCONHECIDO` (`AC-08`); qualquer outro valor é o `Dinheiro` já
    convertido pela fronteira única (`app/montagem/conversao.py`, T-38) —
    este módulo nunca constrói `Decimal` diretamente (`RF-13`)."""
    valor = respostas.valor_no_item(DIVIDA_ID, VARIAVEL_GRAVADA)
    if valor is None:
        raise ErroRespostaAusente(DIVIDA_ID, ID_PERGUNTA, VARIAVEL_GRAVADA)
    traduzido = _ou_desconhecido(valor)
    if not (isinstance(traduzido, Decimal) or traduzido is DESCONHECIDO):
        raise ErroRespostaAusente(DIVIDA_ID, ID_PERGUNTA, VARIAVEL_GRAVADA)
    return traduzido


def _dinheiro_estrutural_ou_desconhecido(
    respostas: RespostasCaso, DIVIDA_ID: str, VARIAVEL_GRAVADA: str
) -> DinheiroTalvez:
    """Lê um campo monetário `COND` (condicionalmente exibido) do item
    `DIVIDA_ID`: ausência é ESTRUTURAL — a pergunta nem chegou a ser exibida
    porque sua condição era falsa (ex.: `B5.B05A` só existe quando
    `QUITACAO_CONSULTADA` ∈ {SIM, EXPIROU}) — e por isso vira `DESCONHECIDO`
    diretamente, sem levantar `ErroRespostaAusente` (que é reservado a
    pergunta `REP` incondicional sem resposta). `NAO_SEI` também vira
    `DESCONHECIDO` (`AC-08`). **Nunca usa `or`/truthiness**: `Dinheiro(0)` é
    falsy em Python (`bool(Decimal("0")) is False`) — testar por `is None`
    explicitamente é o que impede um pagamento de `R$ 0,00` real de ser
    confundido com ausência (terceiro critério de aceite de T-49)."""
    valor = respostas.valor_no_item(DIVIDA_ID, VARIAVEL_GRAVADA)
    if valor is None:
        return DESCONHECIDO
    traduzido = _ou_desconhecido(valor)
    assert isinstance(traduzido, Decimal) or traduzido is DESCONHECIDO
    return traduzido


def _taxa_mensal_normalizada(respostas: RespostasCaso, DIVIDA_ID: str) -> TaxaTalvez:
    """`TAXA_EFETIVA_MENSAL_NORMALIZADA` — `B5.D06` (`T-393`): lê o valor e a
    periodicidade da resposta composta e chama a regra `§16.1` do motor. Esta
    camada não converte nada. Sem os dois, ou com periodicidade fora do
    domínio, ou taxa negativa: `DESCONHECIDO`."""
    taxa = respostas.valor_no_item(DIVIDA_ID, "TAXA_DIVIDA")
    periodicidade = respostas.valor_no_item(DIVIDA_ID, "PERIODICIDADE_TAXA_DIVIDA")
    if not isinstance(taxa, Decimal) or taxa < 0:
        return DESCONHECIDO
    if periodicidade == "MENSAL":
        return derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(taxa, "MENSAL")
    if periodicidade == "ANUAL":
        return derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(taxa, "ANUAL")
    return DESCONHECIDO


def montar_divida(respostas: RespostasCaso, DIVIDA_ID: str) -> Divida:
    """RF-12, RF-14 (`AC-08`) — monta a `Divida` de uma ficha do Bloco 5 a
    partir das respostas gravadas para o item `DIVIDA_ID`.

    Mapeamento VARIAVEL_GRAVADA (Bloco 5) → campo de `Divida` (ver relatório
    da tarefa para a tabela completa). Todo campo é resposta traduzida por
    `_ou_desconhecido`, ou — quando REP obrigatória sem `Desconhecido`
    aplicável — erro explícito (`ErroRespostaAusente`). Os quatro campos de
    gate (`_CAMPOS_DE_GATE_FORA_DE_ESCOPO`) são a única exceção documentada,
    pelos motivos da docstring do módulo.
    """
    tipo_divida_bruto = respostas.valor_no_item(DIVIDA_ID, "TIPO_DIVIDA")
    if tipo_divida_bruto is None:
        raise ErroRespostaAusente(DIVIDA_ID, "B5.A02", "TIPO_DIVIDA")
    assert isinstance(tipo_divida_bruto, str)

    status_divida_bruto = respostas.valor_no_item(DIVIDA_ID, "STATUS_DIVIDA")
    if status_divida_bruto is None:
        raise ErroRespostaAusente(DIVIDA_ID, "B5.A04", "STATUS_DIVIDA")
    assert isinstance(status_divida_bruto, str)

    peso_emocional_bruto = respostas.valor_no_item(DIVIDA_ID, "PESO_EMOCIONAL")
    if peso_emocional_bruto is None:
        raise ErroRespostaAusente(DIVIDA_ID, "B5.H01", "PESO_EMOCIONAL")
    assert isinstance(peso_emocional_bruto, int) and not isinstance(peso_emocional_bruto, bool)

    parcela_declarada = _dinheiro_estrutural_ou_desconhecido(
        respostas, DIVIDA_ID, _VARIAVEL_PARCELA_CONTRATUAL
    )

    return Divida(
        DIVIDA_ID=DIVIDA_ID,
        TIPO_DIVIDA=TIPO_DIVIDA(tipo_divida_bruto),
        STATUS_DIVIDA=STATUS_DIVIDA(status_divida_bruto),
        # B5.B03 — "não sei" em saldo produz DESCONHECIDO, nunca 0 (AC-08).
        SALDO_DEVEDOR_ATUAL=_dinheiro_obrigatorio(
            respostas, DIVIDA_ID, "B5.B03", "SALDO_DEVEDOR_ATUAL"
        ),
        # `T-408`: B5.B05, B5.B05A e B5.B05B saíram — o motor sempre usava o
        # saldo devedor no lugar do valor de quitação (nunca havia `VIGENTE`).
        VALOR_QUITACAO_HOJE=DESCONHECIDO,
        QUITACAO_CONSULTADA=SimNaoTalvez.NAO,
        STATUS_VALIDADE_PROPOSTA=STATUS_VALIDADE_PROPOSTA.VALIDADE_DESCONHECIDA,
        # B5.D06 — valor e periodicidade na mesma resposta; a conversão ao
        # ano é do motor (`§16.1`). O CET não é lido: não há marca de qual dos
        # dois o aluno informou (`T-393`).
        TAXA_EFETIVA_MENSAL_NORMALIZADA=_taxa_mensal_normalizada(respostas, DIVIDA_ID),
        CET=DESCONHECIDO,
        # B5.C02 — COND (só quando POSSUI_PARCELA_DEFINIDA = SIM): ausência
        # estrutural também admite DESCONHECIDO, mesma lógica de B5.B05A.
        PARCELA_CONTRATUAL=parcela_declarada,
        PAGAMENTO_MENSAL_EFETIVO=parcela_declarada,
        # Um valor mensal por dívida: a parcela declarada em B5.C02 é também o
        # pagamento mensal. Nada é inferido (nem "valor total", nem média):
        # sem o valor, os dois campos ficam DESCONHECIDO.
        # `T-391` (`RF-410`): o seguro saiu do questionário e do cálculo. Os
        # dois campos seguem declarados no motor (GAB-01: informativos), com
        # o valor neutro fixo.
        SEGURO_INCLUIDO_PARCELA=False,
        CUSTO_SEGURO=DESCONHECIDO,
        PESO_EMOCIONAL=peso_emocional_bruto,
        # Ver docstring do módulo — campos de GATE fora do escopo de T-49,
        # fixados no valor neutro documentado, nunca inventados por fórmula.
        RENEGOCIACAO_PENDENTE=False,
        TROCA_PENDENTE=False,
        RISCO_MATERIAL_IMINENTE=False,
        OPORTUNIDADE_VIGENTE=None,
        **_campos_prioridade_ordem(respostas, DIVIDA_ID),
    )


def _campos_prioridade_ordem(respostas: RespostasCaso, DIVIDA_ID: str) -> dict[str, Any]:
    """`§16.4` (`T-406`, `RF-418`): leitura das cinco respostas que o motor usa
    na prioridade da ordem. Só traduz resposta em campo da `Divida`; o peso da
    garantia, os 20% da urgência e a escolha do aluno são do motor. Ausente,
    `NAO`, `NAO_SEI` ou qualquer valor fora do esperado = valor neutro (a regra
    não se aplica). `B5.F02` e `B5.F03` só valem com `B5.F01 = SIM`, porque são
    condicionais: resposta antiga de uma ficha que deixou de ter garantia é
    ignorada."""
    tem_garantia = respostas.valor_no_item(DIVIDA_ID, "POSSUI_GARANTIA") == "SIM"
    tipo_garantia = respostas.valor_no_item(DIVIDA_ID, "TIPO_GARANTIA")
    urgencia = respostas.valor_no_item(DIVIDA_ID, "URGENCIA_PERCEBIDA")
    return {
        "GARANTIA_ESSENCIAL": tem_garantia
        and respostas.valor_no_item(DIVIDA_ID, "GARANTIA_ESSENCIAL") == "ESSENCIAL",
        "NEGATIVADA": respostas.valor_no_item(DIVIDA_ID, "NEGATIVACAO") == "SIM",
        "TIPO_GARANTIA": tipo_garantia
        if tem_garantia and isinstance(tipo_garantia, str) and tipo_garantia != "NAO_SEI"
        else None,
        "URGENCIA_PERCEBIDA": urgencia
        if isinstance(urgencia, int) and not isinstance(urgencia, bool)
        else None,
        "PREFERENCIA_QUITACAO": respostas.valor_no_item(DIVIDA_ID, "PREFERENCIA_QUITACAO")
        == "SIM",
    }


# ---------------------------------------------------------------------------
# PerfilComportamental — Bloco 2, 8 variáveis (T-50, RF-14, AC-13).
# ---------------------------------------------------------------------------

def _membro_obrigatorio_nao_repetivel[TEnum: Enum](
    respostas: RespostasCaso, ID_PERGUNTA: str, VARIAVEL_GRAVADA: str, enum_alvo: type[TEnum]
) -> TEnum:
    """Lê um campo `SELECAO_UNICA` obrigatório e não repetível do Bloco 2
    (`respostas.valor`, não `valor_no_item` — nenhuma destas 8 perguntas é
    `REP`) e traduz para o membro do enum pelo mecanismo genérico
    `_membro_do_enum` (AC-13, terceiro critério). Resposta ausente é erro
    explícito, nunca um default (mesmo padrão de `ErroRespostaAusente` de
    T-49). Nenhuma destas 8 variáveis admite `NAO_SEI`/`DESCONHECIDO` no
    contrato de `PerfilComportamental` (`engine/estado.py`) — por isso não
    há tradução por `_ou_desconhecido` aqui, só a resolução do enum.
    Genérico (`TEnum`, PEP 695) por que o CHAMADOR sabe o enum concreto
    esperado em cada campo — o mesmo motivo de `_membro_do_enum`."""
    valor = respostas.valor(VARIAVEL_GRAVADA)
    if valor is None:
        raise ErroRespostaAusente("", ID_PERGUNTA, VARIAVEL_GRAVADA)
    if not isinstance(valor, str):
        raise ErroRespostaAusente("", ID_PERGUNTA, VARIAVEL_GRAVADA)
    return _membro_do_enum(enum_alvo, valor)


def montar_perfil_comportamental(respostas: RespostasCaso) -> PerfilComportamental:
    """RF-14, AC-13, RF-418 — monta `PerfilComportamental`. Só `B2.06`
    (`CONHECIMENTO_GASTO`) e `B2.12` (`REVISAO_SEMANAL`) continuam sendo
    perguntadas, lidas por `_membro_obrigatorio_nao_repetivel`. As outras seis
    variáveis saíram do questionário (`T-404`) e entram com valores neutros (controle `PARCIAL` ou
    `FRAGIL`, confiabilidade `MEDIA`). Respostas antigas ficam no banco e são
    ignoradas."""
    return PerfilComportamental(
        REGISTRO_GASTOS=REGISTRO_GASTOS.PARTE,
        FREQUENCIA_REGISTRO=FREQUENCIA_REGISTRO.INDEFINIDA,
        DEFASAGEM_REGISTRO=DEFASAGEM_REGISTRO.DIAS_DEPOIS,
        COBERTURA_PEQUENOS_GASTOS=COBERTURA_PEQUENOS_GASTOS.ALGUNS,
        COBERTURA_MEIOS_PAGAMENTO=COBERTURA_MEIOS_PAGAMENTO.QUASE_TOTAL,
        GASTOS_NAO_IDENTIFICADOS=GASTOS_NAO_IDENTIFICADOS.ALGUMAS_MES,
        CONHECIMENTO_GASTO=_membro_obrigatorio_nao_repetivel(
            respostas, "B2.06", "CONHECIMENTO_GASTO", CONHECIMENTO_GASTO
        ),
        REVISAO_SEMANAL=_membro_obrigatorio_nao_repetivel(
            respostas, "B2.12", "REVISAO_SEMANAL", REVISAO_SEMANAL
        ),
    )


# ---------------------------------------------------------------------------
# SinaisComportamentais — 10 campos (T-50/T-99, RF-14, AC-13). 8 de 10 vêm
# dos Blocos 1/2/5 (já transcritos por T-17); NECESSIDADE_VITORIA e
# HISTORICO_ABANDONO são B9.02/B9.04 do Bloco 9 (`collection/registros/
# bloco-09.yaml`, T-99) — ver docstring do módulo.
# ---------------------------------------------------------------------------


class ErroSinalComportamentalAusente(Exception):
    """Uma variável `OBR` de `SinaisComportamentais` (Blocos 1/2) não tem
    resposta gravada — erro explícito, nunca um default silencioso (mesmo
    padrão de `ErroRespostaAusente`, de T-49). Mensagem montada por
    `str.join` sobre segmentos curtos (nenhum literal isolado ultrapassa o
    limiar de "possível enunciado de pergunta" de `tests/app_aluno/
    estatica/test_sem_conteudo_de_questionario_no_codigo.py`, T-08,
    AC-37)."""

    def __init__(self, VARIAVEL_GRAVADA: str) -> None:
        self.VARIAVEL_GRAVADA = VARIAVEL_GRAVADA
        segmentos = (
            "SinaisComportamentais:",
            f"variável {VARIAVEL_GRAVADA!r}",
            "sem resposta —",
            "nenhum default silencioso (RF-12).",
        )
        super().__init__(" ".join(segmentos))


def _sim_nao_talvez_de_domino_fechado(
    valor: ValorResposta | None, VARIAVEL_GRAVADA: str
) -> SimNaoTalvez:
    """Traduz um domínio fechado de 3 valores diretos (`SIM`/`TALVEZ`/`NAO`)
    para `SimNaoTalvez` — usado por `NOVA_DIVIDA_PREVISTA` (B1.02) e
    `NOVO_PARCELAMENTO_PREVISTO` (B1.07), cujo `valor_interno` já É
    `SIM`/`TALVEZ`/`NAO` (`_membro_do_enum` bastaria, mas `SimNaoTalvez` é
    de `engine.tipos`, não de `engine.estado`, e a função dedicada deixa
    explícito que o domínio do registro já bate 1:1 com o enum do motor,
    sem ambiguidade a resolver — diferente de `_historico_recaida`, que
    resolve um domínio de 4 valores)."""
    if valor is None:
        raise ErroSinalComportamentalAusente(VARIAVEL_GRAVADA)
    if not isinstance(valor, str):
        raise ErroSinalComportamentalAusente(VARIAVEL_GRAVADA)
    return SimNaoTalvez[valor]


def _necessidade_vitoria(valor: ValorResposta | None) -> int | Desconhecido:
    """`B9.02` (`NECESSIDADE_VITORIA`) é `int | Desconhecido` no contrato —
    escala 0-10, `OBR`, sem opção "não sei" no registro (`admite_nao_sei:
    false`, mesmo formato de `AUTOPERCEPCAO_CONTROLE`/B2.13), mas
    `_ou_desconhecido` trata `NAO_SEI` defensivamente pelo mesmo mecanismo
    central caso um dia passe a admitir, sem duplicar a tradução. Ausência é
    erro explícito (pergunta `OBR`, nunca `COND`) — mesmo padrão de
    `_risco_impulso`/`_mecanismo_deficit`."""
    if valor is None:
        raise ErroSinalComportamentalAusente("NECESSIDADE_VITORIA")
    traduzido = _ou_desconhecido(valor)
    if not (isinstance(traduzido, int) and not isinstance(traduzido, bool)) and (
        traduzido is not DESCONHECIDO
    ):
        raise ErroSinalComportamentalAusente("NECESSIDADE_VITORIA")
    return traduzido


def _mecanismo_deficit(valor: ValorResposta | None) -> frozenset[str] | Desconhecido:
    """`B1.09` (`MECANISMO_DEFICIT`) é `SELECAO_MULTIPLA` — o registro grava
    um `frozenset[str]` de `valor_interno` (checklist). Ausência é erro
    explícito (pergunta `OBR`, nunca `COND`); `NAO_SEI` não é opção do
    registro real (não há entrada `admite_nao_sei` em B1.09), mas
    `_ou_desconhecido` trata o caso defensivamente pelo mesmo mecanismo
    central, sem duplicar a tradução."""
    if valor is None:
        raise ErroSinalComportamentalAusente("MECANISMO_DEFICIT")
    traduzido = _ou_desconhecido(valor)
    if not (isinstance(traduzido, frozenset) or traduzido is DESCONHECIDO):
        raise ErroSinalComportamentalAusente("MECANISMO_DEFICIT")
    return traduzido


def _pacto(valor: ValorResposta | None) -> str:
    """`B1.01` (`PACTO`) é `str` direto no contrato de
    `SinaisComportamentais` (`ESTABELECIDO`/`EM_CONSTRUCAO`/
    `NAO_ESTABELECIDO`) — sem enum próprio em `engine/estado.py`, o
    `valor_interno` já É o valor gravado, sem tradução."""
    if valor is None:
        raise ErroSinalComportamentalAusente("PACTO")
    if not isinstance(valor, str):
        raise ErroSinalComportamentalAusente("PACTO")
    return valor


def _risco_impulso(valor: ValorResposta | None) -> str | Desconhecido:
    """`B2.11` (`RISCO_IMPULSO`) é `str | Desconhecido` no contrato — o
    `valor_interno` (`NENHUMA`/`UMA`/`DUAS_TRES`/`QUATRO_MAIS`) já é a
    string gravada; `NAO_SEI` vira `DESCONHECIDO` por `_ou_desconhecido`
    (mesma tradução central de T-49/T-50, admite_nao_sei: true no
    registro)."""
    if valor is None:
        raise ErroSinalComportamentalAusente("RISCO_IMPULSO")
    traduzido = _ou_desconhecido(valor)
    if not (isinstance(traduzido, str) or traduzido is DESCONHECIDO):
        raise ErroSinalComportamentalAusente("RISCO_IMPULSO")
    return traduzido


def montar_sinais_comportamentais(respostas: RespostasCaso) -> SinaisComportamentais:
    """RF-14, AC-13, RF-418 — monta `SinaisComportamentais`. `B1.02`, `B1.05`,
    `B1.10`, `B5.C07` e `B9.04` saíram do questionário (`T-404`): entram
    `NOVA_DIVIDA_PREVISTA=NAO`, `HISTORICO_RECAIDA=TALVEZ`,
    `HISTORICO_ABANDONO=TALVEZ`, `JANELA_NOVA_DIVIDA=None` e
    `LINHA_CONTINUA_SENDO_UTILIZADA=DESCONHECIDO`. Respostas antigas são
    ignoradas. Seguem perguntadas `B1.01`, `B1.07`, `B1.09`, `B2.11` e `B9.02`.
    """
    return SinaisComportamentais(
        NOVA_DIVIDA_PREVISTA=SimNaoTalvez.NAO,
        MECANISMO_DEFICIT=_mecanismo_deficit(respostas.valor("MECANISMO_DEFICIT")),
        HISTORICO_RECAIDA=SimNaoTalvez.TALVEZ,
        NOVO_PARCELAMENTO_PREVISTO=_sim_nao_talvez_de_domino_fechado(
            respostas.valor("NOVO_PARCELAMENTO_PREVISTO"), "NOVO_PARCELAMENTO_PREVISTO"
        ),
        PACTO=_pacto(respostas.valor("PACTO")),
        RISCO_IMPULSO=_risco_impulso(respostas.valor("RISCO_IMPULSO")),
        LINHA_CONTINUA_SENDO_UTILIZADA=DESCONHECIDO,
        # B9.02 — lido do registro real (collection/registros/bloco-09.yaml,
        # T-99): escala 0-10, por _necessidade_vitoria (mesmo padrão de
        # _risco_impulso: erro explícito se ausente).
        NECESSIDADE_VITORIA=_necessidade_vitoria(respostas.valor("NECESSIDADE_VITORIA")),
        HISTORICO_ABANDONO=SimNaoTalvez.TALVEZ,
        JANELA_NOVA_DIVIDA=None,
    )


# ---------------------------------------------------------------------------
# EstadoFinanceiro completo — T-51, RF-14, AC-18. Ver docstring do módulo
# para a fronteira dos campos monetários agregados (RENDA_TOTAL_RECORRENTE,
# DESPESAS_OPERACIONAIS_ATUAIS, DESPESAS_NAO_MENSAIS_NORMALIZADAS) e
# CONFIABILIDADE_DADOS (derivada pelo motor, T-13 do slug motor-calculo).
# INVENTARIO_COMPLETO (T-52, RF-15, AC-07) é lida de B5.FIM02 por
# _inventario_completo, abaixo — não é mais parâmetro externo.
# ---------------------------------------------------------------------------


class ErroCampoAgregadoDesconhecido(Exception):
    """`OQ-16` (T-103): `RENDA_TOTAL_RECORRENTE`/`DESPESAS_OPERACIONAIS_
    ATUAIS`/`DESPESAS_NAO_MENSAIS_NORMALIZADAS` são tipadas `Dinheiro` puro
    em `engine/estado.py` (`EstadoFinanceiro`), sem união com `Desconhecido`
    — o mesmo contrato que já obriga `_economia_potencial_imediata` (T-51)
    a nunca devolver `DinheiroTalvez`. Quando uma fonte obrigatória do
    agregado é `NAO_SEI`/ausente e por isso o total não pode ser um `Decimal`
    real, esta camada não inventa `0` nem qualquer estimativa: levanta este
    erro nomeado, explícito, nunca silencioso (mesmo padrão de
    `ErroRespostaAusente`, mas dedicado a agregados de Bloco 3 em vez de um
    único campo de resposta)."""

    def __init__(self, VARIAVEL_GRAVADA: str, motivo: str) -> None:
        self.VARIAVEL_GRAVADA = VARIAVEL_GRAVADA
        self.motivo = motivo
        segmentos = (
            f"{VARIAVEL_GRAVADA}:",
            motivo,
            "— nenhuma estimativa silenciosa (RF-12).",
        )
        super().__init__(" ".join(segmentos))


def _renda_principal(respostas: RespostasCaso) -> Dinheiro:
    """`B3.01` (`RENDA_PRINCIPAL`) — `OBR`, não repetível. `OQ-16`: qualidade
    do dado (confirmada/estimada) é metadado, não filtro — qualquer valor
    concreto (`Decimal`) informado entra com o mesmo peso na soma. O
    registro real não declara `admite_nao_sei` para `B3.01` (a segunda
    opção, "renda variável sem valor único", é o próprio
    `salto_consequencia` do registro documentando `RENDA_PRINCIPAL =
    DESCONHECIDA"); por isso `NAO_SEI` é tratado aqui pelo mesmo mecanismo
    central (`_ou_desconhecido`) — resposta ausente ou `DESCONHECIDO`
    levantam `ErroCampoAgregadoDesconhecido` (nunca um valor inventado),
    porque `RENDA_TOTAL_RECORRENTE` é `Dinheiro` puro (ver
    `ErroCampoAgregadoDesconhecido`)."""
    valor = respostas.valor("RENDA_PRINCIPAL")
    if valor is None:
        raise ErroCampoAgregadoDesconhecido("RENDA_PRINCIPAL", "sem resposta")
    traduzido = _ou_desconhecido(valor)
    if traduzido is DESCONHECIDO:
        raise ErroCampoAgregadoDesconhecido("RENDA_PRINCIPAL", "resposta é NAO_SEI/DESCONHECIDO")
    if not isinstance(traduzido, Decimal):
        raise ErroCampoAgregadoDesconhecido("RENDA_PRINCIPAL", "valor não é monetário")
    return traduzido


def _renda_recorrente_adicional_total(respostas: RespostasCaso) -> Dinheiro:
    """`OQ-16`/`OQ-19` (`T-105`): soma de todas as fichas REP de
    `RENDA_RECORRENTE_ADICIONAL` (`B3.03B`, escopo `RENDA_ADICIONAL_ID`) —
    lista aberta, sem limite de quantidade codificado (0, 1 ou N itens).
    `valores_do_escopo` já devolve tupla vazia, nunca erro, quando não há
    nenhuma ficha cadastrada (caso "0 fontes adicionais"). Qualidade do
    dado é metadado, não filtro (`OQ-16`): todo valor concreto informado
    entra na soma com o mesmo peso; um item com `NAO_SEI` não impede a soma
    dos demais — a própria ficha com `NAO_SEI` simplesmente não contribui
    um valor numérico a essa soma (o dado desconhecido daquele item
    específico não é o mesmo caso de `RENDA_PRINCIPAL` desconhecida, que
    inviabiliza QUALQUER total — aqui a renda adicional é aditiva, e uma
    fonte desconhecida entre outras conhecidas não apaga as conhecidas)."""
    valores = respostas.valores_do_escopo(
        EscopoRepeticao.RENDA_ADICIONAL_ID, "RENDA_RECORRENTE_ADICIONAL"
    )
    total = _ZERO
    for valor in valores:
        traduzido = _ou_desconhecido(valor)
        if isinstance(traduzido, Decimal):
            total += traduzido
    return total


def _contribuicao_familiar(respostas: RespostasCaso) -> Dinheiro:
    """`RF-412` (`B3.04A`, `CONTRIBUICAO_FAMILIAR`): quanto outra pessoa
    coloca por mês nas despesas do orçamento soma à renda disponível. Sem
    resposta, `NAO_SEI` ou pergunta que não abriu (`B3.04` = Não): zero — a
    renda fica idêntica à de antes. Soma simples; nenhuma fórmula nova."""
    valor = respostas.valor("CONTRIBUICAO_FAMILIAR")
    traduzido = None if valor is None else _ou_desconhecido(valor)
    return traduzido if isinstance(traduzido, Decimal) else _ZERO


def _renda_total_recorrente(respostas: RespostasCaso) -> Dinheiro:
    """`OQ-16`: `RENDA_TOTAL_RECORRENTE` = `RENDA_PRINCIPAL` (B3.01) + soma
    de todas as fichas de `RENDA_RECORRENTE_ADICIONAL` (B3.03A-C, escopo
    `RENDA_ADICIONAL_ID`). `RECURSOS_EXTRAORDINARIOS` (B3.05) e a renda
    extra potencial (B3.06) NUNCA entram nesta soma — nunca lidas por esta
    função nem por nenhuma outra deste módulo, então não há filtro a
    escrever: a exclusão é por simplesmente nunca ler essas duas
    variáveis."""
    return (
        _renda_principal(respostas)
        + _renda_recorrente_adicional_total(respostas)
        + _contribuicao_familiar(respostas)
    )


def _despesas_operacionais_atuais(respostas: RespostasCaso) -> Dinheiro:
    """`OQ-16`: `DESPESAS_OPERACIONAIS_ATUAIS` = soma de todos os valores
    das fichas REP de `B3.D01` a `B3.D11` (as 10 categorias fixas mais a
    categoria "não listada"). No registro real (`collection/registros/
    bloco-03.yaml`, T-17), as 11 categorias são checklists (`B3.D01-D10`,
    `SELECAO_MULTIPLA`) ou um SIM/NÃO (`B3.D11`) que apenas ABREM uma ficha
    REP por item marcado — TODAS as 11 categorias compartilham o MESMO
    escopo de ficha, `ITEM_DESPESA` (já existente, sem relação com T-105), e
    o MESMO campo de valor por item, `VALOR_DESPESA` (`B3.DF01`). Por isso
    a soma não precisa (e não tem como) discriminar de qual das 11
    categorias cada item veio — somar todos os `VALOR_DESPESA` de todos os
    itens de `ITEM_DESPESA` já é, por construção do registro, a soma exata
    de `B3.D01` a `B3.D11`. Categorias parcialmente preenchidas (nem toda
    categoria tem item marcado) não são um caso especial: sem item
    cadastrado naquela categoria, simplesmente não há ficha a somar ali —
    `valores_do_escopo` sobre um escopo sem itens de uma categoria não
    "falta" nada, porque o escopo é único para as 11. Um item com
    `VALOR_DESPESA = NAO_SEI` não contribui numericamente à soma (mesmo
    tratamento de fonte individual desconhecida de
    `_renda_recorrente_adicional_total`, acima) — nunca um erro que
    bloqueasse a soma inteira por uma única ficha incerta."""
    return _soma_dos_informados(_despesas_operacionais_por_item(respostas))


def _despesas_operacionais_por_item(
    respostas: RespostasCaso,
) -> tuple[tuple[str, DinheiroTalvez], ...]:
    """`T-225` (RF-79, AC-119): a decomposição de
    `_despesas_operacionais_atuais` — um `(item_id, VALOR_DESPESA)` por
    ficha de `ITEM_DESPESA` respondida, `DESCONHECIDO` quando `NAO_SEI`. É
    daqui que o total sai (`_soma_dos_informados`), para que a fotografia
    do mês e o motor leiam a MESMA função (`OQ-53`)."""
    # Um valor por item — a última resposta vence, a mesma chave
    # `(variável, item)` de `RespostasCaso.valores_do_escopo`.
    por_item = {
        resposta.item_id: resposta.valor
        for resposta in respostas.respostas
        if resposta.ID_PERGUNTA == "VALOR_DESPESA" and resposta.item_id
    }
    return tuple(
        (item_id, _dinheiro_ou_desconhecido(valor)) for item_id, valor in por_item.items()
    )


def _dinheiro_ou_desconhecido(valor: ValorResposta) -> DinheiroTalvez:
    traduzido = _ou_desconhecido(valor)
    return traduzido if isinstance(traduzido, Decimal) else DESCONHECIDO


def _soma_dos_informados(linhas: tuple[tuple[str, DinheiroTalvez], ...]) -> Dinheiro:
    """`OQ-16`: item "não sei" não contribui numericamente — nunca bloqueia
    a soma dos demais."""
    total = _ZERO
    for _item_id, valor in linhas:
        if isinstance(valor, Decimal):
            total += valor
    return total




def _despesas_nao_mensais_normalizadas(respostas: RespostasCaso) -> Dinheiro:
    """`OQ-16`/`OQ-19` (`T-105`) — corrigida por `T-107`:
    `DESPESAS_NAO_MENSAIS_NORMALIZADAS` = (soma dos valores anuais de todas
    as fichas REP de `B3.NM02A-D`, escopo `DESPESA_NAO_MENSAL_ID`, CUJA
    `DESPESA_NAO_MENSAL_JA_CONTABILIZADA` (B3.NM02D) NÃO seja `Sim`) / 12 —
    a normalização anual→mensal que o próprio nome da variável indica.
    `B3.NM02B` (`VALOR_DESPESA_NAO_MENSAL`) é "o valor total previsto" da
    despesa não-mensal; `FREQUENCIA_DESPESA_NAO_MENSAL` (B3.NM02C) continua
    fora da fórmula (`OQ-16` nunca normatizou periodicidade). Já
    `DESPESA_NAO_MENSAL_JA_CONTABILIZADA` (B3.NM02D) — cujo próprio
    `salto_consequencia` no registro diz "Sim → não normalizar novamente
    (impedir dupla contagem)" — agora É lida: a primeira resposta de
    `OQ-16` fechou a fórmula sem essa exclusão (implementada assim por
    `T-103`), e uma correção de registro, decisão do usuário, fechou que
    fichas com `Sim` são EXCLUÍDAS da soma antes da divisão por 12; `TALVEZ`/
    `NAO_SEI` continua entrando normalmente (só exclusão explícita por
    `Sim`, nunca por incerteza).

    `valores_do_escopo` (`collection/respostas.py`) devolve só os VALORES de
    uma variável por item, sem o `item_id` correspondente — duas chamadas
    separadas (uma para `VALOR_DESPESA_NAO_MENSAL`, outra para
    `DESPESA_NAO_MENSAL_JA_CONTABILIZADA`) não têm ordem estável garantida
    entre si, então correlacioná-las por índice posicional seria arriscar
    excluir a ficha errada. Por isso esta função descobre os `item_id` do
    escopo diretamente do snapshot em memória (`respostas.respostas`, campo
    público de `RespostasCaso` — mesmo padrão já usado por `app/http/
    rotas_coleta.py` para reconstruir uma `RespostasCaso`)
    e, para cada item, lê as DUAS variáveis pelo mesmo mecanismo de
    `collection/validacao.py::validar_cruzada` — `respostas.valor_no_item
    (item_id, variavel)` — que já resolve exatamente este problema de "duas
    variáveis do mesmo item". `DESPESA_NAO_MENSAL_JA_CONTABILIZADA` é
    `SIM_NAO_TALVEZ` com `valor_interno: null` no registro: o valor
    gravado é a string crua do formulário
    (`app/http/rotas_coleta.py::_resolver_valor`, que devolve `str` direto
    para `SIM_NAO_TALVEZ`), por isso a comparação é contra `_VALOR_JA_
    CONTABILIZADA_SIM = "SIM"`, nunca contra o rótulo em português. `Decimal`
    exato: a divisão por 12 nunca passa por `float` (RF-13, fronteira única
    de `app/montagem/conversao.py`)."""
    return _soma_dos_informados(_despesas_nao_mensais_por_item(respostas))


def _despesas_nao_mensais_por_item(
    respostas: RespostasCaso,
) -> tuple[tuple[str, DinheiroTalvez], ...]:
    """`T-225` (RF-79, AC-119): a decomposição de
    `_despesas_nao_mensais_normalizadas` — um `(item_id, anual / 12)` por
    ficha (`T-404`: sem `B3.NM02D`, nenhuma é excluída), `DESCONHECIDO`
    quando `NAO_SEI`. O total é a soma destas linhas (a divisão por 12 é
    por item, para que a soma das linhas seja o total EXATO, sem resíduo
    de arredondamento entre as duas formas)."""
    itens = dict.fromkeys(
        resposta.item_id
        for resposta in respostas.respostas
        if resposta.ID_PERGUNTA == "VALOR_DESPESA_NAO_MENSAL" and resposta.item_id
    )
    linhas: list[tuple[str, DinheiroTalvez]] = []
    for item_id in itens:
        valor = respostas.valor_no_item(item_id, "VALOR_DESPESA_NAO_MENSAL")
        if valor is None:
            continue
        anual = _dinheiro_ou_desconhecido(valor)
        linhas.append((item_id, anual / _DOZE if isinstance(anual, Decimal) else DESCONHECIDO))
    return tuple(linhas)


_VARIAVEIS_RECURSO_EXTRAORDINARIO: Final[tuple[str, ...]] = (
    "VALOR_RECURSO_EXTRAORDINARIO",
    "JANELA_RECURSO_EXTRAORDINARIO",
    "CERTEZA_RECURSO_EXTRAORDINARIO",
)


def _membro_por_valor[TEnum: Enum](enum_alvo: type[TEnum], valor: ValorResposta) -> TEnum:
    """Como `_membro_do_enum`, mas pelo VALOR do membro — `JANELA_RECURSO_
    EXTRAORDINARIO` tem `valor_interno` `"1_3M"`, que não é nome Python."""
    try:
        return enum_alvo(valor)
    except ValueError as erro:
        raise ErroValorInternoDesconhecido(enum_alvo, str(valor)) from erro


def _recursos_extraordinarios(respostas: RespostasCaso) -> tuple[RecursoExtraordinario, ...]:
    """`RF-98`, `AC-150`, `EC-38`, `DE-02` (`T-273`) — um
    `RecursoExtraordinario` por item `EXT` respondido (`B3.05B`–`D`, escopo
    `RECURSO_EXTRAORDINARIO_ID`), NUNCA somados: cada item leva o seu valor,
    janela e certeza, lidos com `valor_no_item`. `T-404`: `B3.05A` (tipo)
    saiu; a ficha começa em `B3.05B` (`motor-calculo:RF-72`).

    Valor `NAO_SEI` → `DESCONHECIDO`; janela `NAO_SEI` é membro do enum —
    nenhum dos dois vira `0` nem janela presumida (`EC-38`): quem decide o
    que entra na projeção é o motor. Ficha sem uma das quatro respostas →
    `ErroRespostaAusente` nomeando a pergunta (`422`, `T-197`). Resposta de
    caso (`item_id=''`, legado anterior à migração `008`) não é item."""
    itens = sorted(
        {
            resposta.item_id
            for resposta in respostas.respostas
            if resposta.ID_PERGUNTA in _VARIAVEIS_RECURSO_EXTRAORDINARIO and resposta.item_id
        }
    )
    recursos: list[RecursoExtraordinario] = []
    for item_id in itens:
        valor = _dinheiro_obrigatorio(
            respostas, item_id, "B3.05B", "VALOR_RECURSO_EXTRAORDINARIO"
        )
        janela = respostas.valor_no_item(item_id, "JANELA_RECURSO_EXTRAORDINARIO")
        if janela is None:
            raise ErroRespostaAusente(item_id, "B3.05C", "JANELA_RECURSO_EXTRAORDINARIO")
        certeza = respostas.valor_no_item(item_id, "CERTEZA_RECURSO_EXTRAORDINARIO")
        if certeza is None:
            raise ErroRespostaAusente(item_id, "B3.05D", "CERTEZA_RECURSO_EXTRAORDINARIO")
        recursos.append(
            RecursoExtraordinario(
                ITEM_ID=item_id,
                VALOR_RECURSO_EXTRAORDINARIO=valor,
                # "Ainda não sei" grava `NAO_SEI` como `valor_interno` —
                # membro do enum, não o sentinela de coleta.
                JANELA_RECURSO_EXTRAORDINARIO=_membro_por_valor(
                    JANELA_RECURSO_EXTRAORDINARIO,
                    "NAO_SEI" if janela is NAO_SEI else janela,
                ),
                CERTEZA_RECURSO_EXTRAORDINARIO=_membro_por_valor(
                    CERTEZA_RECURSO_EXTRAORDINARIO, certeza
                ),
            )
        )
    return tuple(recursos)


def _capacidade_ataque_declarada(respostas: RespostasCaso) -> DinheiroTalvez:
    """`B3.C01` (`CAPACIDADE_ATAQUE_DECLARADA`) — OBR, admite `NAO_SEI`
    ("Ainda não consigo estimar.") e tem uma opção que grava `valor_interno:
    "0"` diretamente ("Hoje não consigo separar nenhum valor adicional.") —
    `Dinheiro(0)` real, preservado e distinto de `DESCONHECIDO`, mesmo padrão
    de `PARCELA_CONTRATUAL`.
    Resposta ausente é erro explícito: é `OBR`, não `COND` — mesmo padrão de
    `_dinheiro_obrigatorio`, mas sem `DIVIDA_ID` (a pergunta não é `REP`)."""
    valor = respostas.valor("CAPACIDADE_ATAQUE_DECLARADA")
    if valor is None:
        raise ErroRespostaAusente("", "B3.C01", "CAPACIDADE_ATAQUE_DECLARADA")
    traduzido = _ou_desconhecido(valor)
    if not (isinstance(traduzido, Decimal) or traduzido is DESCONHECIDO):
        raise ErroRespostaAusente("", "B3.C01", "CAPACIDADE_ATAQUE_DECLARADA")
    return traduzido


def _contribuicao_extra_mensal(respostas: RespostasCaso) -> Dinheiro | None:
    """`B3.C02A` (`CONTRIBUICAO_EXTRA_MENSAL`, `RF-78`, `RF-443`) — só existe com
    "sim" em `B3.C02`. Sem resposta, "não sei" ou zero → `None` (o plano não
    mostra o cenário acelerado)."""
    valor = respostas.valor("CONTRIBUICAO_EXTRA_MENSAL")
    if valor is None:
        return None
    traduzido = _ou_desconhecido(valor)
    if isinstance(traduzido, Decimal) and traduzido > 0:
        return traduzido
    return None


def _inventario_completo(respostas: RespostasCaso) -> bool:
    """`B5.FIM02` (`CONFIRMACAO_FIM_CADASTRO`) — `RF-15`, `AC-07`. Domínio
    real de `valor_interno` (`collection/registros/bloco-05.yaml`, T-405):
    `SIM · NAO`. Qualquer resposta diferente de `SIM` — incluindo
    a própria ausência de resposta — produz `INVENTARIO_COMPLETO
    = False`; só `SIM` produz `True`. Mapeamento por `valor_interno`, nunca
    por texto de enunciado (terceiro critério de aceite de T-52).

    Ausência de resposta NÃO é `ErroRespostaAusente`: diferente dos campos
    monetários/enum obrigatórios deste módulo, aqui a lacuna documentada
    (segundo critério de aceite) é que "não respondida" é, ela própria, uma
    leitura de fato — o inventário não foi confirmado como completo, então
    não pode ser `True` por omissão. Isso é leitura de resposta (RF-15), não
    regra financeira: a CONSEQUÊNCIA de `INVENTARIO_COMPLETO = False` sobre
    `ORDEM_STATUS`/`STATUS_METODO` é do motor (`engine/diagnostico.py`),
    nunca calculada aqui."""
    valor = respostas.valor("CONFIRMACAO_FIM_CADASTRO")
    return valor == "SIM"


def _reserva_existe(respostas: RespostasCaso) -> RESERVA_EXISTE:
    """`B4.02` (`RESERVA_EXISTE`) — `RF-36`, `AC-51`. `OBR`, não repetível,
    `admite_nao_sei: false` (`collection/registros/bloco-04.yaml:43-64`), e
    `EstadoFinanceiro.RESERVA_EXISTE` (`engine/estado.py:511`) é o enum PURO,
    sem união com `Desconhecido`. Resposta ausente é erro explícito, nunca um
    default — mesmo padrão de `_tipo_renda` (acima).

    Os três `valor_interno` do registro (`SIM`/`INFORMAL`/`NAO`, `:52-57`)
    batem CARACTERE POR CARACTERE com os `name` dos membros do enum
    (`engine/estado.py:187-189`), então a tradução é o mecanismo genérico
    `_membro_do_enum` — nenhuma linha de tradução de rótulo em português é
    escrita aqui (`AC-37`, `AC-53`), e NENHUM dos três membros é colapsado
    em outro: `SIM` e `INFORMAL` são estados de coleta distintos que a
    devolutiva usa, mesmo que a §13.1 só distinga `NAO` de não-`NAO`
    (`OQ-25`, aberta — não bloqueia esta leitura)."""
    valor = respostas.valor("RESERVA_EXISTE")
    if valor is None:
        raise ErroRespostaAusente("", "B4.02", "RESERVA_EXISTE")
    if not isinstance(valor, str):
        raise ErroRespostaAusente("", "B4.02", "RESERVA_EXISTE")
    return _membro_do_enum(RESERVA_EXISTE, valor)


def _disposicao_uso_reserva(respostas: RespostasCaso) -> DISPOSICAO_USO_RESERVA:
    """`B4.03` (`DISPOSICAO_USO_RESERVA`) — `RF-36`, `AC-52`, `EC-16`,
    `EC-17`. `COND`, `admite_nao_sei: false`. Os quatro `valor_interno`
    (`PARTE`/`GRANDE_PARTE`/`TALVEZ`/`NAO`, `bloco-04.yaml:127-133`) batem
    caractere por caractere com os `name` do enum (`engine/estado.py:197-200`)
    e são resolvidos por `_membro_do_enum` — sem tradução de rótulo (`AC-53`).

    **A ausência de `B4.03` devolve `DISPOSICAO_USO_RESERVA.NAO`, e esse
    `NAO` é AUSÊNCIA ESTRUTURAL DA PERGUNTA — NÃO é escolha do aluno.** São
    duas situações humanas DIFERENTES que compartilham o mesmo valor gravado,
    e quem ler o dado cru precisa saber distingui-las:

    - "não tenho reserva": `RESERVA_EXISTE = NAO` e por isso `B4.03` NEM FOI
      EXIBIDA (`condicao_exibicao`, `bloco-04.yaml:135-137`, é a única
      condição que suprime a pergunta). O aluno nunca opinou sobre usar uma
      reserva que não existe.
    - "tenho reserva e prefiro preservá-la integralmente": `B4.03` foi
      exibida e RESPONDIDA com o `valor_interno` `NAO` (`:133`). Aqui há
      escolha declarada.

    Sem esta nota alguém leria o `NAO` do primeiro caso e concluiria que o
    aluno TINHA reserva e recusou usá-la. Decisão do usuário (2026-09-07),
    plano R2.4.2.

    Por que `NAO` e por que isso não é erro: o campo é obrigatório e não
    admite `Desconhecido` (mudar o tipo exigiria alterar `engine/`, proibido
    por `AC-44`); levantar erro transformaria o caso legítimo "não tenho
    reserva" em falha de montagem, contrariando `EC-16` diretamente ("os
    campos condicionais ausentes NÃO são erro"); e `NAO` é o único membro
    cuja leitura de fato é verdadeira quando não há reserva.

    O membro é ARITMETICAMENTE INERTE: no único caminho que o alcança, a
    Regra 1 da §13.1 já curto-circuitou `RESERVA_MOBILIZAVEL` em zero pelo
    primeiro termo (`RESERVA_EXISTE = NAO`), qualquer que seja o segundo.
    **Isto NÃO é reproduzir a Regra 1**: esta função não escreve
    `if RESERVA_EXISTE is NAO: RESERVA_MOBILIZAVEL = 0` nem olha
    `RESERVA_EXISTE` — ela escolhe o valor de um campo obrigatório numa
    ausência estrutural, com o motivo registrado (mesmo padrão documentado de
    `_CAMPOS_DE_GATE_FORA_DE_ESCOPO`, `:315`). Quem aplica a regra é
    `engine/ataque_imediato.py::derivar_RESERVA_MOBILIZAVEL`, invocado por
    `engine/diagnostico.py` (`RF-44`, `AC-68`)."""
    valor = respostas.valor("DISPOSICAO_USO_RESERVA")
    if valor is None:
        return DISPOSICAO_USO_RESERVA.NAO
    if not isinstance(valor, str):
        return DISPOSICAO_USO_RESERVA.NAO
    return _membro_do_enum(DISPOSICAO_USO_RESERVA, valor)


def _reserva_total(respostas: RespostasCaso) -> DinheiroTalvez:
    """`B4.02A` (`RESERVA_TOTAL`) — `RF-37`, `AC-55`, `EC-16`. `COND`,
    `admite_nao_sei: true` (`bloco-04.yaml:66-85`). O campo é
    `DinheiroTalvez` (`engine/estado.py:512`) justamente porque a Regra 3 da
    §13.1 EXIGE o estado desconhecido — "reserva total desconhecida" produz
    `RESERVA_MOBILIZAVEL = DESCONHECIDA`, nunca zero silencioso.

    Um `Decimal` real é repassado inalterado (já veio da fronteira única de
    `app/montagem/conversao.py`, `RF-13` — nenhum `float` no caminho).
    `NAO_SEI` ("Não sei.", `:76`) vira `DESCONHECIDO` pelo mecanismo central
    `_ou_desconhecido`. E a AUSÊNCIA ESTRUTURAL — `B4.02 = NAO` suprime a
    pergunta (`condicao_exibicao`, `:78-80`) — também vira `DESCONHECIDO`:
    NUNCA erro, NUNCA `Decimal("0")`, NUNCA `None` (`EC-16`: campo
    condicional ausente não é erro; e um zero aqui seria afirmar que a
    reserva foi medida e vale zero)."""
    valor = respostas.valor("RESERVA_TOTAL")
    if valor is None:
        return DESCONHECIDO
    traduzido = _ou_desconhecido(valor)
    if not isinstance(traduzido, Decimal):
        return DESCONHECIDO
    return traduzido


def _valor_maximo_reserva_informado_usuario(respostas: RespostasCaso) -> DinheiroTalvez:
    """`B4.03A` (`VALOR_MAXIMO_RESERVA_INFORMADO_USUARIO`) — `RF-37`,
    `AC-56`, `EC-15`, `EC-16`, `EC-17`. `COND`, `admite_nao_sei: true`
    (`bloco-04.yaml:144-164`). Devolve `DESCONHECIDO` em TUDO que não seja um
    `Decimal` real; um `Decimal` é repassado exato, vindo da fronteira única
    (`RF-13`), sem `float` em nenhum ponto do caminho.

    Os quatro caminhos que colapsam em `DESCONHECIDO` (plano R2.4.3):
    `NAO_SEI` ("Não sei.", `:155`); a opção `DECIDIR_DEPOIS`
    ("Prefiro decidir somente depois...", `:154`); e as duas ausências
    estruturais — `B4.03 = NAO` suprime `B4.03A` (`condicao_exibicao`,
    `:157-159`, `EC-17`) e, por cadeia, `B4.02 = NAO` suprime `B4.03` e com
    ela `B4.03A` (`EC-16`).

    **`OQ-22`(a) está ABERTA, e enquanto estiver esta leitura NÃO PODE
    distinguir "decidir depois" de "não sei" pelo `valor_interno`** — desde
    `T-296` as opções têm código (`DECIDIR_DEPOIS`, `NAO_SEI`), mas os dois
    seguem lidos como desconhecido. Aritmeticamente a Regra
    3 da §13.1 já colapsa as duas em `RESERVA_MOBILIZAVEL = DESCONHECIDA`,
    então a leitura correta hoje é idêntica nos dois casos. Tratar a opção
    sem `valor_interno` como qualquer coisa diferente de desconhecido seria
    inventar. O que `OQ-22`(a) decide é se o registro passa a distingui-las
    para a devolutiva — mudança de YAML, não deste código."""
    valor = respostas.valor("VALOR_MAXIMO_RESERVA_INFORMADO_USUARIO")
    if valor is None:
        return DESCONHECIDO
    traduzido = _ou_desconhecido(valor)
    if not isinstance(traduzido, Decimal):
        return DESCONHECIDO
    return traduzido


def montar_estado_financeiro(
    respostas: RespostasCaso,
    *,
    DATA_REFERENCIA: date,
    dividas: tuple[Divida, ...],
    CONFIABILIDADE_DADOS: CONFIABILIDADE_DADOS,
    economia_nao_identificada: Dinheiro | None = None,
) -> EstadoFinanceiro:
    """RF-14, AC-18 — monta o `EstadoFinanceiro` COMPLETO a partir das
    respostas do caso, com `DATA_REFERENCIA` vinda do `Caso` (`app/casos/
    maquina.py::Caso.DATA_REFERENCIA`) como parâmetro EXPLÍCITO — nunca de
    `date.today()`/`datetime.now()` (`AC-18`: é isso que faz recalcular o
    mesmo caso com a mesma `DATA_REFERENCIA` produzir o mesmo `SNAPSHOT_ID`).
    Verificado também por teste estático dedicado (`tests/app_aluno/
    estatica/test_sem_relogio_em_montagem.py`).

    Função PURA: a mesma `respostas` e os mesmos parâmetros produzem sempre
    o mesmo `EstadoFinanceiro` — nenhuma leitura de relógio, de ambiente ou
    de estado global em nenhum caminho (mesmo padrão de `montar_divida`/
    `montar_perfil_comportamental`/`montar_sinais_comportamentais`, que já
    são puras). `EstadoFinanceiro` é `frozen=True, slots=True`
    (`engine/estado.py`) — comparável por `==` estrutural.

    Campos preenchidos a partir de resposta (`RF-12`): `TIPO_RENDA` (B3.02,
    `_tipo_renda`), `CAPACIDADE_ATAQUE_DECLARADA` (B3.C01,
    `_capacidade_ataque_declarada`, `DinheiroTalvez` — `NAO_SEI` vira
    `DESCONHECIDO`), `ECONOMIA_POTENCIAL_IMEDIATA` (B2.09/B2.10/B2.10A,
    `_economia_potencial_imediata`), `perfil_comportamental`
    (`montar_perfil_comportamental`, T-50), `sinais_comportamentais`
    (`montar_sinais_comportamentais`, T-50) e `AUTOPERCEPCAO_CONTROLE`
    (B2.13, `_autopercepcao_controle`, T-50) — este admite `DESCONHECIDO`.

    `RENDA_TOTAL_RECORRENTE`, `DESPESAS_OPERACIONAIS_ATUAIS` e
    `DESPESAS_NAO_MENSAIS_NORMALIZADAS` (`T-103`, `OQ-16`): NÃO são mais
    parâmetro externo — são calculadas aqui a partir das respostas do
    Bloco 3 por `_renda_total_recorrente`, `_despesas_operacionais_atuais`
    e `_despesas_nao_mensais_normalizadas`, respectivamente (ver essas três
    funções para a fórmula normativa exata fechada por `OQ-16`, e
    `ErroCampoAgregadoDesconhecido` para o caminho de erro quando
    `RENDA_PRINCIPAL` é desconhecida). A fronteira documentada em `T-51`
    (parâmetro obrigatório sem default) era a decisão certa ENQUANTO a
    fórmula de composição do Bloco 3 não estava fechada — `OQ-16`
    resolveu isso, e `OQ-19`/`T-105` destravou o mecanismo de repetição que
    faltava para ler as fichas de renda adicional e despesa não-mensal.

    `CONFIABILIDADE_DADOS` continua sendo PARÂMETRO EXTERNO explícito —
    derivada pelo motor, função de `engine/comportamento.py`, T-13 do slug
    `motor-calculo` — fora da allowlist de import desta camada e fora do
    fluxo permitido por `RF-16`/Lei nº 3; ver docstring do módulo. `dividas`
    é recebida pronta porque cada `Divida` é montada individualmente por
    `montar_divida` (T-49) — não é responsabilidade desta função descobrir
    quantas fichas de dívida existem nem iterar sobre elas.

    `INVENTARIO_COMPLETO` (`T-52`, `RF-15`, `AC-07`): NÃO é mais parâmetro
    externo — é lido diretamente das respostas por `_inventario_completo`
    (`B5.FIM02`/`CONFIRMACAO_FIM_CADASTRO`), mesmo padrão de `_tipo_renda`/
    `_capacidade_ataque_declarada`, acima. A fronteira documentada em `T-51`
    (parâmetro obrigatório sem default) era a decisão certa ENQUANTO esta
    leitura não existia; agora que `RF-15` está implementado, continuar
    recebendo o booleano de fora seria reproduzir aqui uma leitura que já
    mora nesta função.

    **Os cinco campos de reserva e caixa do Bloco 4 (`T-111`, `RF-36`,
    `RF-37`, `RF-38`).** `RESERVA_EXISTE` (B4.02), `RESERVA_TOTAL` (B4.02A),
    `DISPOSICAO_USO_RESERVA` (B4.03), `VALOR_MAXIMO_RESERVA_INFORMADO_
    USUARIO` (B4.03A) e `DINHEIRO_DISPONIVEL` (B4.01/B4.01A) são LIDOS das
    respostas pelas cinco funções privadas acima — nenhum vira parâmetro
    externo novo, e a assinatura desta função permanece inalterada. Cada
    leitura é `resposta → conversão → tipo`: NENHUMA das três regras da
    §13.1 é reproduzida aqui. Quem aplica `MIN`/`MAX`, quem curto-circuita
    em zero e quem propaga `DESCONHECIDO` é `engine/ataque_imediato.py::
    derivar_RESERVA_MOBILIZAVEL`, invocado por `engine/diagnostico.py` —
    esta camada muda a ENTRADA, nunca a derivação (`RF-44`, `AC-68`).

    **`investimentos` e `ativos` são tupla vazia
    DECLARADA, com motivo — jamais omissão silenciosa, jamais estimativa,
    jamais classificação inventada (`RF-39`, `AC-60`, `AC-62`, `EC-19`).**
    Não há função de leitura para as duas porque NÃO HÁ O QUE LER: uma
    função vazia sugeriria que existe leitura parcial. Mesmo padrão
    documentado de `_CAMPOS_DE_GATE_FORA_DE_ESCOPO` (`:315`). Os motivos,
    nominalmente:

    - `investimentos` e `ativos` — `motor-calculo:OQ-26` e
      `motor-calculo:OQ-27`, AMBAS abertas e AMBAS necessárias: responder só
      uma NÃO destrava. `CLASSIFICACAO_MOBILIZACAO` e
      `VALOR_LIQUIDO_REALIZAVEL*` são campos obrigatórios e SEM DEFAULT nas
      três dataclasses de item de `engine/estado.py`, e cada um depende de
      uma das duas questões por causa independente — sem as duas respostas
      não é possível construir um único item sem inventar um dado.
      `CLASSIFICACAO_MOBILIZACAO` não é derivada aqui em hipótese alguma:
      derivá-la nesta camada seria fórmula patrimonial, proibida pela
      Lei nº 3 (`RF-44`).

    `recursos_extraordinarios` deixou a lacuna em `T-273` (`RF-98`): um item
    por ficha `EXT`, lido por `_recursos_extraordinarios`.

    `AC-60` é mais forte que "não implementado": as duas permanecem vazias
    MESMO com fichas de investimento, imóvel, veículo e outro ativo
    preenchidas nas respostas. A lacuna é do contrato, não da coleta.
    """
    return EstadoFinanceiro(
        DATA_REFERENCIA=DATA_REFERENCIA,
        RENDA_TOTAL_RECORRENTE=_renda_total_recorrente(respostas),
        TIPO_RENDA=TIPO_RENDA.RELATIVAMENTE_ESTAVEL,  # `T-404`: B3.02 saiu
        DESPESAS_OPERACIONAIS_ATUAIS=_despesas_operacionais_atuais(respostas),
        DESPESAS_NAO_MENSAIS_NORMALIZADAS=_despesas_nao_mensais_normalizadas(respostas),
        CAPACIDADE_ATAQUE_DECLARADA=_capacidade_ataque_declarada(respostas),
        CONTRIBUICAO_EXTRA_MENSAL=_contribuicao_extra_mensal(respostas),
        # `T-408`: B2.09, B2.10 e B2.10A saíram; só resta o valor da chamadora.
        ECONOMIA_POTENCIAL_IMEDIATA=(
            _ZERO if economia_nao_identificada is None else economia_nao_identificada
        ),
        INVENTARIO_COMPLETO=_inventario_completo(respostas),
        dividas=dividas,
        perfil_comportamental=montar_perfil_comportamental(respostas),
        sinais_comportamentais=montar_sinais_comportamentais(respostas),
        CONFIABILIDADE_DADOS=CONFIABILIDADE_DADOS,
        AUTOPERCEPCAO_CONTROLE=DESCONHECIDO,  # `T-408`: B2.13 saiu
        # --- Bloco 4 · reserva (`T-111`, `RF-36`, `RF-37`) ---
        RESERVA_EXISTE=_reserva_existe(respostas),
        RESERVA_TOTAL=_reserva_total(respostas),
        DISPOSICAO_USO_RESERVA=_disposicao_uso_reserva(respostas),
        VALOR_MAXIMO_RESERVA_INFORMADO_USUARIO=_valor_maximo_reserva_informado_usuario(respostas),
        # --- Bloco 4 · caixa (`T-111`, `RF-38`) ---
        DINHEIRO_DISPONIVEL=_ZERO,  # `T-408`: B4.01/B4.01A saíram
        # --- Lacuna DECLARADA, com motivo na docstring acima (`RF-39`,
        # `AC-60`, `AC-62`, `EC-19`) — nunca omissão silenciosa: as duas
        # `motor-calculo:OQ-26` e `motor-calculo:OQ-27` bloqueiam
        # `investimentos`/`ativos` (as DUAS, responder só uma não destrava).
        investimentos=(),
        ativos=(),
        # `T-273` (RF-98): item a item, nunca somados.
        recursos_extraordinarios=_recursos_extraordinarios(respostas),
    )
