"""`RF-415` — `B5.I03` (data da informação) é só informação do revisor.

A resposta aparece na conferência (`GET .../decisao`) e não muda nada do que
chega ao motor: a `Divida` montada é idêntica com e sem ela.

REGRAS: RF-415
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.montagem.estado import montar_divida
from collection.respostas import Resposta, RespostasCaso
from tests.app_aluno.test_liberacao_homologacao import _Ambiente
from tests.app_aluno.test_montagem_divida import _AGORA, _CASO_ID, _ficha_minima_completa


@pytest.fixture
def ambiente(tmp_path: Path) -> _Ambiente:
    return _Ambiente(tmp_path)


def test_rf415_a_divida_montada_e_identica_com_e_sem_a_data_da_informacao() -> None:
    sem = _ficha_minima_completa("D001")
    com = RespostasCaso(
        respostas=(
            *sem.respostas,
            Resposta(
                CASO_ID=_CASO_ID,
                ID_PERGUNTA="DATA_REFERENCIA_DADO",
                item_id="D001",
                valor="HA_MAIS_DE_3_MESES",
                QUESTIONARIO_VERSION="1.0.0",
                respondida_em=_AGORA,
            ),
        )
    )

    assert montar_divida(com, "D001") == montar_divida(sem, "D001")


def test_rf415_a_montagem_nao_le_a_data_da_informacao() -> None:
    assert "DATA_REFERENCIA_DADO" not in Path("app/montagem/estado.py").read_text(encoding="utf-8")


def test_rf415_o_revisor_ve_quando_a_divida_foi_consultada(
    ambiente: _Ambiente, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = "/revisao/caso/CASO-HOMOLOGACAO/decisao"
    sem = ambiente.cliente(monkeypatch).get(url).json()
    assert sem["datas_da_informacao"] == []

    ambiente.responder("DATA_REFERENCIA_DADO", "HA_13_MESES", ambiente.divida)
    com = ambiente.cliente(monkeypatch).get(url).json()

    assert com["datas_da_informacao"] == [
        {"item_id": ambiente.divida, "nome": ambiente.divida, "rotulo": "Há 1–3 meses"}
    ]
    assert {k: v for k, v in com.items() if k != "datas_da_informacao"} == {
        k: v for k, v in sem.items() if k != "datas_da_informacao"
    }
