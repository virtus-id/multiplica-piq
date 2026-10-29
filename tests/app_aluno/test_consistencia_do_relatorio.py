"""`T-451` — conferência de consistência do relatório (`RF-472`). Snapshots do
motor REAL com dados fictícios; a inconsistência é plantada com `replace`.

REGRAS: RF-472
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from engine.snapshot import SnapshotOrdem
from report.consistencia import verificar_consistencia
from report.pdf import renderizar_html_do_plano
from report.plano import carregar_textos_canonicos, montar_contexto_plano
from tests.app_aluno.test_pendencias_do_relatorio import _snapshot_base
from tests.app_aluno.test_prognostico_no_plano import _snapshot

_AVISO = "não passaram na nossa conferência automática"


def _html(snapshot: SnapshotOrdem) -> str:
    textos = carregar_textos_canonicos()
    return renderizar_html_do_plano(montar_contexto_plano(snapshot, textos), textos)


def test_rf472_snapshots_do_motor_sao_consistentes() -> None:
    for snapshot in (
        _snapshot_base(),
        _snapshot(),
        _snapshot(Decimal("300")),
        _snapshot(Decimal("0")),
    ):
        assert verificar_consistencia(snapshot) == ()
        assert _AVISO not in _html(snapshot)


def test_rf472_resultado_do_mes_que_nao_fecha_gera_aviso() -> None:
    base = _snapshot_base()
    quebrado = replace(
        base,
        diagnostico=replace(base.diagnostico, RESULTADO_CAIXA_OBSERVADO=Decimal("123.45")),
    )

    assert verificar_consistencia(quebrado) == (
        "renda − despesas − parcelas não fecha com o resultado do mês",
    )
    assert _AVISO in _html(quebrado)


def test_rf472_mes_do_plano_que_nao_fecha_gera_aviso() -> None:
    base = _snapshot(Decimal("300"))
    assert base.prognostico is not None
    meses = base.prognostico.MESES_DO_PLANO
    primeiro = replace(meses[0], SALDO_TOTAL=meses[0].SALDO_TOTAL + Decimal("50"))
    quebrado = replace(
        base,
        prognostico=replace(base.prognostico, MESES_DO_PLANO=(primeiro, *meses[1:])),
    )

    achados = verificar_consistencia(quebrado)
    assert any("plano seguido, mês" in a for a in achados)
    assert _AVISO in _html(quebrado)


def test_rf472_aporte_diferente_do_informado_gera_aviso() -> None:
    base = _snapshot(Decimal("300"))
    assert base.prognostico is not None and base.prognostico.com_extra is not None
    extra = replace(base.prognostico.com_extra, CONTRIBUICAO_EXTRA_MENSAL=Decimal("999"))
    quebrado = replace(base, prognostico=replace(base.prognostico, com_extra=extra))

    assert "o aporte do cenário acelerado difere do valor informado pelo aluno" in (
        verificar_consistencia(quebrado)
    )
