"""`T-517`, `T-521` — dívida pendente e plano parcial no vocabulário do caso, o
aviso nominal na seção de pendências e a marca por campo ao revisor.

Spec: `specs/calculo-de-divida.spec.md`. O snapshot vem do motor REAL; as
respostas, da ficha da calculadora. A marca por campo está em
`test_premissas_da_divida.py::test_revisor_recebe_so_a_marca_por_campo_da_divida`;
`EC-74` (todas pendentes ⇒ `422`, motor não chamado), em
`test_montagem_divida_calculada.py::test_ec74_todas_pendentes_recusa_com_422_e_nao_chama_o_motor`.

REGRAS: `RF-527`, `RF-528`, `RF-529`, `AC-539`, `AC-540`, `EC-74`
"""

from __future__ import annotations

from dataclasses import replace

from app.http.serializacao_plano import vocabulario_do_caso
from app.montagem.premissas import premissas_da_ficha
from collection.registro import EscopoRepeticao
from engine.tipos import ORDEM_STATUS
from report.plano import VocabularioDoCaso, carregar_textos_canonicos, montar_contexto_plano
from tests.app_aluno.test_pendencias_do_relatorio import _snapshot_base
from tests.app_aluno.test_premissas_da_divida import F, _ficha_nao_sei, _respostas


def _vocabulario_com_pendente() -> VocabularioDoCaso:
    # D001 completa; D003, sem nenhuma resposta útil, pendente em S, P e T
    respostas = _respostas(
        ("D001", _ficha_nao_sei(F.PARCELA)),
        ("D003", _ficha_nao_sei(F.SALDO, F.PARCELA, F.TAXA, F.PRAZO)),
    )
    itens = {EscopoRepeticao.DIVIDA_ID: ("D001", "D003")}
    return vocabulario_do_caso((), respostas, ["D001"], (), premissas_da_ficha(respostas, itens))


def test_ac539_pendente_marca_plano_parcial_e_nomeia_o_campo_faltante() -> None:
    vocabulario = _vocabulario_com_pendente()

    assert vocabulario.plano_parcial is True
    assert vocabulario.dividas_pendentes == (
        ("D003", ("SALDO_DEVEDOR_ATUAL", "PARCELA_CONTRATUAL", "TAXA_EFETIVA_MENSAL_NORMALIZADA")),
    )

    snapshot = replace(_snapshot_base(), ORDEM_STATUS=ORDEM_STATUS.PROVISORIA)
    pendencias = montar_contexto_plano(
        snapshot, carregar_textos_canonicos(), vocabulario
    ).pendencias
    assert pendencias is not None
    nomeadas = {id_: campos for id_, _, campos in pendencias.campos_faltantes_por_divida}
    assert len(nomeadas["D003"]) == 3


def test_ac539_pendente_aparece_mesmo_com_ordem_definitiva_e_fica_fora_da_ordem() -> None:
    snapshot = _snapshot_base()
    contexto = montar_contexto_plano(
        snapshot, carregar_textos_canonicos(), _vocabulario_com_pendente()
    )

    assert contexto.pendencias is not None
    assert "D003" not in {p.DIVIDA_ID for p in contexto.ordem}


def test_caso_sem_pendente_fica_inalterado() -> None:
    respostas = _respostas(("D001", _ficha_nao_sei(F.PARCELA)))
    itens = {EscopoRepeticao.DIVIDA_ID: ("D001",)}
    vocabulario = vocabulario_do_caso(
        (), respostas, ["D001"], (), premissas_da_ficha(respostas, itens)
    )
    textos = carregar_textos_canonicos()
    snapshot = _snapshot_base()

    assert vocabulario.plano_parcial is False
    assert vocabulario.dividas_pendentes == ()
    assert montar_contexto_plano(snapshot, textos, vocabulario).pendencias == (
        montar_contexto_plano(snapshot, textos).pendencias
    )


def test_ac540_revisor_ve_calculado_e_estimado_e_nenhuma_formula_nem_juros() -> None:
    """`AC-540`/`RF-529`: um valor calculado e outro estimado chegam como marca; o payload
    do revisor não leva fórmula, total de juros nem cronograma (`PD-14`)."""
    import json

    from app.http.serializacao_plano import serializar_estado_inputs
    from report.plano import montar_contexto_estado_inputs

    estado = _snapshot_base().estado_inputs
    primeira, segunda = estado.dividas[0].DIVIDA_ID, estado.dividas[1].DIVIDA_ID
    respostas = _respostas(
        (primeira, _ficha_nao_sei(F.PARCELA)),  # calculado
        (segunda, _ficha_nao_sei(F.PARCELA, F.PRAZO)),  # sem parcela nem prazo: estimado
    )
    itens = {EscopoRepeticao.DIVIDA_ID: (primeira, segunda)}
    premissas = premissas_da_ficha(respostas, itens)
    vocabulario = vocabulario_do_caso((), respostas, [primeira, segunda], (), premissas)
    estimada = premissas[1].parcela_estimada
    assert estimada is not None
    # o plano paga a estimada na segunda dívida (a prioritária do exemplo)
    estado = replace(
        estado,
        dividas=(
            estado.dividas[0],
            replace(estado.dividas[1], PAGAMENTO_MENSAL_EFETIVO=estimada.valor),
            *estado.dividas[2:],
        ),
    )

    payload = serializar_estado_inputs(
        montar_contexto_estado_inputs(estado, carregar_textos_canonicos(), vocabulario)
    )

    marcas = {
        (i, c["codigo"]): c["marca"]
        for i, divida in enumerate(payload["dividas"])
        for c in divida["campos"]
        if "marca" in c
    }
    assert set(marcas.values()) == {"calculado", "estimado"}
    assert marcas[(0, "PARCELA_CONTRATUAL")] == "calculado"
    assert (
        marcas[(1, "PAGAMENTO_MENSAL_EFETIVO")] == "estimado"
    )  # nunca `hipotese`/`pendente` (OQ-87)
    texto = json.dumps(payload, ensure_ascii=False).lower()
    assert not any(
        x in texto for x in ("cronograma", "total_de_juros", "total de juros", "formula")
    )
