"""`AC-180` — `B3.01` diz o que informar (`RF-117`, `T-338`, `T-409`).

O motor desconta as parcelas das dívidas da renda; quem informa o que cai na
conta (depois dos consignados) faz cada consignado ser contado duas vezes. A
instrução precisa dizer, com todas as letras, que o valor é ANTES de
empréstimos e consignados. Desde `T-409` a pergunta é curta e a instrução vai
no campo `apoio`, em destaque menor abaixo dela.
"""

from __future__ import annotations

from collection.carga import carregar_registros

_ENUNCIADO = "Qual é o seu salário líquido mensal?"
_APOIO = (
    "Informe o valor após os descontos de Imposto de Renda e Previdência, mas "
    "antes dos empréstimos e consignados."
)


def test_ac180_o_enunciado_de_b3_01_e_a_pergunta_curta() -> None:
    registro = next(r for r in carregar_registros().registros if r.ID == "B3.01")

    assert registro.enunciado == _ENUNCIADO


def test_ac180_a_instrucao_de_preenchimento_vai_no_apoio() -> None:
    registro = next(r for r in carregar_registros().registros if r.ID == "B3.01")

    assert registro.apoio == _APOIO
