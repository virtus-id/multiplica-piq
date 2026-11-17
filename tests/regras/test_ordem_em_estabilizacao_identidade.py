"""Fora do caso de `RF-552`, o snapshot é o de antes — `AC-577` (`T-603`).

Teste de caracterização escrito ANTES de `RF-552`–`RF-554` tocarem o motor: os
digests abaixo foram lidos da execução de `calcular_plano` na branch anterior à
`T-606`, não escritos à mão. Digest = SHA-256 do snapshot serializado
(`_serializar_canonico` + `json.dumps(sort_keys=True)`) sem os campos novos
(`MOTIVO_POSICAO` de cada posição, `QUITACOES_SO_PARCELAS` de
`prognostico.sem_acao`), que `AC-577` autoriza a aparecer.

Estados em `MODO_ESTABILIZACAO` com capacidade ≤ 0 (`GAB-A` e `GAB-04`) são o
caso de `RF-552` item 2: a ordem publicada pode mudar, e com ela o que a
espelha (`DIVIDA_ALVO_ATUAL`, `PROXIMA_DIVIDA`, `engine/snapshot.py`) e, em
cada cenário, `ORDEM_DE_ATAQUE`/`ORDEM_FORA_DO_HORIZONTE` (Leitura 2,
`AC-577` emendado). `GAB-04` está aqui porque, embora `AC-577` o cite entre os
"de capacidade positiva", o próprio estado tem capacidade −1.000 em
estabilização. O resto do snapshot (diagnóstico, simulação, método, status) é
congelado igual.
"""

import hashlib
import json
from collections.abc import Callable
from dataclasses import replace

import pytest

from engine.estado import (
    CERTEZA_RECURSO_EXTRAORDINARIO,
    JANELA_RECURSO_EXTRAORDINARIO,
    EstadoFinanceiro,
    RecursoExtraordinario,
)
from engine.motor import calcular_plano
from engine.parametros import Parametros
from engine.precisao import dinheiro
from engine.snapshot import SnapshotOrdem, _serializar_canonico
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.fixtures.carregar import carregar_gab_a, carregar_gab_b, carregar_gab_c
from tests.invariantes.test_gab01_seguro import _estado_com_seguro_embutido
from tests.invariantes.test_gab02_inventario import _estado_inventario_incompleto
from tests.invariantes.test_gab03_rotativo import _estado_com_rotativo_sem_dados
from tests.invariantes.test_gab04_estabilizacao import _estado_gab04
from tests.invariantes.test_gab05_troca import _estado_financeiro_neutro
from tests.regras.test_ordem_com_todas_as_dividas import _caso_teste3
from tests.regras.test_ordem_do_revisor import (
    _LISTA,
    _estado,
    _estado_ac555,
    _estado_com_divida_bloqueada,
    _estado_ec80,
)

# Campos novos de RF-553/RF-554: fora do digest em todo estado.
_CAMPOS_NOVOS: frozenset[str] = frozenset({"MOTIVO_POSICAO", "QUITACOES_SO_PARCELAS"})
# RF-552 item 2 (estabilização com capacidade ≤ 0): a ordem publicada e o que
# a espelha podem mudar.
_CAMPOS_DA_ORDEM: frozenset[str] = frozenset(
    {
        "ORDEM_QUITACAO",
        "DIVIDA_ALVO_ATUAL",
        "PROXIMA_DIVIDA",
        "ORDEM_DE_ATAQUE",
        "ORDEM_FORA_DO_HORIZONTE",
    }
)


def _sem_chaves(valor: object, chaves: frozenset[str]) -> object:
    if isinstance(valor, dict):
        return {k: _sem_chaves(v, chaves) for k, v in valor.items() if k not in chaves}
    if isinstance(valor, list):
        return [_sem_chaves(item, chaves) for item in valor]
    return valor


def digest_do_snapshot(snapshot: SnapshotOrdem, *, sem_a_ordem: bool = False) -> str:
    """SHA-256 do snapshot serializado sem os campos novos (e, em
    estabilização com capacidade ≤ 0, sem a ordem publicada)."""
    chaves = _CAMPOS_NOVOS | _CAMPOS_DA_ORDEM if sem_a_ordem else _CAMPOS_NOVOS
    serializado = _sem_chaves(_serializar_canonico(snapshot), chaves)
    texto = json.dumps(serializado, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _parametros() -> Parametros:
    return FonteParametrosArquivo().carregar("1.0.1")


def _estado_ac556() -> EstadoFinanceiro:
    """O estado de `test_ac556_com_estouro_a_ordem_publicada_e_a_de_ataque_e_a_lista`."""
    return _estado(
        "3000",
        ("D001", "3000", "0.02", "200"),
        ("D002", "5000", "0.03", "250"),
        ("D003", "8000", "0.01", "200"),
        ("D004", "300000", "0.005", "1600"),
    )


def _estado_ec78() -> EstadoFinanceiro:
    """O estado de `test_ec78_divida_que_acaba_sozinha_antes_da_vez_e_pulada`."""
    return _estado(
        "4800",
        ("D001", "4000", "0.02", "200"),
        ("D002", "900", "0.00", "300"),
        ("D003", "6000", "0.04", "300"),
    )


def _estado_ac561() -> EstadoFinanceiro:
    """O estado de `test_ac561_verde_e_cenario_adicional_seguem_a_lista` (`PROVAVEL`)."""
    recurso = RecursoExtraordinario(
        ITEM_ID="R1",
        VALOR_RECURSO_EXTRAORDINARIO=dinheiro("1500"),
        JANELA_RECURSO_EXTRAORDINARIO=JANELA_RECURSO_EXTRAORDINARIO.UM_A_TRES_MESES,
        CERTEZA_RECURSO_EXTRAORDINARIO=CERTEZA_RECURSO_EXTRAORDINARIO.PROVAVEL,
    )
    return replace(
        _estado_ac555(),
        CONTRIBUICAO_EXTRA_MENSAL=dinheiro("150"),
        recursos_extraordinarios=(recurso,),
    )


def _plano(
    estado: Callable[[], EstadoFinanceiro], lista: tuple[str, ...] | None = None
) -> Callable[[], SnapshotOrdem]:
    return lambda: calcular_plano(estado(), _parametros(), ordem_do_revisor=lista)


def _plano_v2_ac562() -> SnapshotOrdem:
    estado, parametros = _estado_ac555(), _parametros()
    v1 = calcular_plano(estado, parametros)
    return calcular_plano(estado, parametros, v1, ordem_do_revisor=_LISTA)


_LISTA_AC556 = ("D004", "D003", "D002", "D001")
_LISTA_EC78 = ("D003", "D002", "D001")
_LISTA_EC80 = ("D001", "D003", "D002")

# (nome, snapshot, digest) — congelados antes de RF-552 (capacidade positiva
# ou fora de estabilização: snapshot inteiro, menos os campos novos).
_CONGELADOS: tuple[tuple[str, Callable[[], SnapshotOrdem], str], ...] = (
    (
        "GAB-B",
        _plano(carregar_gab_b),
        "ffc327188c2c669d1da17361dc27250bb912835e42a42c94be95fd34fb0437ba",
    ),
    (
        "GAB-C",
        _plano(carregar_gab_c),
        "df585a5dd183033cba6ace18e2807582988382e9015b08b05779301bab8495fc",
    ),
    (
        "GAB-01",
        _plano(_estado_com_seguro_embutido),
        "edb8ee1d8d0a1e367d15a587163fffc5df097ebbe501f00ea69f6ea0375368a9",
    ),
    (
        "GAB-02",
        _plano(_estado_inventario_incompleto),
        "548f579b88e884038b88f085b3b306825f0dce9673839b345bf99b18299f8298",
    ),
    (
        "GAB-03",
        _plano(_estado_com_rotativo_sem_dados),
        "6140260a6aab816f86f2394bb4344c4735645c85857004fb6224b52d3fce7244",
    ),
    (
        "GAB-05",
        _plano(_estado_financeiro_neutro),
        "0534bc0fd8c086a86c305535b02c20fdde561543475f0c0c2ee24748733bdea6",
    ),
    (
        "teste3-AC-512",
        _plano(_caso_teste3),
        "8f11b967ce1faf8401f57d9ea21f830229c5b370b562a2bb934e07c8051d3440",
    ),
    (
        "AC-555-sem-lista",
        _plano(_estado_ac555),
        "e89f44a06c48ebd999e5b7a028dfd9bb8c26bbbfaa4d843f720c2673b39dba38",
    ),
    (
        "AC-555-com-lista",
        _plano(_estado_ac555, _LISTA),
        "887d8dd1e217335e4f973c4167be36cee0b09b0ec6abf8370f13b2f7043ff641",
    ),
    (
        "AC-556-sem-lista",
        _plano(_estado_ac556),
        "9b3bd0cd0b2f18671b7855ed7379e6a86503ff3c98b620013f3d3b3475c60100",
    ),
    (
        "AC-556-com-lista",
        _plano(_estado_ac556, _LISTA_AC556),
        "fa363c8adb9fed9dac8e632fa58f29292784fd5acd7bf4ba57bcea2963420c29",
    ),
    (
        "AC-557-bloqueada-sem-lista",
        _plano(_estado_com_divida_bloqueada),
        "5cd06ae72407836c1d6441983e350e3ffd92adadd97d9090bed9a4a9e31609f8",
    ),
    (
        "EC-78-com-lista",
        _plano(_estado_ec78, _LISTA_EC78),
        "42b24d8924da6b20aff407a51adc8efe9e8ff9bd91aff8fea19021025dce79c6",
    ),
    (
        "EC-80-sem-lista",
        _plano(_estado_ec80),
        "2377d3b9530e4008d2839e4981713d2778d0e18d08611f81249ea3a1ee5f9c33",
    ),
    (
        "EC-80-com-lista",
        _plano(_estado_ec80, _LISTA_EC80),
        "9dd85387564c89e31182f4bc1add9481b3e42d725502c10fa44bacc4feb3a3be",
    ),
    (
        "AC-561-sem-lista",
        _plano(_estado_ac561),
        "bc95f42d40daca88168bb879d290674aaaa09b0755cd148ad18e35899775a340",
    ),
    (
        "AC-561-com-lista",
        _plano(_estado_ac561, _LISTA),
        "56c371d5ea2524898edb0b986ed67154e0f3a1ecafb070052d648699bf9617e0",
    ),
    (
        "AC-562-v2",
        _plano_v2_ac562,
        "5cf43e2efb542c047444462ce652979c04255e74c7452284864ec2f3c46c75f1",
    ),
)

# Estabilização com capacidade ≤ 0 (RF-552 item 2): sem a ordem publicada.
_CONGELADOS_SEM_A_ORDEM: tuple[tuple[str, Callable[[], SnapshotOrdem], str], ...] = (
    (
        "GAB-A",
        _plano(carregar_gab_a),
        "e098c9c0bbdf0a7fd719d462faf59d99730842780ae16552776a0fd6ebadee54",
    ),
    (
        "GAB-04",
        _plano(_estado_gab04),
        "096a1586d0ea0b541c31fc3abc93aa11676e48f43187bdd1f321a62f2756d8b6",
    ),
)


@pytest.mark.parametrize(
    ("plano", "digest"),
    [pytest.param(plano, d, id=nome) for nome, plano, d in _CONGELADOS],
)
def test_ac577_capacidade_positiva_snapshot_e_o_de_antes(
    plano: Callable[[], SnapshotOrdem], digest: str
) -> None:
    assert digest_do_snapshot(plano()) == digest


@pytest.mark.parametrize(
    ("plano", "digest"),
    [pytest.param(plano, d, id=nome) for nome, plano, d in _CONGELADOS_SEM_A_ORDEM],
)
def test_ac577_estabilizacao_so_a_ordem_pode_mudar(
    plano: Callable[[], SnapshotOrdem], digest: str
) -> None:
    snapshot = plano()
    assert snapshot.diagnostico.MODO_ESTABILIZACAO
    assert snapshot.diagnostico.CAPACIDADE_ATAQUE_CONSERVADORA <= 0
    assert digest_do_snapshot(snapshot, sem_a_ordem=True) == digest
