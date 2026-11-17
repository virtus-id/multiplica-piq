// @vitest-environment happy-dom
/**
 * `Explicacao` — o ícone ⓘ de ajuda dos campos numéricos da ficha de dívida
 * (`RF-562`, `AC-600`, `AC-601`, `EC-99`).
 *
 * `happy-dom`, não `jsdom`: a cadeia de dependências do jsdom quebra neste
 * Node 22.9 (`ERR_REQUIRE_ESM` em `@csstools/css-calc`).
 *
 * Queries acessíveis (`getByRole`), nunca seletor por classe.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import Explicacao from "../../../src/componentes/Explicacao";

const O_QUE_E = "Quanto você deve hoje nesta dívida.";
const ONDE_ENCONTRAR = "No DDC, que você pede no aplicativo do seu banco.";

function montar() {
  render(
    <Explicacao
      campo="Saldo devedor"
      oQueE={O_QUE_E}
      ondeEncontrar={ONDE_ENCONTRAR}
    />,
  );
  return screen.getByRole("button", { name: "O que é Saldo devedor?" });
}

describe("Explicacao", () => {
  it("fecha por padrão — sem o balão nem `aria-expanded`", () => {
    const botao = montar();

    expect(botao).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("hover abre o balão; `mouseleave` fecha", () => {
    const botao = montar();

    fireEvent.mouseEnter(botao);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    expect(botao).toHaveAttribute("aria-expanded", "true");

    fireEvent.mouseLeave(botao);
    expect(screen.queryByRole("tooltip")).toBeNull();
    expect(botao).toHaveAttribute("aria-expanded", "false");
  });

  it("`Tab` foca e abre; `Escape` fecha e devolve o foco ao botão", async () => {
    const usuario = userEvent.setup();
    const botao = montar();

    await usuario.tab();
    expect(botao).toHaveFocus();
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    fireEvent.keyDown(botao, { key: "Escape" });
    expect(screen.queryByRole("tooltip")).toBeNull();
    expect(botao).toHaveFocus();
  });

  it("clique no botão abre; clique fora fecha", () => {
    const botao = montar();

    fireEvent.click(botao);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("toque no botão abre; toque fora fecha", () => {
    const botao = montar();

    fireEvent.touchStart(botao);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    fireEvent.touchStart(document.body);
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("`aria-label`, `aria-expanded` e `aria-describedby` corretos nos dois estados", () => {
    const botao = montar();
    const idDescricao = botao.getAttribute("aria-describedby");
    expect(idDescricao).toBeTruthy();
    expect(botao).toHaveAttribute("aria-label", "O que é Saldo devedor?");
    expect(botao).toHaveAttribute("aria-expanded", "false");

    fireEvent.mouseEnter(botao);
    const balao = screen.getByRole("tooltip");
    expect(balao).toHaveAttribute("id", idDescricao);
    expect(botao).toHaveAttribute("aria-expanded", "true");
    expect(botao).toHaveAttribute("aria-describedby", idDescricao as string);
  });

  it("o balão mostra o conteúdo recebido e nunca é modal", () => {
    const botao = montar();

    fireEvent.mouseEnter(botao);
    const balao = screen.getByRole("tooltip");

    expect(balao).toHaveTextContent(O_QUE_E);
    expect(balao).toHaveTextContent(ONDE_ENCONTRAR);
    // `role="dialog"`/modal capturaria o foco e bloquearia o campo ao lado
    // (`EC-99`) — o balão nunca é nenhum dos dois.
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
