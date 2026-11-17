// @vitest-environment happy-dom
/**
 * `DivergenciaDaDivida` — o popup da divergência (`T-684`; `RF-566`,
 * `RF-567`, `AC-608`, `AC-609`, `AC-611`, `AC-612`, `AC-613`, `EC-100`,
 * `EC-102`, `EC-105`).
 *
 * A API é simulada: cada valor exibido é um texto que o "servidor" mandou. O
 * happy-dom tem `showModal()`/`close()`, mas não a tecla Esc, o foco preso nem
 * o fundo inerte — isso é provado no E2E (`AC-610`, `T-688`).
 */
import { readFileSync } from "node:fs";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import DivergenciaDaDivida, {
  textoDoValor,
} from "../../../src/componentes/DivergenciaDaDivida";
import * as api from "../../../src/services/api";
import type {
  CorpoDaCalculadora,
  RespostaDaPrevia,
  ValorCalculado,
} from "../../../src/tipos";

afterEach(() => {
  vi.restoreAllMocks();
});

const ESPERA = { timeout: 3000 };

const FRASE_RF_519 =
  "Nas condições informadas, essa parcela não reduz o saldo devedor. Revise os dados ou simule outra condição.";

/** Os quatro valores do `AC-534`, como digitados. */
const CORPO: CorpoDaCalculadora = {
  sistema: "PRICE",
  periodicidade: "MENSAL",
  saldo: "10.000,00",
  parcela: "400,00",
  taxa: "2,00",
  prazo: "24",
  recalcular: null,
};

function valor(
  texto: string,
  marca: ValorCalculado["marca"] = "INFORMADO",
): ValorCalculado {
  return {
    texto,
    entrada: texto,
    marca,
    rotulo: marca === "INFORMADO" ? "informado" : "calculado",
  };
}

function previa(extra: Partial<RespostaDaPrevia> = {}): RespostaDaPrevia {
  return {
    estado: "CALCULADO",
    campo_calculado: null,
    valores: {},
    teorico: null,
    alternativas: [],
    resumo: null,
    parcela_estimada: null,
    erros: [],
    mensagem: null,
    ...extra,
  };
}

/** A prévia `INCOMPATIVEL` do `AC-534`. */
const INCOMPATIVEL = previa({
  estado: "INCOMPATIVEL",
  mensagem: "Os quatro valores não são compatíveis.",
  valores: {
    SALDO: valor("R$ 10.000,00"),
    PARCELA: valor("R$ 400,00"),
    TAXA: valor("2,00% a.m."),
    PRAZO: valor("24"),
  },
  teorico: { campo: "PARCELA", texto: "R$ 528,72" },
  alternativas: ["SALDO", "PARCELA", "TAXA", "PRAZO"],
  hipotese_conservadora: {
    saldo: "R$ 13.240,00",
    taxa: "2,00% a.m.",
    marca: "HIPOTESE",
    rotulo: "hipótese",
    aviso: "Aviso do servidor sobre saldo e taxa.",
  },
});

const PARCELA_RECALCULADA = previa({
  campo_calculado: "PARCELA",
  valores: { PARCELA: valor("R$ 528,72", "CALCULADO") },
});

function montar(
  extra: Partial<Parameters<typeof DivergenciaDaDivida>[0]> = {},
) {
  const aoConfirmar = vi.fn();
  const aoVoltar = vi.fn();
  render(
    <DivergenciaDaDivida
      casoId="CASO-1"
      corpo={CORPO}
      previa={INCOMPATIVEL}
      gravando={false}
      erroAoSalvar={null}
      aoConfirmar={aoConfirmar}
      aoVoltar={aoVoltar}
      {...extra}
    />,
  );
  return { aoConfirmar, aoVoltar };
}

const confirmar = () =>
  screen.getByRole("button", { name: "Confirmar e continuar" });

describe("DivergenciaDaDivida", () => {
  it("AC-608: título, frase do valor teórico, opções na ordem com Manter marcada, hipótese conservadora e os dois botões", () => {
    const prever = vi.spyOn(api, "preverCalculadora");
    montar();
    const dialog = screen.getByRole("dialog", {
      name: "Os valores desta dívida não batem",
    });
    expect(dialog).toHaveAttribute("open");
    expect(
      screen.getByText(
        "Com esse saldo, taxa e prazo, a parcela seria R$ 528,72. Você informou R$ 400,00.",
      ),
    ).toBeInTheDocument();
    const radios = screen.getAllByRole("radio");
    expect(radios.map((r) => r.closest("label")?.textContent)).toEqual([
      "Manter os valores que informei",
      "Recalcular o saldo",
      "Recalcular a parcela",
      "Recalcular a taxa",
      "Recalcular o prazo",
    ]);
    expect(radios[0]).toBeChecked();
    expect(
      screen.getByText("Saldo: R$ 13.240,00 · Taxa: 2,00% a.m. (hipótese)"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Aviso do servidor sobre saldo e taxa."),
    ).toBeInTheDocument();
    expect(confirmar()).toBeEnabled();
    expect(
      screen.getByRole("button", { name: "Voltar e corrigir" }),
    ).toBeInTheDocument();
    // NFR Performance: abrir não chama o servidor.
    expect(prever).not.toHaveBeenCalled();
  });

  it("AC-608: sem hipótese conservadora na prévia, o bloco não existe", () => {
    montar({ previa: { ...INCOMPATIVEL, hipotese_conservadora: null } });
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.queryByText(/hipótese/)).not.toBeInTheDocument();
    expect(
      screen.queryByText("Aviso do servidor sobre saldo e taxa."),
    ).not.toBeInTheDocument();
  });

  it("AC-609: Confirmar com Manter entrega null e nunca chama o servidor", async () => {
    const prever = vi.spyOn(api, "preverCalculadora");
    const user = userEvent.setup();
    const { aoConfirmar, aoVoltar } = montar();
    await user.click(confirmar());
    expect(aoConfirmar).toHaveBeenCalledWith(null);
    expect(aoVoltar).not.toHaveBeenCalled();
    expect(prever).not.toHaveBeenCalled();
  });

  it("AC-612: Recalcular a parcela pede a prévia com o recálculo, mostra o valor e confirma PARCELA", async () => {
    const prever = vi
      .spyOn(api, "preverCalculadora")
      .mockResolvedValue(PARCELA_RECALCULADA);
    const user = userEvent.setup();
    const { aoConfirmar } = montar();
    await user.click(screen.getByRole("radio", { name: "Recalcular a parcela" }));
    expect(prever).toHaveBeenCalledWith(
      "CASO-1",
      { ...CORPO, recalcular: "PARCELA" },
      expect.any(AbortSignal),
    );
    expect(
      await screen.findByText(
        "Parcela recalculada: R$ 528,72 (calculado)",
        {},
        ESPERA,
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Parcela recalculada: R$ 528,72 (calculado)",
    );
    await waitFor(() => expect(confirmar()).toBeEnabled());
    await user.click(confirmar());
    expect(aoConfirmar).toHaveBeenCalledWith("PARCELA");
  });

  it("AC-613, EC-102: taxa sem solução mostra a frase exata e bloqueia; trocar para parcela apaga a frase e libera", async () => {
    vi.spyOn(api, "preverCalculadora").mockImplementation(
      async (_caso, corpo) =>
        corpo.recalcular === "TAXA"
          ? previa({ estado: "ERRO", mensagem: FRASE_RF_519 })
          : PARCELA_RECALCULADA,
    );
    const user = userEvent.setup();
    montar();
    await user.click(screen.getByRole("radio", { name: "Recalcular a taxa" }));
    expect(await screen.findByRole("alert", {}, ESPERA)).toHaveTextContent(
      FRASE_RF_519,
    );
    expect(screen.getByRole("alert").textContent).toBe(FRASE_RF_519);
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
    expect(confirmar()).toBeDisabled();

    await user.click(screen.getByRole("radio", { name: "Recalcular a parcela" }));
    expect(screen.queryByText(FRASE_RF_519)).not.toBeInTheDocument();
    expect(
      await screen.findByText(
        "Parcela recalculada: R$ 528,72 (calculado)",
        {},
        ESPERA,
      ),
    ).toBeInTheDocument();
    expect(confirmar()).toBeEnabled();
  });

  it("RF-567: confirmar fica desabilitado com a resposta pendente e depois de falha de rede", async () => {
    let rejeitar: (erro: unknown) => void = () => {};
    vi.spyOn(api, "preverCalculadora").mockImplementation(
      () =>
        new Promise<RespostaDaPrevia>((_resolver, rejeitarAgora) => {
          rejeitar = rejeitarAgora;
        }),
    );
    const user = userEvent.setup();
    montar();
    await user.click(screen.getByRole("radio", { name: "Recalcular a parcela" }));
    expect(confirmar()).toBeDisabled();
    rejeitar(new TypeError("Failed to fetch"));
    expect(await screen.findByRole("alert", {}, ESPERA)).toHaveTextContent(
      "Não foi possível calcular.",
    );
    expect(confirmar()).toBeDisabled();
    // "Manter" continua confirmável.
    await user.click(
      screen.getByRole("radio", { name: "Manter os valores que informei" }),
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(confirmar()).toBeEnabled();
  });

  it("RF-567: trocar de opção aborta o pedido anterior e a resposta atrasada não aparece", async () => {
    const sinais: AbortSignal[] = [];
    let resolverPrimeira: (r: RespostaDaPrevia) => void = () => {};
    vi.spyOn(api, "preverCalculadora").mockImplementation(
      (_caso, _corpo, sinal) => {
        if (sinal) sinais.push(sinal);
        if (sinais.length === 1)
          return new Promise<RespostaDaPrevia>((resolver) => {
            resolverPrimeira = resolver;
          });
        return Promise.resolve(
          previa({
            campo_calculado: "PRAZO",
            valores: { PRAZO: valor("36", "CALCULADO") },
          }),
        );
      },
    );
    const user = userEvent.setup();
    montar();
    await user.click(screen.getByRole("radio", { name: "Recalcular a parcela" }));
    await user.click(screen.getByRole("radio", { name: "Recalcular o prazo" }));
    expect(sinais).toHaveLength(2);
    expect(sinais[0].aborted).toBe(true);
    expect(
      await screen.findByText("Prazo recalculado: 36 meses (calculado)", {}, ESPERA),
    ).toBeInTheDocument();
    resolverPrimeira(PARCELA_RECALCULADA);
    await Promise.resolve();
    expect(screen.queryByText(/Parcela recalculada/)).not.toBeInTheDocument();
    expect(
      screen.getByText("Prazo recalculado: 36 meses (calculado)"),
    ).toBeInTheDocument();
  });

  it("AC-611, EC-100: Voltar e corrigir chama aoVoltar, nunca aoConfirmar", async () => {
    const user = userEvent.setup();
    const { aoConfirmar, aoVoltar } = montar();
    await user.click(screen.getByRole("button", { name: "Voltar e corrigir" }));
    expect(aoVoltar).toHaveBeenCalledTimes(1);
    expect(aoConfirmar).not.toHaveBeenCalled();
  });

  it("AC-611, EC-100: o close do navegador (Esc) chama aoVoltar", () => {
    const { aoConfirmar, aoVoltar } = montar();
    fireEvent(screen.getByRole("dialog"), new Event("close"));
    expect(aoVoltar).toHaveBeenCalledTimes(1);
    expect(aoConfirmar).not.toHaveBeenCalled();
  });

  it("EC-105: o erro ao salvar aparece dentro do dialog, em role=alert", () => {
    montar({ erroAoSalvar: "Não foi possível salvar." });
    const alerta = screen.getByRole("alert");
    expect(alerta).toHaveTextContent("Não foi possível salvar.");
    expect(screen.getByRole("dialog")).toContainElement(alerta);
  });

  it("gravando: o botão diz Salvando… e fica desabilitado", () => {
    montar({ gravando: true });
    expect(screen.getByRole("button", { name: "Salvando…" })).toBeDisabled();
  });

  it("PD-25: textoDoValor só acrescenta ' meses' ao prazo", () => {
    expect(textoDoValor("PRAZO", "24")).toBe("24 meses");
    expect(textoDoValor("PARCELA", "R$ 528,72")).toBe("R$ 528,72");
    expect(textoDoValor("TAXA", "2,00% a.m.")).toBe("2,00% a.m.");
    expect(textoDoValor("SALDO", "R$ 10.000,00")).toBe("R$ 10.000,00");
  });

  it("Lei nº 3: o componente não faz conta nem formata valor financeiro", () => {
    const fonte = readFileSync(
      "src/componentes/DivergenciaDaDivida.tsx",
      "utf-8",
    );
    expect(fonte).not.toMatch(
      /parseFloat|parseInt|Number\(|Math\.|toFixed|toLocaleString|Intl\./,
    );
  });
});
