// @vitest-environment happy-dom
/**
 * `AndamentoDoPlano` — as três etapas, iguais em toda tela do aluno (`RF-431`,
 * `T-421`), e o mapa nunca mente sobre onde o aluno está (`AC-94`, `T-171`).
 */
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AndamentoDoPlano } from "../../../src/componentes/AcompanhamentoDoPlano";
import type { Inicio } from "../../../src/tipos";

function fabricarInicio(fase: string, respondidas = 3, total = 101): Inicio {
  return {
    CASO_ID: "CASO-TESTE",
    estado: "ESTADO-QUALQUER",
    fase,
    mensagem: "mensagem de teste",
    proxima_etapa: { destino: "pergunta", ID_PERGUNTA: null, item_id: null },
    progresso: { respondidas, total },
    valor_em_destaque: null,
    plano_liberado: false,
    versao_do_plano: null,
  } as unknown as Inicio;
}

function etapaEmCurso(): string {
  const atual = document.querySelector('li[aria-current="step"]');
  return atual?.querySelector("strong")?.textContent ?? "";
}

describe("AndamentoDoPlano", () => {
  it("tem exatamente três etapas, com a primeira 'Preencha as informações'", () => {
    render(<AndamentoDoPlano inicio={fabricarInicio("coleta")} />);

    const itens = within(screen.getByRole("navigation", { name: "Andamento do plano" })).getAllByRole("listitem");
    expect(itens).toHaveLength(3);
    expect(itens[0]).toHaveTextContent("Preencha as informações");
    expect(itens[1]).toHaveTextContent("Elaboração e análise do plano");
    expect(itens[2]).toHaveTextContent("Plano liberado");
  });

  it.each([
    ["coleta", "Preencha as informações"],
    ["revisao", "Elaboração e análise do plano"],
    ["reprovado", "Elaboração e análise do plano"],
    ["plano", "Plano liberado"],
  ])("AC-94: na fase %s a etapa atual é '%s' e é só uma", (fase, rotulo) => {
    render(<AndamentoDoPlano inicio={fabricarInicio(fase)} />);

    expect(document.querySelectorAll('li[aria-current="step"]')).toHaveLength(1);
    expect(etapaEmCurso()).toBe(rotulo);
  });

  it("T-171: fase desconhecida cai na análise, não no começo, e não dá ordem", () => {
    render(<AndamentoDoPlano inicio={fabricarInicio("fase_futura")} />);

    expect(etapaEmCurso()).toBe("Elaboração e análise do plano");
    expect(screen.queryByText(/Faça a próxima ação/i)).toBeNull();
    expect(screen.getByText(/está com a equipe/i)).toBeInTheDocument();
  });

  it("sem 'inicio' (telas de coleta) vale a fase de coleta", () => {
    render(<AndamentoDoPlano fase="coleta" />);

    expect(etapaEmCurso()).toBe("Preencha as informações");
  });

  it("AC-96: na coleta, o que falta vem COM unidade", () => {
    render(<AndamentoDoPlano inicio={fabricarInicio("coleta", 3, 101)} />);

    expect(screen.getByText("Faltam 98 perguntas.")).toBeInTheDocument();
  });

  it("AC-96: uma pergunta restante fala no singular", () => {
    render(<AndamentoDoPlano inicio={fabricarInicio("coleta", 100, 101)} />);

    expect(screen.getByText("Falta 1 pergunta.")).toBeInTheDocument();
  });

  it('T-293: com fichas abertas mostra só as respondidas, nunca "faltam"', () => {
    const inicio = fabricarInicio("coleta", 59, 152);
    inicio.progresso.fichas_abertas = true;
    render(<AndamentoDoPlano inicio={inicio} />);

    expect(screen.getByText("Você já respondeu 59 perguntas.")).toBeInTheDocument();
    expect(screen.queryByText(/Faltam/)).not.toBeInTheDocument();
  });

  it("AC-115: nenhuma etapa é clicável — o andamento informa, não navega", () => {
    const { container } = render(<AndamentoDoPlano inicio={fabricarInicio("plano")} />);

    expect(container.querySelector('button, a, [role="button"], [tabindex]')).toBeNull();
  });
});
