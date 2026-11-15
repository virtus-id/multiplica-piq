"""Para o aluno, nada fala do ajuste da ordem — `RF-551`, `AC-574`, `AC-575`
(`T-595`) · plano `R18.9` (Relatório).

Dois snapshots REAIS do mesmo estado (`calcular_plano` com e sem
`ordem_do_revisor`): os textos fixos de `textos-canonicos.yaml` que aparecem
no `ContextoPlano` só diferem nas quatro variantes neutras. Conferido também
no plano serializado da tela e no HTML do PDF liberado e da prévia, que saem
todos de `montar_contexto_plano`.

REGRAS: `RF-551`, `AC-574`, `AC-575`
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterator, Mapping
from dataclasses import replace
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from typing import Any

import pytest
import yaml

from app.casos.maquina import ESTADO_CASO, Caso
from app.http.serializacao_plano import serializar_plano
from engine.estado import EstadoFinanceiro
from engine.motor import calcular_plano
from engine.snapshot import SnapshotOrdem, _serializar_canonico
from persistencia.arquivo.repositorio_snapshots import _desserializar_snapshot
from report.pdf import gerar_html_da_previa, gerar_html_do_plano_liberado
from report.plano import (
    CAMINHO_TEXTOS_CANONICOS,
    ContextoPlano,
    carregar_textos_canonicos,
    montar_contexto_plano,
)
from tests.regras.test_ordem_do_revisor import _estado_ac555, _parametros

_LISTA = ("D003", "D001", "D002")
_YAML: dict[str, Any] = yaml.safe_load(CAMINHO_TEXTOS_CANONICOS.read_text(encoding="utf-8"))
_NEUTROS: Mapping[str, str] = _YAML["ordem_do_revisor"]
#: As quatro variantes de `RF-551`, como o aluno as lê.
_QUATRO_NEUTRAS = frozenset(
    _NEUTROS[chave]
    for chave in (
        "explicacao_primeira",
        "como_funciona_passo_1",
        "resposta_maior_divida",
        "aviso_incomodo",
    )
)
#: Os textos de hoje que essas quatro passagens substituem, em todos os métodos.
_QUATRO_DE_HOJE = frozenset(
    {
        *(
            redacoes[chave]
            for redacoes in _YAML["explicacao_da_posicao"].values()
            for chave in ("primeira", "primeira_com_prioridade")
            if chave in redacoes
        ),
        *(passos[0] for metodo, passos in _YAML["como_funciona"].items() if metodo != "titulo"),
        *(passos[0] for passos in _YAML["como_funciona_com_prioridade"].values()),
        *(
            item["resposta"]
            for item in _YAML["duvidas"]
            if item["pergunta"] == _NEUTROS["pergunta_maior_divida"]
        ),
        _YAML["incomodo"]["aviso"],
    }
)


def _folhas(no: object) -> Iterator[str]:
    if isinstance(no, str):
        yield no
    elif isinstance(no, Mapping):
        for valor in no.values():
            yield from _folhas(valor)
    elif isinstance(no, list | tuple):
        for valor in no:
            yield from _folhas(valor)


_TEXTOS_FIXOS = frozenset(_folhas(_YAML))


def _textos_fixos_do(no: object) -> Iterator[str]:
    """Todo texto do `ContextoPlano` que é, inteiro, um texto do YAML."""
    if isinstance(no, str):
        if no in _TEXTOS_FIXOS:
            yield no
    elif dataclasses.is_dataclass(no) and not isinstance(no, type):
        for campo in dataclasses.fields(no):
            yield from _textos_fixos_do(getattr(no, campo.name))
    elif isinstance(no, Mapping):
        for valor in no.values():
            yield from _textos_fixos_do(valor)
    elif isinstance(no, list | tuple):
        for valor in no:
            yield from _textos_fixos_do(valor)


def _sem_prioridade() -> EstadoFinanceiro:
    """`_estado_ac555` com nota de incômodo 10 em todas (o aviso aparece da
    segunda posição em diante)."""
    estado = _estado_ac555()
    return replace(estado, dividas=tuple(replace(d, PESO_EMOCIONAL=10) for d in estado.dividas))


def _com_prioridade() -> EstadoFinanceiro:
    """Idem, com `D002` negativada: a `§16.4` entra em jogo e os textos de
    hoje são as variantes `_com_prioridade`."""
    estado = _sem_prioridade()
    return replace(
        estado,
        dividas=tuple(
            replace(d, NEGATIVADA=True) if d.DIVIDA_ID == "D002" else d for d in estado.dividas
        ),
    )


def _par(estado: EstadoFinanceiro) -> tuple[SnapshotOrdem, SnapshotOrdem]:
    parametros = _parametros()
    return calcular_plano(estado, parametros), calcular_plano(
        estado, parametros, ordem_do_revisor=_LISTA
    )


def _caso_liberado(snapshot: SnapshotOrdem) -> Caso:
    return Caso(
        CASO_ID="CASO-ORDEM-DO-REVISOR",
        conta_id="CONTA-ORDEM-DO-REVISOR",
        estado=ESTADO_CASO.PLANO_LIBERADO,
        DATA_REFERENCIA=date(2026, 3, 15),
        QUESTIONARIO_VERSION="1.0.0",
        snapshot_raiz_id=snapshot.SNAPSHOT_ID,
        snapshot_liberado_id=snapshot.SNAPSHOT_ID,
        ultima_interacao_em=datetime(2026, 1, 1, tzinfo=UTC),
        criado_em=datetime(2026, 1, 1, tzinfo=UTC),
    )


class _TextoVisivel(HTMLParser):
    """O que o aluno lê no HTML: sem tags, `<style>` nem comentários."""

    def __init__(self) -> None:
        super().__init__()
        self.partes: list[str] = []
        self._dentro_de_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._dentro_de_style = self._dentro_de_style or tag in ("style", "script")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("style", "script"):
            self._dentro_de_style = False

    def handle_data(self, data: str) -> None:
        if not self._dentro_de_style:
            self.partes.append(data)


def _texto_corrido(bruto: str) -> str:
    return " ".join(bruto.split())


def _texto_do_html(bruto: str) -> str:
    leitor = _TextoVisivel()
    leitor.feed(bruto)
    return _texto_corrido(" ".join(leitor.partes))


def _apresentacoes(snapshot: SnapshotOrdem, contexto: ContextoPlano) -> dict[str, str]:
    """Tela (plano serializado), PDF liberado e prévia, como texto corrido."""
    textos = carregar_textos_canonicos()
    tela = " ".join(_folhas(serializar_plano(contexto, textos=textos)))
    return {
        "tela": _texto_corrido(tela),
        "pdf": _texto_do_html(
            gerar_html_do_plano_liberado(
                _caso_liberado(snapshot), snapshot, textos, data_base=date(2026, 3, 15)
            )
        ),
        "previa": _texto_do_html(
            gerar_html_da_previa(snapshot, textos, data_base=date(2026, 3, 15))
        ),
    }


_ESTADOS = [
    pytest.param(_sem_prioridade, id="sem-prioridade"),
    pytest.param(_com_prioridade, id="com-prioridade-16.4"),
]


@pytest.mark.parametrize("montar_estado", _ESTADOS)
def test_ac574_so_as_quatro_variantes_neutras_mudam(montar_estado: Any) -> None:
    sem, com = _par(montar_estado())
    assert sem.ORDEM_DO_REVISOR is None
    assert com.ORDEM_DO_REVISOR == _LISTA
    textos = carregar_textos_canonicos()

    contexto_sem = montar_contexto_plano(sem, textos)
    contexto_com = montar_contexto_plano(com, textos)
    fixos_sem = set(_textos_fixos_do(contexto_sem))
    fixos_com = set(_textos_fixos_do(contexto_com))

    assert fixos_com - fixos_sem == _QUATRO_NEUTRAS
    assert fixos_sem - fixos_com
    assert fixos_sem - fixos_com <= _QUATRO_DE_HOJE
    for passagem in _QUATRO_NEUTRAS:
        minuscula = passagem.lower()
        for proibido in (
            "revisor",
            "especialista",
            "mais cobra juros",
            "a menor",
            "prioriza",
            "garantia de um bem essencial",
            "alterad",
            "ajustad",
        ):
            assert proibido not in minuscula, (proibido, passagem)
    # O carimbo continua dizendo o método.
    assert contexto_com.metodo == contexto_sem.metodo
    assert contexto_com.metodo


@pytest.mark.parametrize("montar_estado", _ESTADOS)
def test_ac574_tela_pdf_liberado_e_previa_sem_mencao_ao_ajuste(montar_estado: Any) -> None:
    sem, com = _par(montar_estado())
    textos = carregar_textos_canonicos()
    contexto_com = montar_contexto_plano(com, textos)

    for onde, texto in _apresentacoes(com, contexto_com).items():
        minusculo = texto.lower()
        assert "revisor" not in minusculo, onde
        assert "especialista" not in minusculo, onde
        for neutra in _QUATRO_NEUTRAS:
            assert neutra in texto, (onde, neutra)
        for de_hoje in _QUATRO_DE_HOJE:
            assert de_hoje not in texto, (onde, de_hoje)
        if onde != "tela":
            assert f"método {contexto_com.metodo}" in texto, onde


def _antigo(snapshot: SnapshotOrdem) -> SnapshotOrdem:
    """O snapshot como linha gravada antes da Rodada 16: sem a chave."""
    bruto = json.loads(json.dumps(_serializar_canonico(snapshot)))
    bruto.pop("ORDEM_DO_REVISOR", None)
    return _desserializar_snapshot(bruto)


@pytest.mark.parametrize(
    "ler", [pytest.param(lambda s: s, id="novo"), pytest.param(_antigo, id="linha-antiga")]
)
def test_ac575_sem_a_lista_os_textos_sao_os_de_hoje(ler: Any) -> None:
    sem, _ = _par(_sem_prioridade())
    snapshot = ler(sem)
    assert snapshot.ORDEM_DO_REVISOR is None
    contexto = montar_contexto_plano(snapshot, carregar_textos_canonicos())
    metodo = snapshot.METODO_RECOMENDADO_PIQ.value

    primeira = contexto.ordem[0]
    assert primeira.explicacao == _YAML["explicacao_da_posicao"][metodo]["primeira"]
    assert contexto.como_funciona == tuple(_YAML["como_funciona"][metodo])
    (resposta,) = [r for p, r in contexto.duvidas if p == _NEUTROS["pergunta_maior_divida"]]
    assert resposta in _QUATRO_DE_HOJE
    avisos = {posicao.aviso_incomodo for posicao in contexto.ordem[1:]}
    assert avisos == {_YAML["incomodo"]["aviso"]}
    assert not set(_textos_fixos_do(contexto)) & _QUATRO_NEUTRAS
