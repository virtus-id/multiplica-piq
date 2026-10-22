// @vitest-environment happy-dom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ResumoDaFicha from "../../../src/componentes/ResumoDaFicha";
import type { Pergunta } from "../../../src/tipos";

function campo(extra: Partial<Pergunta>): Pergunta {
  return {
    CASO_ID: "C",
    ID: "B3.DF01",
    bloco: 3,
    tipo: "MOEDA",
    enunciado: "Qual é o valor mensal de Aluguel?",
    opcoes: [],
    escopo_repeticao: "ITEM_DESPESA",
    item_id: "I1",
    posicao: null,
    total_na_ficha: null,
    admite_nao_sei: false,
    valor_atual: null,
    respondida_como_nao_sei: false,
    valores_marcados: [],
    aviso: null,
    ...extra,
  } as Pergunta;
}

describe("ResumoDaFicha (T-410)", () => {
  it("mostra o valor em reais e a escolha Fixo/Variável pelo rótulo da opção", () => {
    render(
      <ResumoDaFicha
        campos={[
          campo({ valor_atual: "1500.50" }),
          campo({
            ID: "B3.DF02",
            tipo: "SELECAO_UNICA",
            valor_atual: "FIXA",
            opcoes: [
              { rotulo: "Fixo", valor_interno: "FIXA", admite_nao_sei: false },
              { rotulo: "Variável", valor_interno: "VARIAVEL", admite_nao_sei: false },
            ],
          }),
        ]}
      />,
    );

    expect(screen.getByText("R$ 1.500,50")).toBeInTheDocument();
    expect(screen.getByText("Fixo")).toBeInTheDocument();
  });

  it("campo em branco aparece como travessão", () => {
    render(<ResumoDaFicha campos={[campo({ valor_atual: null })]} />);

    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
