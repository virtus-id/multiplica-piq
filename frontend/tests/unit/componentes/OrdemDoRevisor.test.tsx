// @vitest-environment happy-dom
/**
 * `OrdemDoRevisor` — a seção "Ordem de quitação" da conferência (`T-599`,
 * `RF-548`, `AC-569`, `AC-570`).
 *
 * Mover só muda a lista na tela; quem recalcula é o botão, que chama
 * `ajustarOrdem`. Prazo e custo, antes e depois, são os da resposta.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import OrdemDoRevisor from "../../../src/componentes/OrdemDoRevisor";
import * as api from "../../../src/services/api";
import type {
  OrdemNaConferencia,
  ResultadoDoAjusteDaOrdem,
} from "../../../src/services/api";

afterEach(() => {
  vi.restoreAllMocks();
});

const VIGENTE = [
  { DIVIDA_ID: "D001", nome: "Cheque especial — CAIXA" },
  { DIVIDA_ID: "D002", nome: "Cartão de crédito — Nubank" },
  { DIVIDA_ID: "D003", nome: "Empréstimo pessoal — BB" },
];

const ORDEM: OrdemNaConferencia = { vigente: VIGENTE, ajustada: false, editavel: true };

const RESULTADO: ResultadoDoAjusteDaOrdem = {
  SNAPSHOT_ID: "S2",
  versao: 2,
  ordem_vigente: ["D002", "D001", "D003"],
  ajustada: true,
  antes: {
    SNAPSHOT_ID: "S1",
    prazo: { meses: 18, estourou_horizonte: false },
    custo_total_de_juros: { valor: "R$ 1.234,56", motivo: null },
  },
  depois: {
    SNAPSHOT_ID: "S2",
    prazo: { meses: 20, estourou_horizonte: false },
    custo_total_de_juros: { valor: "não disponível", motivo: "Sem cronograma" },
  },
};

function montar(
  ordem: OrdemNaConferencia = ORDEM,
  ultimoAjuste: ResultadoDoAjusteDaOrdem | null = null,
) {
  const aoAjustar = vi.fn();
  render(
    <OrdemDoRevisor
      casoId="CASO-1"
      ordem={ordem}
      ultimoAjuste={ultimoAjuste}
      aoAjustar={aoAjustar}
    />,
  );
  return aoAjustar;
}

function nomesNaTela(): string[] {
  const lista = screen.getByRole("list");
  return within(lista)
    .getAllByRole("listitem")
    .map((item) => VIGENTE.find((d) => item.textContent?.includes(d.nome))?.nome ?? "");
}

const recalcular = () => screen.getByRole("button", { name: "Recalcular nesta ordem" });

describe("OrdemDoRevisor — lista e botões (AC-569)", () => {
  it("lista os nomes na ordem vigente, com a indicação de que é a do método", () => {
    montar();
    expect(nomesNaTela()).toEqual(VIGENTE.map((d) => d.nome));
    expect(screen.getByText("Ordem do método")).toBeInTheDocument();
  });

  it("rótulos nomeiam a dívida; subir desativado na primeira e descer na última", () => {
    montar();
    expect(screen.getByRole("button", { name: `Subir ${VIGENTE[0].nome}` })).toBeDisabled();
    expect(screen.getByRole("button", { name: `Descer ${VIGENTE[0].nome}` })).toBeEnabled();
    expect(screen.getByRole("button", { name: `Subir ${VIGENTE[2].nome}` })).toBeEnabled();
    expect(screen.getByRole("button", { name: `Descer ${VIGENTE[2].nome}` })).toBeDisabled();
  });

  it("mover muda só a lista na tela, anuncia a posição e não chama a API", async () => {
    const espiao = vi.spyOn(api, "ajustarOrdem");
    montar();

    await userEvent.click(screen.getByRole("button", { name: `Subir ${VIGENTE[1].nome}` }));

    expect(nomesNaTela()).toEqual([VIGENTE[1].nome, VIGENTE[0].nome, VIGENTE[2].nome]);
    expect(screen.getByRole("status")).toHaveTextContent(`${VIGENTE[1].nome}: posição 1 de 3.`);
    expect(espiao).not.toHaveBeenCalled();
  });

  it("operável por teclado: a dívida que chega à ponta mantém o foco no outro botão", async () => {
    montar();
    const descer = screen.getByRole("button", { name: `Descer ${VIGENTE[1].nome}` });
    descer.focus();

    await userEvent.keyboard("{Enter}");

    expect(nomesNaTela()).toEqual([VIGENTE[0].nome, VIGENTE[2].nome, VIGENTE[1].nome]);
    expect(screen.getByRole("button", { name: `Subir ${VIGENTE[1].nome}` })).toHaveFocus();
  });

  it('"Recalcular nesta ordem" só com a lista diferente da vigente e o motivo preenchido', async () => {
    montar();
    expect(recalcular()).toBeDisabled(); // lista igual, motivo vazio

    await userEvent.type(screen.getByLabelText("Motivo interno"), "Negativada primeiro");
    expect(recalcular()).toBeDisabled(); // lista igual

    await userEvent.clear(screen.getByLabelText("Motivo interno"));
    await userEvent.click(screen.getByRole("button", { name: `Descer ${VIGENTE[0].nome}` }));
    expect(recalcular()).toBeDisabled(); // motivo vazio

    await userEvent.type(screen.getByLabelText("Motivo interno"), "   ");
    expect(recalcular()).toBeDisabled(); // só espaços

    await userEvent.type(screen.getByLabelText("Motivo interno"), "Negativada primeiro");
    expect(recalcular()).toBeEnabled();

    // De volta à ordem vigente: nada a recalcular.
    await userEvent.click(screen.getByRole("button", { name: `Subir ${VIGENTE[0].nome}` }));
    expect(recalcular()).toBeDisabled();
  });

  it('"Voltar à ordem do método" não aparece com a ordem do método', () => {
    montar();
    expect(screen.queryByRole("button", { name: "Voltar à ordem do método" })).toBeNull();
  });

  it("sem edição (editavel = false): lista só leitura, sem botões nem motivo", () => {
    montar({ ...ORDEM, ajustada: true, editavel: false });
    expect(nomesNaTela()).toEqual(VIGENTE.map((d) => d.nome));
    expect(screen.getByText("Ajustada na conferência")).toBeInTheDocument();
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    expect(screen.queryByLabelText("Motivo interno")).toBeNull();
  });
});

describe("OrdemDoRevisor — recálculo (AC-570)", () => {
  it("envia a lista e o motivo, e entrega o resultado à tela", async () => {
    const espiao = vi.spyOn(api, "ajustarOrdem").mockResolvedValue(RESULTADO);
    const aoAjustar = montar();

    await userEvent.click(screen.getByRole("button", { name: `Subir ${VIGENTE[1].nome}` }));
    await userEvent.type(screen.getByLabelText("Motivo interno"), " Negativada primeiro ");
    await userEvent.click(recalcular());

    expect(espiao).toHaveBeenCalledWith("CASO-1", ["D002", "D001", "D003"], "Negativada primeiro");
    expect(aoAjustar).toHaveBeenCalledWith(RESULTADO);
  });

  it("voltar à ordem do método envia a lista vazia sem motivo (OQ-99)", async () => {
    const espiao = vi.spyOn(api, "ajustarOrdem").mockResolvedValue(RESULTADO);
    montar({ ...ORDEM, ajustada: true });

    await userEvent.click(screen.getByRole("button", { name: "Voltar à ordem do método" }));

    expect(espiao).toHaveBeenCalledWith("CASO-1", [], "");
  });

  it("botões desativados e progresso anunciado durante o envio", async () => {
    let concluir: (r: ResultadoDoAjusteDaOrdem) => void = () => {};
    vi.spyOn(api, "ajustarOrdem").mockReturnValue(
      new Promise((resolver) => {
        concluir = resolver;
      }),
    );
    montar({ ...ORDEM, ajustada: true });
    await userEvent.click(screen.getByRole("button", { name: `Subir ${VIGENTE[1].nome}` }));
    await userEvent.type(screen.getByLabelText("Motivo interno"), "Motivo");

    await userEvent.click(recalcular());

    expect(screen.getByRole("status")).toHaveTextContent("Recalculando…");
    for (const botao of screen.getAllByRole("button")) expect(botao).toBeDisabled();
    concluir(RESULTADO);
    expect(await screen.findByText("Plano recalculado.")).toBeInTheDocument();
  });

  it.each([
    [409, "Este plano saiu da conferência."],
    [422, "D009 não está entre as dívidas elegíveis."],
  ])("com %i, a mensagem da rota aparece e lista e motivo ficam", async (status, detalhe) => {
    vi.spyOn(api, "ajustarOrdem").mockRejectedValue(new api.ErroHttp(status, detalhe));
    const aoAjustar = montar();
    await userEvent.click(screen.getByRole("button", { name: `Descer ${VIGENTE[0].nome}` }));
    await userEvent.type(screen.getByLabelText("Motivo interno"), "Motivo interno");

    await userEvent.click(recalcular());

    expect(await screen.findByRole("alert")).toHaveTextContent(detalhe);
    expect(nomesNaTela()).toEqual([VIGENTE[1].nome, VIGENTE[0].nome, VIGENTE[2].nome]);
    expect(screen.getByLabelText("Motivo interno")).toHaveValue("Motivo interno");
    expect(recalcular()).toBeEnabled();
    expect(aoAjustar).not.toHaveBeenCalled();
  });

  it("mostra prazo e custo antes e depois, como vieram do servidor", () => {
    montar(ORDEM, RESULTADO);
    const tabela = screen.getByRole("table", { name: "Antes e depois do recálculo" });
    const prazo = within(tabela).getByRole("row", { name: /Prazo/ });
    expect(prazo).toHaveTextContent("18 meses");
    expect(prazo).toHaveTextContent("20 meses");
    const custo = within(tabela).getByRole("row", { name: /Custo total de juros/ });
    expect(custo).toHaveTextContent("R$ 1.234,56");
    expect(custo).toHaveTextContent("não disponível");
    expect(custo).toHaveTextContent("Sem cronograma");
  });

  it("prazo que estoura o horizonte é dito, não contado", () => {
    montar(ORDEM, {
      ...RESULTADO,
      depois: { ...RESULTADO.depois, prazo: { meses: 120, estourou_horizonte: true } },
    });
    const prazo = within(screen.getByRole("table")).getByRole("row", { name: /Prazo/ });
    expect(prazo).toHaveTextContent("não quita no horizonte");
    expect(prazo).not.toHaveTextContent("120");
  });
});
