// @vitest-environment happy-dom
/**
 * `AlertaInventario` — o alerta permanente de inventário incompleto
 * (`RF-86`, `RF-87`, `AC-133`, `AC-154`, T-251, `T-658`/`T-661` — `RF-559`).
 *
 * O componente só mostra o que o servidor devolveu: mensagem e ações por
 * pendência; sem pendência, nada no DOM.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import AlertaInventario, {
  ContextoDoAlerta,
} from "../../../src/componentes/AlertaInventario";
import * as api from "../../../src/services/api";

afterEach(() => {
  vi.restoreAllMocks();
});

// `RENDA_EXTRA_SEM_ITEM` — escopo e `ID_PARA_CORRIGIR` presentes, para
// exercitar os dois botões juntos (`AC-133`).
const RENDA_SEM_ITEM: api.PendenciaDeInventario = {
  tipo: "INVENTARIO",
  codigo: "RENDA_EXTRA_SEM_ITEM",
  ID: "B3.03",
  ID_PARA_CORRIGIR: "B3.03",
  item_id: null,
  escopo: "RENDA_ADICIONAL_ID",
  enunciado: "Você informou que possui renda extra, mas ainda não cadastrou nenhuma.",
  mensagem: "Você informou que possui renda extra, mas ainda não cadastrou nenhuma.",
};

// `T-647`/`T-657` (`RF-559`): `SEM_DIVIDAS` — escopo `DIVIDA_ID`,
// `ID_PARA_CORRIGIR` nulo (não há mais pergunta de quantidade a corrigir).
const SEM_DIVIDAS: api.PendenciaDeInventario = {
  tipo: "INVENTARIO",
  codigo: "SEM_DIVIDAS",
  ID: null,
  ID_PARA_CORRIGIR: null,
  item_id: null,
  escopo: "DIVIDA_ID",
  enunciado: "Você ainda não cadastrou nenhuma dívida.",
  mensagem: "Você ainda não cadastrou nenhuma dívida.",
};

function montar(pendencias: api.PendenciaDeInventario[], irPara = vi.fn()) {
  const obter = vi
    .spyOn(api, "obterInventario")
    .mockResolvedValue({ pendencias });
  const utilidades = render(
    <ContextoDoAlerta.Provider
      value={{ casoId: "CASO-1", irPara, navegacao: { tela: "inicio" } }}
    >
      <AlertaInventario />
    </ContextoDoAlerta.Provider>,
  );
  return { irPara, obter, ...utilidades };
}

describe("AlertaInventario", () => {
  it("AC-133: anuncia a mensagem do servidor, com uma ação por pendência", async () => {
    const { irPara } = montar([RENDA_SEM_ITEM]);

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(RENDA_SEM_ITEM.mensagem);

    const cadastrar = screen.getByRole("button", {
      name: "Cadastrar as fichas",
    });
    expect(cadastrar).toHaveAccessibleDescription(RENDA_SEM_ITEM.mensagem);
    await userEvent.click(cadastrar);
    expect(irPara).toHaveBeenCalledWith({
      tela: "fichas",
      escopo: "RENDA_ADICIONAL_ID",
    });

    await userEvent.click(
      screen.getByRole("button", { name: "Corrigir a resposta" }),
    );
    expect(irPara).toHaveBeenCalledWith({
      tela: "respostas",
      idPergunta: "B3.03",
    });
  });

  it("AC-154: pendência sem escopo oferece só a correção da declaração", async () => {
    montar([{ ...RENDA_SEM_ITEM, escopo: null, mensagem: "Sem escopo." }]);

    await screen.findByRole("alert");
    expect(
      screen.queryByRole("button", { name: "Cadastrar as fichas" }),
    ).toBeNull();
    expect(
      screen.getByRole("button", { name: "Corrigir a resposta" }),
    ).toBeInTheDocument();
  });

  it("sem pendência, nada é renderizado", async () => {
    const { obter, container } = montar([]);

    await waitFor(() => expect(obter).toHaveBeenCalledWith("CASO-1"));
    expect(container).toBeEmptyDOMElement();
  });

  it("T-661 (RF-559): SEM_DIVIDAS mostra só 'Cadastrar as fichas'", async () => {
    const { irPara } = montar([SEM_DIVIDAS]);

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(SEM_DIVIDAS.mensagem);

    await userEvent.click(
      screen.getByRole("button", { name: "Cadastrar as fichas" }),
    );
    expect(irPara).toHaveBeenCalledWith({ tela: "fichas", escopo: "DIVIDA_ID" });
  });

  it("T-661 (RF-559): ID_PARA_CORRIGIR nulo não mostra 'Corrigir a resposta'", async () => {
    montar([SEM_DIVIDAS]);

    await screen.findByRole("alert");
    expect(
      screen.queryByRole("button", { name: "Corrigir a resposta" }),
    ).toBeNull();
  });

  it("fora do contexto de um caso (tela da equipe, testes da casca), nada", () => {
    const { container } = render(<AlertaInventario />);
    expect(container).toBeEmptyDOMElement();
  });
});
