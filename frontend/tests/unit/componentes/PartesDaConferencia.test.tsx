// @vitest-environment happy-dom
/**
 * `TabelaDeDividas` — a marca por valor (`T-514`; `RF-528`, `RF-529`, `AC-540`).
 *
 * Só a marca em texto chega ao revisor: sem marca, a célula é a de sempre.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TabelaDeDividas } from "../../../src/componentes/revisao/PartesDaConferencia";
import type { EstadoInputs } from "../../../src/services/api";
import type { Plano } from "../../../src/tipos";

const PLANO = { ordem: [] } as unknown as Plano;

function entradas(
  campos: EstadoInputs["dividas"][number]["campos"],
): EstadoInputs {
  return {
    campos: [],
    perfil_comportamental: [],
    sinais_comportamentais: [],
    dividas: [{ DIVIDA_ID: "D001", nome: "Cartão", campos }],
  };
}

describe("TabelaDeDividas — marca por valor", () => {
  it("mostra o chip em texto só no valor calculado ou estimado", () => {
    render(
      <TabelaDeDividas
        plano={PLANO}
        entradas={entradas([
          {
            nome: "Saldo",
            codigo: "SALDO_DEVEDOR_ATUAL",
            valor: "R$ 10.000,00",
          },
          {
            nome: "Taxa",
            codigo: "TAXA_EFETIVA_MENSAL_NORMALIZADA",
            valor: "2,00% a.m.",
            marca: "calculado",
          },
          { nome: "Parcela", codigo: "PARCELA_CONTRATUAL", valor: "R$ 0,00" },
          {
            nome: "Pagamento",
            codigo: "PAGAMENTO_MENSAL_EFETIVO",
            valor: "R$ 528,72",
            marca: "estimado",
          },
        ])}
      />,
    );
    expect(screen.getByText("calculado")).toBeInTheDocument();
    expect(screen.getByText("estimado")).toBeInTheDocument();
    expect(screen.getAllByText(/^(calculado|estimado)$/)).toHaveLength(2);
    expect(screen.getByText("R$ 10.000,00").querySelector(".chip")).toBeNull();
  });

  it("T-531: a estimada marca o pagamento do plano, não o habitual que ficou em zero", () => {
    render(
      <TabelaDeDividas
        plano={PLANO}
        entradas={entradas([
          { nome: "Parcela", codigo: "PARCELA_CONTRATUAL", valor: "R$ 0,00" },
          {
            nome: "Pagamento",
            codigo: "PAGAMENTO_MENSAL_EFETIVO",
            valor: "R$ 528,72",
            marca: "estimado",
          },
        ])}
      />,
    );
    expect(
      screen.getByRole("columnheader", { name: "Pagamento do plano" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("R$ 528,72").querySelector(".chip")?.textContent,
    ).toBe("estimado");
    expect(screen.getByText("R$ 0,00").querySelector(".chip")).toBeNull();
  });

  it("sem marca, a célula renderiza como antes", () => {
    render(
      <TabelaDeDividas
        plano={PLANO}
        entradas={entradas([
          {
            nome: "Saldo",
            codigo: "SALDO_DEVEDOR_ATUAL",
            valor: "R$ 10.000,00",
          },
        ])}
      />,
    );
    expect(
      screen.queryByText(/^(calculado|estimado)$/),
    ).not.toBeInTheDocument();
    expect(screen.getByText("R$ 10.000,00")).toBeInTheDocument();
  });
});
