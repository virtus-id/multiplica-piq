"""RF-453 (T-439) — ao terminar o cálculo, o aluno com orçamento que não fecha é avisado,
com o mesmo número que o plano mostra; mês positivo e cálculo em curso: nada."""

from __future__ import annotations

from dataclasses import replace

from app.casos.maquina import ESTADO_CASO
from app.http.rotas_calculo import _aviso_de_deficit
from tests.app_aluno.test_pendencias_do_relatorio import _snapshot_base
from tests.app_aluno.test_prognostico_no_plano import _snapshot


class _Snapshots:
    def __init__(self, snapshot: object) -> None:
        self._snapshot = snapshot

    def historico(self, _raiz: str) -> list[object]:
        return [self._snapshot]


class _Caso:
    def __init__(self, estado: ESTADO_CASO) -> None:
        self.estado = estado
        self.snapshot_raiz_id = "RAIZ"


def test_mes_negativo_avisa_com_o_valor_do_plano() -> None:
    snapshot = _snapshot_base()  # renda 8.000, saídas 9.000
    texto = _aviso_de_deficit(_Caso(ESTADO_CASO.AGUARDANDO_REVISAO), _Snapshots(snapshot))  # type: ignore[arg-type]
    assert texto is not None
    assert "superam sua renda em R$ 1.000,00 por mês" in texto and "provisório" in texto


def test_mes_positivo_nao_avisa() -> None:
    assert _aviso_de_deficit(_Caso(ESTADO_CASO.AGUARDANDO_REVISAO), _Snapshots(_snapshot())) is None  # type: ignore[arg-type]


def test_calculo_em_curso_nao_avisa() -> None:
    snapshot = replace(_snapshot_base())
    assert _aviso_de_deficit(_Caso(ESTADO_CASO.CALCULANDO), _Snapshots(snapshot)) is None  # type: ignore[arg-type]


def test_aviso_do_plano_nao_diz_que_o_plano_nao_foi_gerado() -> None:
    """RF-453: o plano do deficitário existe; nenhum texto fixo promete que ele só será
    calculado depois."""
    from report.plano import carregar_textos_canonicos

    textos = carregar_textos_canonicos().estabilizacao
    for chave in ("aviso_1", "aviso_2", "aviso_3", "texto", "ordem_intro"):
        assert "só é calculado" not in textos.get(chave, "")
        assert "não é gerado" not in textos.get(chave, "")
