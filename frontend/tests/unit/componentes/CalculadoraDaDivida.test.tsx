// @vitest-environment happy-dom
/**
 * `CalculadoraDaDivida` — prévia, erro, incompatibilidade e confirmação
 * (`T-515`; `RF-519`, `RF-525`, `RF-526`, `AC-529`, `AC-536`, `AC-541`).
 *
 * O componente só mostra o que o servidor devolve: aqui a API é simulada e
 * cada valor exibido é um texto que o "servidor" mandou.
 */
import { readFileSync } from "node:fs";

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import CalculadoraDaDivida from "../../../src/componentes/CalculadoraDaDivida";
import * as api from "../../../src/services/api";
import type {
  CorpoDaCalculadora,
  Pergunta,
  RespostaDaPrevia,
  ValorCalculado,
} from "../../../src/tipos";

afterEach(() => {
  vi.restoreAllMocks();
});

const ESPERA = { timeout: 3000 };

function pergunta(extra: Partial<Pergunta> = {}): Pergunta {
  return {
    CASO_ID: "CASO-1",
    ID: "B5.CALC01",
    bloco: 5,
    tipo: "CALCULO_DIVIDA",
    enunciado: "Vamos conferir os números desta dívida",
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

/** O que o servidor devolve para cada pergunta individual lida ao abrir. */
function gravado(extras: Record<string, Partial<Pergunta>> = {}) {
  const base: Record<string, Partial<Pergunta>> = {
    "B5.B03": { enunciado: "Saldo devedor da dívida?" },
    "B5.C02": { enunciado: "Parcela da dívida?" },
    "B5.C02B": { enunciado: "Meses restantes?" },
    "B5.D06": {
      enunciado: "CET ou taxa de juros?",
      opcoes: [
        { rotulo: "ao mês", valor_interno: "MENSAL", admite_nao_sei: false },
        { rotulo: "ao ano", valor_interno: "ANUAL", admite_nao_sei: false },
      ],
    },
    "B5.C02A": {
      enunciado: "Price ou SAC?",
      opcoes: [
        {
          rotulo: "Price (parcelas fixas)",
          valor_interno: "PRICE",
          admite_nao_sei: false,
        },
        {
          rotulo: "SAC (parcelas que diminuem)",
          valor_interno: "SAC",
          admite_nao_sei: false,
        },
      ],
    },
  };
  for (const [id, extra] of Object.entries(extras))
    base[id] = { ...base[id], ...extra };
  return vi.spyOn(api, "obterPergunta").mockImplementation(
    async (_caso, id) =>
      ({
        pergunta: pergunta({ ID: id, tipo: "MOEDA", ...base[id] }),
        total_pendencias: 0,
      }) as unknown as Awaited<ReturnType<typeof api.obterPergunta>>,
  );
}

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

function montar(aoConfirmar = vi.fn(), aoEditar = vi.fn()) {
  render(
    <CalculadoraDaDivida
      casoId="CASO-1"
      pergunta={pergunta()}
      aoConfirmar={aoConfirmar}
      aoEditar={aoEditar}
    />,
  );
  return { aoConfirmar, aoEditar };
}

describe("CalculadoraDaDivida", () => {
  it("abre com o que foi gravado: 'não sei' vira campo vazio marcado e SAC continua SAC", async () => {
    gravado({
      "B5.B03": { valor_atual: "10000.00" },
      "B5.C02B": { valor_atual: "NAO_SEI", respondida_como_nao_sei: true },
      "B5.D06": { valor_atual: "ANUAL", valor_do_campo: "0.12" },
      "B5.C02A": { valor_atual: "SAC" },
    });
    const prever = vi
      .spyOn(api, "preverCalculadora")
      .mockResolvedValue(previa());
    montar();
    expect(
      await screen.findByLabelText("Saldo devedor da dívida?"),
    ).toHaveValue("10.000,00");
    expect(screen.getByLabelText("Meses restantes?")).toHaveValue("");
    expect(
      screen.getByRole("radio", { name: "SAC (parcelas que diminuem)" }),
    ).toBeChecked();
    expect(screen.getByRole("radio", { name: "ao ano" })).toBeChecked();
    await waitFor(() => expect(prever).toHaveBeenCalled(), ESPERA);
    expect(prever.mock.calls[0][1]).toEqual<CorpoDaCalculadora>({
      sistema: "SAC",
      periodicidade: "ANUAL",
      saldo: "10.000,00",
      parcela: null,
      taxa: "12",
      prazo: null,
      recalcular: null,
    });
  });

  it("AC-529: o 24 antigo some na hora da edição e não volta quando a troca gera erro", async () => {
    gravado();
    const prever = vi
      .spyOn(api, "preverCalculadora")
      .mockResolvedValueOnce(
        previa({
          campo_calculado: "PRAZO",
          valores: { PRAZO: valor("24", "CALCULADO") },
          resumo: {
            prazo: 24,
            primeira_parcela: "R$ 528,72",
            ultimo_pagamento: "R$ 528,72",
            total_de_juros: "R$ 2.689,28",
          },
        }),
      )
      .mockResolvedValueOnce(
        previa({
          estado: "ERRO",
          mensagem:
            "Nas condições informadas, essa parcela não reduz o saldo devedor.",
        }),
      );
    const user = userEvent.setup();
    montar();
    expect(
      (await screen.findAllByText("24", {}, ESPERA)).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("R$ 2.689,28")).toBeInTheDocument();

    await user.click(
      screen.getByRole("radio", { name: "SAC (parcelas que diminuem)" }),
    );
    // Imediatamente, antes de qualquer resposta: nada do cálculo anterior.
    expect(screen.queryAllByText("24")).toHaveLength(0);
    expect(screen.queryByText("R$ 2.689,28")).not.toBeInTheDocument();

    const alerta = await screen.findByRole("alert", {}, ESPERA);
    expect(alerta).toHaveTextContent("não reduz o saldo devedor");
    expect(screen.queryAllByText("24")).toHaveLength(0);
    expect(prever).toHaveBeenCalledTimes(2);
  });

  it("cancela a requisição anterior e descarta resposta fora de ordem", async () => {
    gravado();
    const sinais: AbortSignal[] = [];
    let resolverPrimeira: (r: RespostaDaPrevia) => void = () => {};
    vi.spyOn(api, "preverCalculadora").mockImplementation(
      (_caso, _corpo, sinal) => {
        if (sinal) sinais.push(sinal);
        if (sinais.length === 1) {
          return new Promise<RespostaDaPrevia>((resolver) => {
            resolverPrimeira = resolver;
          });
        }
        return Promise.resolve(
          previa({ valores: { SALDO: valor("R$ 2,00") } }),
        );
      },
    );
    const user = userEvent.setup();
    montar();
    await waitFor(() => expect(sinais).toHaveLength(1), ESPERA);
    await user.type(screen.getByLabelText("Saldo devedor da dívida?"), "5");
    await waitFor(() => expect(sinais).toHaveLength(2), ESPERA);
    expect(sinais[0].aborted).toBe(true);
    expect(await screen.findByText("R$ 2,00", {}, ESPERA)).toBeInTheDocument();
    // A primeira responde tarde: não pode sobrescrever a segunda.
    resolverPrimeira(previa({ valores: { SALDO: valor("R$ 1,00") } }));
    await Promise.resolve();
    expect(screen.queryByText("R$ 1,00")).not.toBeInTheDocument();
    expect(screen.getByText("R$ 2,00")).toBeInTheDocument();
  });

  it("'não sei' vai como null e o digitado vai como digitado (RF-526)", async () => {
    gravado();
    const prever = vi
      .spyOn(api, "preverCalculadora")
      .mockResolvedValue(previa());
    const user = userEvent.setup();
    montar();
    await user.type(
      await screen.findByLabelText("Saldo devedor da dívida?"),
      "1000000",
    );
    await user.click(screen.getByRole("checkbox", { name: /Não sei.*Taxa/ }));
    await waitFor(() => {
      const ultimo = prever.mock.calls.at(-1)?.[1];
      expect(ultimo).toMatchObject({
        saldo: "10.000,00",
        taxa: null,
        recalcular: null,
      });
    }, ESPERA);
  });

  it("incompatibilidade em texto e escolha por teclado: escolher parcela mostra o valor calculado", async () => {
    gravado();
    const prever = vi
      .spyOn(api, "preverCalculadora")
      .mockResolvedValueOnce(
        previa({
          estado: "INCOMPATIVEL",
          mensagem: "Os quatro valores não são compatíveis.",
          valores: { PARCELA: valor("R$ 500,00") },
          teorico: { campo: "PARCELA", texto: "R$ 528,72" },
          alternativas: ["SALDO", "PARCELA", "TAXA", "PRAZO"],
        }),
      )
      .mockResolvedValueOnce(
        previa({
          campo_calculado: "PARCELA",
          valores: { PARCELA: valor("R$ 528,72", "CALCULADO") },
        }),
      );
    const user = userEvent.setup();
    montar();
    expect(
      await screen.findByText(/Valores incompatíveis/, {}, ESPERA),
    ).toBeInTheDocument();
    expect(screen.getByText("R$ 528,72")).toBeInTheDocument();
    expect(screen.getByText("R$ 500,00")).toBeInTheDocument();
    // Sem escolha: os originais permanecem e "manter" está marcado.
    expect(
      screen.getByRole("radio", { name: /Manter os valores/ }),
    ).toBeChecked();

    const parcela = screen.getByRole("radio", { name: "Parcela" });
    parcela.focus();
    await user.keyboard(" ");
    expect(parcela).toBeChecked();
    await waitFor(
      () => expect(prever.mock.calls.at(-1)?.[1].recalcular).toBe("PARCELA"),
      ESPERA,
    );
    expect(
      await screen.findByText("calculado", {}, ESPERA),
    ).toBeInTheDocument();
    expect(screen.getByText("R$ 528,72")).toBeInTheDocument();
    // A escolha segue disponível para mudar de ideia.
    expect(
      screen.getByRole("radio", { name: /Manter os valores/ }),
    ).toBeInTheDocument();
  });

  it("erro de campo: aria-invalid e mensagem em role=alert", async () => {
    gravado();
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(
      previa({
        estado: "ERRO",
        erros: [
          {
            campo: "PRAZO",
            codigo: "PRAZO_NAO_INTEIRO",
            mensagem: "Use meses inteiros.",
          },
        ],
      }),
    );
    montar();
    expect(await screen.findByRole("alert", {}, ESPERA)).toHaveTextContent(
      "Use meses inteiros.",
    );
    expect(screen.getByLabelText("Meses restantes?")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("falha de rede apaga o resultado e mostra a mensagem do servidor", async () => {
    gravado();
    vi.spyOn(api, "preverCalculadora").mockRejectedValue(
      new api.ErroHttp(503, "Não foi possível calcular."),
    );
    montar();
    expect(await screen.findByRole("alert", {}, ESPERA)).toHaveTextContent(
      "Não foi possível calcular.",
    );
  });

  it("confirmar envia o mesmo corpo e entrega a confirmação; 422 mostra o erro e não avança", async () => {
    gravado();
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(previa());
    const confirmar = vi
      .spyOn(api, "confirmarCalculadora")
      .mockRejectedValueOnce(new api.ErroHttp(422, "Taxa acima do limite."))
      .mockResolvedValueOnce({
        ID_PERGUNTA: "B5.CALC01",
        proxima: { pergunta: null, coleta_completa: false },
        avisos: [],
      });
    const user = userEvent.setup();
    const { aoConfirmar } = montar();
    const botao = await screen.findByRole("button", { name: "Continuar" });
    await waitFor(() => expect(botao).toBeEnabled(), ESPERA);
    await user.click(botao);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Taxa acima do limite.",
    );
    expect(aoConfirmar).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await waitFor(() => expect(aoConfirmar).toHaveBeenCalledTimes(1));
    expect(confirmar).toHaveBeenCalledWith(
      "CASO-1",
      "D001",
      expect.objectContaining({ sistema: "PRICE" }),
    );
  });

  it("Lei nº 3: o componente não faz conta nem formata valor financeiro", () => {
    const fonte = readFileSync(
      "src/componentes/CalculadoraDaDivida.tsx",
      "utf-8",
    );
    expect(fonte).not.toMatch(
      /parseFloat|parseInt|Number\(|Math\.|toFixed|toLocaleString|Intl\./,
    );
  });

  it("T-531: a parcela estimada aparece em linha à parte, marcada, e nunca no campo digitado", async () => {
    gravado();
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(
      previa({
        estado: "PENDENTE",
        parcela_estimada: {
          texto: "R$ 528,72",
          marca: "ESTIMADO",
          rotulo: "estimado",
          hipotese: "Hipótese de teste.",
        },
      }),
    );
    montar();
    const linha = await screen.findByTestId(
      "parcela-estimada",
      undefined,
      ESPERA,
    );
    expect(linha).toHaveTextContent("R$ 528,72");
    expect(linha).toHaveTextContent("estimado");
    expect(linha).toHaveTextContent("Hipótese de teste.");
    expect(screen.getByLabelText("Parcela da dívida?")).toHaveValue("");
  });

  it("T-531: sem estimativa (prazo ou pagamento informado) a linha não existe", async () => {
    gravado();
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(
      previa({ estado: "PENDENTE" }),
    );
    montar();
    await screen.findByLabelText("Saldo devedor da dívida?");
    await waitFor(
      () => expect(screen.queryByText(/calculando/i)).not.toBeInTheDocument(),
      ESPERA,
    );
    expect(screen.queryByTestId("parcela-estimada")).not.toBeInTheDocument();
  });
  it("AC-553: a hipótese conservadora mostra saldo, taxa, marca e aviso do servidor, e some sem hipótese", async () => {
    gravado();
    vi.spyOn(api, "preverCalculadora")
      .mockResolvedValueOnce(
        previa({
          estado: "INCOMPATIVEL",
          mensagem: "Os quatro valores não são compatíveis.",
          valores: { PARCELA: valor("R$ 700,00") },
          teorico: { campo: "PARCELA", texto: "R$ 528,72" },
          alternativas: ["SALDO", "PARCELA", "TAXA", "PRAZO"],
          hipotese_conservadora: {
            saldo: "R$ 13.240,00",
            taxa: "2,00%",
            marca: "HIPOTESE",
            rotulo: "hipótese",
            aviso: "Aviso do servidor sobre saldo e taxa.",
          },
        }),
      )
      .mockResolvedValue(
        previa({
          campo_calculado: "PARCELA",
          valores: { PARCELA: valor("R$ 528,72", "CALCULADO") },
        }),
      );
    const user = userEvent.setup();
    montar();

    const bloco = await screen.findByTestId(
      "hipotese-conservadora",
      undefined,
      ESPERA,
    );
    expect(bloco).toHaveTextContent("R$ 13.240,00");
    expect(bloco).toHaveTextContent("2,00%");
    expect(bloco).toHaveTextContent("hipótese");
    expect(bloco).toHaveTextContent("Aviso do servidor sobre saldo e taxa.");
    // RF-539: parcela e prazo da hipótese não governam o plano, então o bloco não os traz
    expect(bloco).not.toHaveTextContent("R$ 700,00");
    expect(bloco).not.toHaveTextContent("R$ 528,72");

    // RF-525: escolher recalcular a parcela encerra o cenário (o servidor deixa de devolvê-lo)
    await user.click(screen.getByRole("radio", { name: "Parcela" }));
    await waitFor(
      () =>
        expect(
          screen.queryByTestId("hipotese-conservadora"),
        ).not.toBeInTheDocument(),
      ESPERA,
    );
  });

  it("AC-553: sem hipótese na resposta o bloco não existe", async () => {
    gravado();
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(
      previa({
        estado: "INCOMPATIVEL",
        mensagem: "Os quatro valores não são compatíveis.",
        valores: { PARCELA: valor("R$ 500,00") },
        teorico: { campo: "PARCELA", texto: "R$ 528,72" },
        alternativas: ["SALDO", "PARCELA", "TAXA", "PRAZO"],
        hipotese_conservadora: null,
      }),
    );
    montar();
    await screen.findByText(/Valores incompatíveis/, {}, ESPERA);
    expect(
      screen.queryByTestId("hipotese-conservadora"),
    ).not.toBeInTheDocument();
  });
});
