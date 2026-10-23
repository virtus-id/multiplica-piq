"""A data em que o revisor liberou o plano — `RF-445`.

O Mês 1 do plano é o mês SEGUINTE a ela; todo mês do documento sai como
calendário a partir daí (`report.plano.rotulo_do_mes`). Só leitura da trilha de
revisões. Sem conexão, sem registro ou com erro, devolve `None` e o plano cai
nos rótulos "Mês N", em vez de falhar por causa de um rótulo.
"""

from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from app.revisao.fila import DECISAO_REVISAO
from persistencia.app_aluno.revisoes import RepositorioRevisoesSupabase
from persistencia.supabase.conexao import ErroConexaoAusente

_FUSO = ZoneInfo("America/Sao_Paulo")


def data_da_liberacao(caso_id: str, snapshot_id: str) -> date | None:
    try:
        registros = RepositorioRevisoesSupabase().listar_do_caso(caso_id)
    except ErroConexaoAusente:
        return None
    liberacoes = [
        r.decidido_em
        for r in registros
        if r.SNAPSHOT_ID == snapshot_id and r.decisao is DECISAO_REVISAO.LIBERADO
    ]
    return max(liberacoes).astimezone(_FUSO).date() if liberacoes else None
