"""Sistema de amortização — `RF-509`, `AC-509`, `EC-60` (`T-463`).

`PRICE` (padrão): o pagamento mensal é fixo, a parcela declarada. `SAC`: a
**amortização é constante** e o pagamento do mês é a amortização mais os juros
do saldo daquele mês, então cai a cada mês:

```
AMORTIZACAO_SAC = PAGAMENTO_MENSAL_EFETIVO − SALDO_DEVEDOR_ATUAL × TAXA   (parcela de hoje)
pagamento do mês = AMORTIZACAO_SAC + juros do mês
```

O valor extra reduz o prazo (`OQ-69`): a amortização continua a mesma e o saldo
menor derruba os juros e o pagamento dos meses seguintes. A parcela é usada como
o aluno informou, sem seguros nem taxas separados (`OQ-70`). Se a parcela não
cobre os juros (`AMORTIZACAO_SAC <= 0`), não há solução: vale o pagamento fixo
declarado e a dívida cresce (`RF-79`, `EC-60`).
"""

from __future__ import annotations

from decimal import localcontext
from typing import Final

from engine.estado import Divida
from engine.precisao import CONTEXTO_MOTOR
from engine.tipos import DESCONHECIDO, SISTEMA_AMORTIZACAO, Dinheiro

REGRAS: Final[tuple[str, ...]] = ("RF-509", "RF-79", "AC-509", "EC-60")


def amortizacao_sac(divida: Divida) -> Dinheiro | None:
    """A amortização constante da `SAC`, ou `None` quando a dívida não é `SAC`
    ou quando não há solução (dado desconhecido, ou parcela que não cobre os
    juros)."""
    if divida.SISTEMA_AMORTIZACAO is not SISTEMA_AMORTIZACAO.SAC:
        return None
    saldo = divida.SALDO_DEVEDOR_ATUAL
    taxa = divida.TAXA_EFETIVA_MENSAL_NORMALIZADA
    pagamento = divida.PAGAMENTO_MENSAL_EFETIVO
    if saldo is DESCONHECIDO or taxa is DESCONHECIDO or pagamento is DESCONHECIDO:
        return None
    with localcontext(CONTEXTO_MOTOR):
        amortizacao = pagamento - saldo * taxa
    return amortizacao if amortizacao > 0 else None


def pagamento_nominal_do_mes(divida: Divida, juros_do_mes: Dinheiro) -> Dinheiro | None:
    """O pagamento do mês ANTES de limitar ao saldo: fixo (a parcela declarada)
    na `PRICE`, amortização mais juros do mês na `SAC`. `None` quando a parcela
    é desconhecida."""
    amortizacao = amortizacao_sac(divida)
    if amortizacao is not None:
        with localcontext(CONTEXTO_MOTOR):
            return amortizacao + juros_do_mes
    pagamento = divida.PAGAMENTO_MENSAL_EFETIVO
    return None if pagamento is DESCONHECIDO else pagamento
