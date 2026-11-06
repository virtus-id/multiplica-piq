// @vitest-environment happy-dom
/**
 * `TelaPergunta` — o ramo `CALCULO_DIVIDA` (`T-513`; `RF-523`, `RF-526`).
 *
 * Confirmar leva ao `proxima` que a API devolve; a casca não ganha um segundo
 * "Continuar" enquanto não há aviso de gravação.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as api from "../../../src/services/api";
import TelaPergunta from "../../../src/telas/TelaPergunta";
import type { Pergunta } from "../../../src/tipos";

afterEach(() => {
  vi.restoreAllMocks();
});

function pergunta(extra: Partial<Pergunta>): Pergunta {
  return {
    CASO_ID: "CASO-1",
    ID: "B5.CALC01",
    bloco: 5,
    tipo: "CALCULO_DIVIDA",
    enunciado: "Vamos conferir os números",
    opcoes: [],
    escopo_repeticao: "DIVIDA_ID",
    item_id: "D001",
    posicao: 1,
    total_na_ficha: 5,
    admite_nao_sei: false,
    valor_atual: null,
    respondida_como_nao_sei: false,
    valores_marcados: [],
    aviso: null,
    sistema: "PRICE",
    ...extra,
  };
}

describe("TelaPergunta — calculadora da dívida", () => {
  it("confirmar leva à pergunta que a API devolve em `proxima`", async () => {
    vi.spyOn(api, "obterProximaPergunta").mockResolvedValue({
      pergunta: pergunta({}),
      total_pendencias: 3,
    } as unknown as Awaited<ReturnType<typeof api.obterProximaPergunta>>);
    vi.spyOn(api, "obterPergunta").mockImplementation(
      async (_caso, id) =>
        ({
          pergunta: pergunta({
            ID: id,
            tipo: "MOEDA",
            enunciado: `Pergunta ${id}`,
          }),
          total_pendencias: 3,
        }) as unknown as Awaited<ReturnType<typeof api.obterPergunta>>,
    );
    vi.spyOn(api, "preverCalculadora").mockResolvedValue({
      estado: "SEM_CALCULO",
      campo_calculado: null,
      valores: {},
      teorico: null,
      alternativas: [],
      resumo: null,
      parcela_estimada: null,
      erros: [],
      mensagem: null,
    });
    vi.spyOn(api, "confirmarCalculadora").mockResolvedValue({
      ID_PERGUNTA: "B5.CALC01",
      proxima: {
        pergunta: pergunta({
          ID: "B5.A02",
          tipo: "SELECAO_UNICA",
          enunciado: "Próxima da ficha",
        }),
        coleta_completa: false,
      },
      avisos: [],
    });
    const user = userEvent.setup();
    render(<TelaPergunta casoId="CASO-1" onColetaCompleta={vi.fn()} />);

    const botoes = await screen.findAllByRole("button", { name: "Continuar" });
    expect(botoes).toHaveLength(1); // só o da calculadora
    await waitFor(() => expect(botoes[0]).toBeEnabled(), { timeout: 3000 });
    await user.click(botoes[0]);
    expect(
      await screen.findByRole("heading", { name: "Próxima da ficha" }),
    ).toBeInTheDocument();
  });
});
