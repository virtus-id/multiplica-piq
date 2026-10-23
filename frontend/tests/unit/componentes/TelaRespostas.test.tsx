// @vitest-environment happy-dom
/**
 * `TelaRespostas` — uma página só, com todas as partes, índice fixo e o mesmo
 * layout para ver e editar (`T-422`, `RF-433`; `RF-68`, `RF-114`, `RF-115`,
 * `AC-100`, `AC-101`).
 *
 * Textos inventados: o que se prova é a ESTRUTURA, não a redação do questionário.
 */
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TelaRespostas, { agruparPorItem } from "../../../src/telas/TelaRespostas";
import * as api from "../../../src/services/api";
import type { ParteDasRespostas, RespostaDada } from "../../../src/tipos";

beforeEach(() => {
  // O happy-dom não rola: o que se prova é a chamada, não a animação.
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

function resposta(
  ID: string,
  item_id: string | null,
  extra: Partial<RespostaDada> = {},
): RespostaDada {
  return {
    ID,
    item_id,
    enunciado: `Enunciado ${ID}${item_id ? ` (${item_id})` : ""}?`,
    respondida_como_nao_sei: false,
    valores: [`valor ${ID}`],
    ...extra,
  };
}

const PARTES: ParteDasRespostas[] = [
  { bloco: 1, rotulo: "Parte Um", total_de_perguntas: 10, respondidas: [resposta("B1.01", null)] },
  { bloco: 2, rotulo: "Parte Dois", total_de_perguntas: 4, respondidas: [] },
  {
    bloco: 3,
    rotulo: "Parte Três",
    total_de_perguntas: 8,
    respondidas: [
      resposta("B5.A", "D001"),
      resposta("B5.A", "D002"),
      resposta("B5.B", "D001", { respondida_como_nao_sei: true, valores: [] }),
      resposta("B5.B", "D002"),
    ],
  },
];

function montar(extra: { editavel?: boolean; pode_retomar_edicao?: boolean } = {}, fase?: "plano") {
  vi.spyOn(api, "obterRespostasDoCaso").mockResolvedValue({
    CASO_ID: "C1",
    partes: PARTES,
    ...extra,
  });
  const voltar = vi.fn();
  render(<TelaRespostas casoId="C1" voltar={voltar} fase={fase} />);
  return { voltar };
}

describe("agruparPorItem", () => {
  it("soltas primeiro; um grupo por item, na ordem de aparição, sem reordenar as perguntas", () => {
    const grupos = agruparPorItem(PARTES[2].respondidas);
    expect(grupos.map((g) => g.titulo)).toEqual(["Dívida 1", "Dívida 2"]);
    expect(grupos[0].respostas.map((r) => r.ID)).toEqual(["B5.A", "B5.B"]);
    expect(grupos[1].respostas.map((r) => r.item_id)).toEqual(["D002", "D002"]);

    const mistas = agruparPorItem([resposta("X", "D001"), resposta("Y", null)]);
    expect(mistas[0]).toMatchObject({ itemId: null, titulo: null });
  });
});

describe("agruparPorItem — o título é o tipo da ficha", () => {
  it("despesa não é dívida e a numeração recomeça a cada tipo", () => {
    const grupos = agruparPorItem([
      resposta("R1", "REND001"),
      resposta("V1", "DESP001"),
      resposta("V1", "DESP002"),
      resposta("N1", "NM001"),
      resposta("E1", "EXT001"),
      resposta("B5.A", "D001"),
    ]);

    expect(grupos.map((g) => g.titulo)).toEqual([
      "Renda adicional 1",
      "Despesa 1",
      "Despesa 2",
      "Despesa não mensal 1",
      "Valor extraordinário 1",
      "Dívida 1",
    ]);
  });
});

describe("TelaRespostas — a página única (RF-433)", () => {
  it("mostra TODAS as partes na mesma página, inclusive a vazia, sem menu lateral", async () => {
    montar({ editavel: false, pode_retomar_edicao: true });

    expect(await screen.findByRole("heading", { level: 2, name: "Parte Um" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Parte Dois" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Parte Três" })).toBeInTheDocument();
    expect(screen.getByText("Você ainda não respondeu nada desta parte.")).toBeInTheDocument();
    expect(screen.getByText("1 resposta de 10 perguntas")).toBeInTheDocument();
    expect(screen.getByText("Enunciado B1.01?")).toBeInTheDocument();
    // Dados de dívidas diferentes ficam em grupos separados.
    expect(screen.getByRole("heading", { level: 3, name: "Dívida 1" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Dívida 2" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Partes das respostas" })).not.toBeInTheDocument();
  });

  it("o índice leva a cada parte por rolagem, sem trocar o conteúdo", async () => {
    montar({ editavel: false });
    const indice = await screen.findByRole("navigation", { name: "Seções das respostas" });
    expect(within(indice).getAllByRole("button")).toHaveLength(3);

    fireEvent.click(within(indice).getByRole("button", { name: "Parte Três" }));

    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
    expect(within(indice).getByRole("button", { name: "Parte Três" })).toHaveAttribute(
      "aria-current",
      "true",
    );
    expect(screen.getByRole("heading", { level: 2, name: "Parte Um" })).toBeInTheDocument();
  });

  it("a busca acha pergunta ou resposta e leva ao item", async () => {
    montar({ editavel: false });
    const busca = await screen.findByLabelText("Buscar pergunta ou resposta");

    fireEvent.change(busca, { target: { value: "B5.B" } });
    const achado = (await screen.findAllByRole("button", { name: /Enunciado B5\.B/ }))[0];
    fireEvent.click(achado);

    expect(document.getElementById("resposta-3-B5.B-D001")).not.toBeNull();
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });

  it('"Não sei" antigo continua legível como resposta', async () => {
    montar({ editavel: false });
    expect((await screen.findAllByText("Você respondeu: não sei.")).length).toBeGreaterThan(0);
  });
});

describe("TelaRespostas — visualizar × editar (RF-114/RF-115)", () => {
  it("em conferência: modo visualizar, sem campos, com a faixa de análise e o botão de editar", async () => {
    montar({ editavel: false, pode_retomar_edicao: true });

    expect(await screen.findByText("Seu plano está em elaboração e análise.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Editar respostas/ })).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Salvar alterações/ })).not.toBeInTheDocument();
  });

  it("em cálculo: modo visualizar e sem a ação de editar", async () => {
    montar({ editavel: false, pode_retomar_edicao: false });

    expect(await screen.findByText("Seu plano está em elaboração e análise.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Editar respostas/ })).not.toBeInTheDocument();
  });

  it("plano liberado: só consulta, sem dizer que está em análise", async () => {
    montar({ editavel: false, pode_retomar_edicao: false }, "plano");

    expect(await screen.findByText("Seu plano de quitação já foi liberado.")).toBeInTheDocument();
    expect(screen.queryByText(/em elaboração e análise/)).not.toBeInTheDocument();
  });

  it("editar pede confirmação, retira o plano e a página passa ao modo editar", async () => {
    const retomar = vi.spyOn(api, "retomarEdicao").mockResolvedValue({ estado: "COLETA_INICIAL" });
    vi.spyOn(api, "obterPergunta").mockResolvedValue({ pergunta: null });
    const obter = vi
      .spyOn(api, "obterRespostasDoCaso")
      .mockResolvedValueOnce({ CASO_ID: "C1", partes: PARTES, editavel: false, pode_retomar_edicao: true })
      .mockResolvedValue({ CASO_ID: "C1", partes: PARTES, editavel: true, pode_retomar_edicao: false });
    render(<TelaRespostas casoId="C1" voltar={vi.fn()} />);

    fireEvent.click(await screen.findByRole("button", { name: /Editar respostas/ }));
    // Nada acontece até confirmar.
    expect(retomar).not.toHaveBeenCalled();
    expect(screen.getByText("Alterar suas informações?")).toBeInTheDocument();

    const confirmar = screen.getAllByRole("button", { name: "Editar respostas" });
    fireEvent.click(confirmar[confirmar.length - 1]);

    expect(await screen.findByText("Revise suas informações")).toBeInTheDocument();
    expect(retomar).toHaveBeenCalledWith("C1");
    expect(obter).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("button", { name: "Salvar alterações" })).toBeDisabled();
  });

  it('"Continuar aguardando" não retira nada', async () => {
    const retomar = vi.spyOn(api, "retomarEdicao");
    montar({ editavel: false, pode_retomar_edicao: true });

    fireEvent.click(await screen.findByRole("button", { name: /Editar respostas/ }));
    fireEvent.click(screen.getByRole("button", { name: "Continuar aguardando" }));

    expect(retomar).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /Editar respostas/ })).toBeInTheDocument();
  });

  it("o servidor recusa (409): a mensagem dele aparece e o plano segue em conferência", async () => {
    vi.spyOn(api, "retomarEdicao").mockRejectedValue(new Error("Seu plano não está em conferência."));
    montar({ editavel: false, pode_retomar_edicao: true });

    fireEvent.click(await screen.findByRole("button", { name: /Editar respostas/ }));
    const confirmar = screen.getAllByRole("button", { name: "Editar respostas" });
    fireEvent.click(confirmar[confirmar.length - 1]);

    expect(await screen.findByRole("alert")).toHaveTextContent("Seu plano não está em conferência.");
    expect(screen.queryByText("Revise suas informações")).not.toBeInTheDocument();
  });

  it("sem o campo `editavel` (servidor antigo) a tela é editável como sempre", async () => {
    vi.spyOn(api, "obterPergunta").mockResolvedValue({ pergunta: null });
    montar({});

    expect(await screen.findByText("Revise suas informações")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar alterações" })).toBeInTheDocument();
  });
});

describe("TelaRespostas — taxa e dinheiro como o aluno digitou (T-335)", () => {
  it('TAXA aparece como "8%" e MOEDA como "R$ 2.276,76"', async () => {
    vi.spyOn(api, "obterRespostasDoCaso").mockResolvedValue({
      CASO_ID: "C1",
      editavel: false,
      partes: [
        {
          bloco: 5,
          rotulo: "Parte Cinco",
          total_de_perguntas: 2,
          respondidas: [
            resposta("B5.D01A", "D006", { tipo: "TAXA", valores: ["0.08"] }),
            resposta("B5.B03", "D006", { tipo: "MOEDA", valores: ["2276.76"] }),
          ],
        },
      ],
    });
    render(<TelaRespostas casoId="C1" voltar={vi.fn()} />);

    expect(await screen.findByText("8%")).toBeInTheDocument();
    expect(screen.getByText("R$ 2.276,76")).toBeInTheDocument();
    expect(screen.queryByText("0.08")).not.toBeInTheDocument();
  });
});
