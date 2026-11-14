"""Sem a lista do revisor, a saída é a de antes — `RF-545`, `AC-554` (`T-565`).

Teste de caracterização escrito ANTES de `RF-545` tocar o motor: os valores de
`hash_inputs` e `SNAPSHOT_ID` abaixo foram lidos da execução de `calcular_plano`
na branch anterior à `T-566`, não escritos à mão. Cada gabarito e invariante
roda o motor como hoje e tem de reproduzi-los byte a byte.

`GAB-05` (troca) não passa por `calcular_plano` no seu próprio teste: aqui
roda o motor sobre o mesmo estado neutro que ele usa (sem dívidas).
"""

from collections.abc import Callable

import pytest

from engine.estado import EstadoFinanceiro
from engine.motor import calcular_plano
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.fixtures.carregar import carregar_gab_a, carregar_gab_b, carregar_gab_c
from tests.invariantes.test_gab01_seguro import _estado_com_seguro_embutido
from tests.invariantes.test_gab02_inventario import _estado_inventario_incompleto
from tests.invariantes.test_gab03_rotativo import _estado_com_rotativo_sem_dados
from tests.invariantes.test_gab04_estabilizacao import _estado_gab04
from tests.invariantes.test_gab05_troca import _estado_financeiro_neutro

# (nome, estado, hash_inputs, SNAPSHOT_ID) — congelados antes de RF-545.
_CONGELADOS: tuple[tuple[str, Callable[[], EstadoFinanceiro], str, str], ...] = (
    (
        "GAB-A",
        carregar_gab_a,
        "738f762d135d57d3f9fbc9a9e353c20f6ffd686ad07ffb129e2d0327229fd4fa",
        "012fe55fd6a717470634d1962214c49f7870f28918751b15f2dd3453f35ab404",
    ),
    (
        "GAB-B",
        carregar_gab_b,
        "44f395e05b7042f1a828bb129c0098b5999b516f38a5aba612febe18d9ab057e",
        "629983d30ed0eb8e0b57d6d598902871776c2eb2ee5ca2eb9af7babfbaf220fe",
    ),
    (
        "GAB-C",
        carregar_gab_c,
        "add026ae453d2d0bd48de1ac6089f99ba3be7d9ac218fb1dddade690267842e2",
        "4bfbb4eb6c38e35979118972b09fffed454b6558021055ef3dc79c87b75f8445",
    ),
    (
        "GAB-01",
        _estado_com_seguro_embutido,
        "b1c2f434029047a2725a90c24831dec2a450c6c5409aca5891bf269d48edbdc8",
        "4bda272909aee2e699215c52765e7e7362b81d15e52819d1b82de77c770e6fac",
    ),
    (
        "GAB-02",
        _estado_inventario_incompleto,
        "bcc03ae3ff14a3871363ad5e03d7e678efa9d2f916a40cbde44e8fe1ce96dae0",
        "6b70e84ce4dac600266521902b5c9760c5a57ad5ab920d2ae1488cc550cb6697",
    ),
    (
        "GAB-03",
        _estado_com_rotativo_sem_dados,
        "7dfdd691292e2ae6bb47a42aa87303d825f3d80690faa9e5e8d4046c9dba92a7",
        "4451f469f6adcd75a5d8794e3758115915c66401a1e8b5c7110c166e24f31fa1",
    ),
    (
        "GAB-04",
        _estado_gab04,
        "da746d239e29aab1e2a8835d322f0d5df3691dd719bff8bf891dd02e5909d96e",
        "519f6dba0c435b5fdae1e3ee7c854afcc4392bdeca618edee978689e3b48f0dc",
    ),
    (
        "GAB-05",
        _estado_financeiro_neutro,
        "76e9c1a954fb7af4b3175efc286b0ac7bc2d619cd4867cdf919ceb3ef3ba61dc",
        "3372a6d58bbc12c3e5e05de7ecedf646e0604431b3b3e96838114ff025cafba9",
    ),
)


@pytest.mark.parametrize(
    ("estado", "hash_inputs", "snapshot_id"),
    [pytest.param(estado, h, s, id=nome) for nome, estado, h, s in _CONGELADOS],
)
def test_ac554_sem_a_lista_hash_e_snapshot_id_sao_os_de_antes(
    estado: Callable[[], EstadoFinanceiro], hash_inputs: str, snapshot_id: str
) -> None:
    parametros = FonteParametrosArquivo().carregar("1.0.1")
    snapshot = calcular_plano(estado(), parametros)
    assert snapshot.hash_inputs == hash_inputs
    assert snapshot.SNAPSHOT_ID == snapshot_id
