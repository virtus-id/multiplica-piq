// @vitest-environment happy-dom
/**
 * `CalculadoraDaDivida` — prévia, erro, linha marcada, popup da divergência e
 * confirmação (`T-515`, `T-687`; `RF-519`, `RF-526`, `RF-564` a `RF-568`).
 *
 * O componente só mostra o que o servidor devolve: aqui a API é simulada e
 * cada valor exibido é um texto que o "servidor" mandou.
 */
import { readFileSync } from "node:fs";

import { render, screen, waitFor, within } from "@testing-library/react";
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

const FRASE_RF_519 =
  "Nas condições informadas, essa parcela não reduz o saldo devedor. Revise os dados ou simule outra condição.";

/** O `AC-534` gravado: saldo R$ 10.000,00, parcela R$ 400,00, 2% ao mês, 24 meses. */
const AC_534 = {
  "B5.B03": { valor_atual: "10000.00" },
  "B5.C02": { valor_atual: "400.00" },
  "B5.C02B": { valor_atual: "24" },
  "B5.D06": { valor_atual: "MENSAL", valor_do_campo: "0.02" },
};

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

const CONFIRMACAO = {
  ID_PERGUNTA: "B5.CALC01",
  proxima: { pergunta: null, coleta_completa: false },
  avisos: [],
};

const TITULO = "Os valores desta dívida não batem";

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
  /** Espera a prévia chegar: "Continuar" só habilita com ela. */
  async function continuarHabilitado() {
    const botao = await screen.findByRole("button", { name: "Continuar" });
    await waitFor(() => expect(botao).toBeEnabled(), ESPERA);
    return botao;
  }

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

  it("AC-616, AC-529: 'Calculado: 24 meses' some na hora da edição (SAC, ao ano, parcela) e não volta com o erro", async () => {
    gravado({
      "B5.B03": { valor_atual: "10000.00" },
      "B5.C02": { valor_atual: "528.72" },
      "B5.C02B": { valor_atual: "NAO_SEI", respondida_como_nao_sei: true },
      "B5.D06": { valor_atual: "MENSAL", valor_do_campo: "0.02" },
    });
    const prever = vi
      .spyOn(api, "preverCalculadora")
      .mockImplementation(async (_caso, corpo) =>
        corpo.parcela === "200,00"
          ? previa({ estado: "ERRO", mensagem: FRASE_RF_519 })
          : previa({
              campo_calculado: "PRAZO",
              valores: { PRAZO: valor("24", "CALCULADO") },
            }),
      );
    const user = userEvent.setup();
    const linha = "Calculado: 24 meses";
    montar();
    expect(await screen.findByText(linha, {}, ESPERA)).toBeInTheDocument();

    await user.click(
      screen.getByRole("radio", { name: "SAC (parcelas que diminuem)" }),
    );
    // Imediatamente, antes de qualquer resposta: nada do cálculo anterior.
    expect(screen.queryByText(linha)).not.toBeInTheDocument();
    expect(await screen.findByText(linha, {}, ESPERA)).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "ao ano" }));
    expect(screen.queryByText(linha)).not.toBeInTheDocument();
    expect(await screen.findByText(linha, {}, ESPERA)).toBeInTheDocument();

    const parcela = screen.getByLabelText("Parcela da dívida?");
    await user.clear(parcela);
    expect(screen.queryByText(linha)).not.toBeInTheDocument();
    await user.type(parcela, "20000");
    const alerta = await screen.findByRole("alert", {}, ESPERA);
    expect(alerta).toHaveTextContent(FRASE_RF_519);
    expect(screen.queryByText(linha)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();
    expect(prever.mock.calls.at(-1)?.[1]).toMatchObject({ parcela: "200,00" });
  });

  it("cancela a requisição anterior e descarta resposta fora de ordem (linha 'Calculado: …')", async () => {
    gravado();
    const sinais: AbortSignal[] = [];
    let resolverPrimeira: (r: RespostaDaPrevia) => void = () => {};
    const prazo = (texto: string) =>
      previa({
        campo_calculado: "PRAZO",
        valores: { PRAZO: valor(texto, "CALCULADO") },
      });
    vi.spyOn(api, "preverCalculadora").mockImplementation(
      (_caso, _corpo, sinal) => {
        if (sinal) sinais.push(sinal);
        if (sinais.length === 1) {
          return new Promise<RespostaDaPrevia>((resolver) => {
            resolverPrimeira = resolver;
          });
        }
        return Promise.resolve(prazo("24"));
      },
    );
    const user = userEvent.setup();
    montar();
    await waitFor(() => expect(sinais).toHaveLength(1), ESPERA);
    await user.type(screen.getByLabelText("Saldo devedor da dívida?"), "5");
    await waitFor(() => expect(sinais).toHaveLength(2), ESPERA);
    expect(sinais[0].aborted).toBe(true);
    expect(
      await screen.findByText("Calculado: 24 meses", {}, ESPERA),
    ).toBeInTheDocument();
    // A primeira responde tarde: não pode sobrescrever a segunda.
    resolverPrimeira(prazo("36"));
    await Promise.resolve();
    expect(screen.queryByText("Calculado: 36 meses")).not.toBeInTheDocument();
    expect(screen.getByText("Calculado: 24 meses")).toBeInTheDocument();
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

  it("AC-603: CONFERIDO não desenha valores, mensagem, resumo nem marca; Continuar salva sem popup", async () => {
    gravado(AC_534);
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(
      previa({
        estado: "CONFERIDO",
        mensagem: "Os quatro valores são compatíveis entre si.",
        valores: {
          SALDO: valor("R$ 10.000,00"),
          PARCELA: valor("R$ 528,71"),
          TAXA: valor("2,00% a.m."),
          PRAZO: valor("24"),
        },
        resumo: {
          prazo: 24,
          primeira_parcela: "R$ 528,71",
          ultimo_pagamento: "R$ 528,71",
          total_de_juros: "R$ 2.689,04",
        },
      }),
    );
    const confirmar = vi
      .spyOn(api, "confirmarCalculadora")
      .mockResolvedValue(CONFIRMACAO);
    const user = userEvent.setup();
    const { aoConfirmar } = montar();
    const botao = await continuarHabilitado();
    for (const texto of [
      "Os quatro valores são compatíveis entre si.",
      "Resumo do cálculo",
      "R$ 10.000,00",
      "R$ 528,71",
      "2,00% a.m.",
      "R$ 2.689,04",
      "informado",
    ])
      expect(screen.queryByText(texto, { exact: false })).not.toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    await user.click(botao);
    await waitFor(() => expect(aoConfirmar).toHaveBeenCalledTimes(1));
    expect(confirmar.mock.calls[0][2]).toMatchObject({ recalcular: null });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("AC-604, AC-606: INCOMPATIVEL não desenha nada na página; Continuar abre o popup e não salva", async () => {
    gravado(AC_534);
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(INCOMPATIVEL);
    const confirmar = vi.spyOn(api, "confirmarCalculadora");
    const user = userEvent.setup();
    montar();
    const botao = await continuarHabilitado();
    for (const texto of [
      "Valores incompatíveis",
      "Qual informação recalcular?",
      "Manter os valores que informei",
      "R$ 13.240,00",
      "Aviso do servidor sobre saldo e taxa.",
      "R$ 528,72",
    ])
      expect(screen.queryByText(texto, { exact: false })).not.toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: /Recalcular/ })).toBeNull();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(botao);
    expect(screen.getByRole("dialog", { name: TITULO })).toBeInTheDocument();
    expect(confirmar).not.toHaveBeenCalled();
  });

  it.each([
    [
      "frase do RF-519",
      previa({ estado: "ERRO", mensagem: FRASE_RF_519 }),
      FRASE_RF_519,
    ],
    [
      "saldo zero",
      previa({
        estado: "ERRO",
        erros: [
          {
            campo: "SALDO",
            codigo: "SALDO_NAO_POSITIVO",
            mensagem: "O saldo devedor precisa ser maior que zero.",
          },
        ],
      }),
      "O saldo devedor precisa ser maior que zero.",
    ],
  ])(
    "AC-605: %s aparece em role=alert e Continuar fica desabilitado",
    async (_nome, resposta, mensagem) => {
      gravado();
      const prever = vi
        .spyOn(api, "preverCalculadora")
        .mockResolvedValue(resposta);
      montar();
      expect(await screen.findByRole("alert", {}, ESPERA)).toHaveTextContent(
        mensagem,
      );
      expect(prever).toHaveBeenCalled();
      expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();
    },
  );

  it.each(["CALCULADO", "PENDENTE", "SEM_CALCULO"] as const)(
    "AC-607: %s salva direto, com recalcular null, sem popup",
    async (estado) => {
      gravado();
      vi.spyOn(api, "preverCalculadora").mockResolvedValue(previa({ estado }));
      const confirmar = vi
        .spyOn(api, "confirmarCalculadora")
        .mockResolvedValue(CONFIRMACAO);
      const user = userEvent.setup();
      const { aoConfirmar } = montar();
      await user.click(await continuarHabilitado());
      await waitFor(() => expect(aoConfirmar).toHaveBeenCalledTimes(1));
      expect(confirmar.mock.calls[0][2]).toMatchObject({ recalcular: null });
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    },
  );

  it("AC-609: Manter + Confirmar e continuar salva os quatro como digitados, avança e fecha o popup", async () => {
    gravado(AC_534);
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(INCOMPATIVEL);
    const confirmar = vi
      .spyOn(api, "confirmarCalculadora")
      .mockResolvedValue(CONFIRMACAO);
    const user = userEvent.setup();
    const { aoConfirmar } = montar();
    await user.click(await continuarHabilitado());
    const dialog = screen.getByRole("dialog", { name: TITULO });
    expect(
      within(dialog).getByRole("radio", {
        name: "Manter os valores que informei",
      }),
    ).toBeChecked();
    await user.click(
      within(dialog).getByRole("button", { name: "Confirmar e continuar" }),
    );
    await waitFor(() => expect(aoConfirmar).toHaveBeenCalledTimes(1));
    expect(confirmar).toHaveBeenCalledWith("CASO-1", "D001", {
      sistema: "PRICE",
      periodicidade: "MENSAL",
      saldo: "10.000,00",
      parcela: "400,00",
      taxa: "2",
      prazo: "24",
      recalcular: null,
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("AC-611, EC-100, EC-104: Voltar não grava, deixa os campos e foca o saldo; reabre com Manter; valores novos compatíveis salvam sem popup", async () => {
    gravado(AC_534);
    vi.spyOn(api, "preverCalculadora").mockImplementation(
      async (_caso, corpo) =>
        corpo.recalcular === "PARCELA"
          ? PARCELA_RECALCULADA
          : corpo.parcela === "528,71"
            ? previa({ estado: "CONFERIDO" })
            : INCOMPATIVEL,
    );
    const confirmar = vi
      .spyOn(api, "confirmarCalculadora")
      .mockResolvedValue(CONFIRMACAO);
    const user = userEvent.setup();
    const { aoConfirmar } = montar();
    await user.click(await continuarHabilitado());
    await user.click(screen.getByRole("radio", { name: "Recalcular a parcela" }));
    expect(
      screen.getByRole("radio", { name: "Recalcular a parcela" }),
    ).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Voltar e corrigir" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(confirmar).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Saldo devedor da dívida?")).toHaveValue(
      "10.000,00",
    );
    expect(screen.getByLabelText("Parcela da dívida?")).toHaveValue("400,00");
    expect(document.activeElement?.id).toBe("calculadora-SALDO");

    // Sem editar nada, o popup reabre do zero: a opção anterior foi descartada.
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    expect(
      screen.getByRole("radio", { name: "Manter os valores que informei" }),
    ).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Voltar e corrigir" }));

    // EC-104: valores novos são avaliados do zero.
    const parcela = screen.getByLabelText("Parcela da dívida?");
    await user.clear(parcela);
    await user.type(parcela, "52871");
    await waitFor(
      () =>
        expect(
          screen.getByRole("button", { name: "Continuar" }),
        ).toBeEnabled(),
      ESPERA,
    );
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await waitFor(() => expect(aoConfirmar).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(confirmar.mock.calls[0][2]).toMatchObject({
      parcela: "528,71",
      recalcular: null,
    });
  });

  it("AC-612: recalcular a parcela no popup salva com recalcular PARCELA", async () => {
    gravado(AC_534);
    vi.spyOn(api, "preverCalculadora").mockImplementation(
      async (_caso, corpo) =>
        corpo.recalcular === "PARCELA" ? PARCELA_RECALCULADA : INCOMPATIVEL,
    );
    const confirmar = vi
      .spyOn(api, "confirmarCalculadora")
      .mockResolvedValue(CONFIRMACAO);
    const user = userEvent.setup();
    const { aoConfirmar } = montar();
    await user.click(await continuarHabilitado());
    await user.click(screen.getByRole("radio", { name: "Recalcular a parcela" }));
    expect(
      await screen.findByText(
        "Parcela recalculada: R$ 528,72 (calculado)",
        {},
        ESPERA,
      ),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Confirmar e continuar" }),
    );
    await waitFor(() => expect(aoConfirmar).toHaveBeenCalledTimes(1));
    expect(confirmar.mock.calls[0][2]).toMatchObject({
      saldo: "10.000,00",
      parcela: "400,00",
      recalcular: "PARCELA",
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("AC-612, EC-101: ficha reaberta com a parcela recalculada mostra a linha e salva sem popup", async () => {
    gravado({
      ...AC_534,
      "B5.C02": { valor_atual: "NAO_SEI", respondida_como_nao_sei: true },
    });
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(PARCELA_RECALCULADA);
    const confirmar = vi
      .spyOn(api, "confirmarCalculadora")
      .mockResolvedValue(CONFIRMACAO);
    const user = userEvent.setup();
    const { aoConfirmar } = montar();
    expect(
      await screen.findByText("Calculado: R$ 528,72", {}, ESPERA),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Parcela da dívida?")).toHaveValue("");
    expect(
      screen.getByRole("checkbox", { name: /Não sei.*Parcela/ }),
    ).toBeChecked();
    await user.click(await continuarHabilitado());
    await waitFor(() => expect(aoConfirmar).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(confirmar.mock.calls[0][2]).toMatchObject({
      parcela: null,
      recalcular: null,
    });
  });

  it.each([
    ["PARCELA", "Parcela", "Parcela da dívida?", "R$ 528,72", "Calculado: R$ 528,72"],
    ["TAXA", "Taxa", "CET ou taxa de juros?", "2,00% a.m.", "Calculado: 2,00% a.m."],
    ["PRAZO", "Prazo", "Meses restantes?", "24", "Calculado: 24 meses"],
  ] as const)(
    "AC-614: %s calculado mostra a linha abaixo do campo, fora dele, e no aria-describedby",
    async (campo, nome, rotulo, texto, linha) => {
      gravado({
        "B5.B03": { valor_atual: "10000.00" },
        "B5.C02": { valor_atual: "NAO_SEI", respondida_como_nao_sei: true },
        "B5.C02B": { valor_atual: "NAO_SEI", respondida_como_nao_sei: true },
        "B5.D06": { valor_atual: "DESCONHECIDA" },
      });
      vi.spyOn(api, "preverCalculadora").mockResolvedValue(
        previa({
          campo_calculado: campo,
          valores: { [campo]: valor(texto, "CALCULADO") },
        }),
      );
      montar();
      const paragrafo = await screen.findByText(linha, {}, ESPERA);
      expect(paragrafo.id).toBe(`calculadora-${campo}-linha`);
      const entrada = screen.getByLabelText(rotulo);
      expect(entrada).toHaveValue("");
      expect(entrada.getAttribute("aria-describedby")).toContain(paragrafo.id);
      expect(
        screen.getByRole("checkbox", { name: new RegExp(`Não sei.*${nome}`) }),
      ).toBeChecked();
      // Uma linha só, no campo calculado.
      expect(screen.getAllByText(/^Calculado:/)).toHaveLength(1);
    },
  );

  it("AC-615: a parcela estimada vira 'Estimada: … (hipótese de 24 meses)' abaixo da parcela, sem o texto longo e sem linha no prazo", async () => {
    gravado({
      "B5.B03": { valor_atual: "10000.00" },
      "B5.C02": { valor_atual: "NAO_SEI", respondida_como_nao_sei: true },
      "B5.C02B": { valor_atual: "NAO_SEI", respondida_como_nao_sei: true },
      "B5.D06": { valor_atual: "MENSAL", valor_do_campo: "0.02" },
    });
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(
      previa({
        estado: "PENDENTE",
        parcela_estimada: {
          texto: "R$ 528,72",
          marca: "ESTIMADO",
          rotulo: "estimado",
          hipotese:
            "Sem prazo nem pagamento informados, estimamos a parcela em 24 meses.",
        },
      }),
    );
    montar();
    const paragrafo = await screen.findByText(
      "Estimada: R$ 528,72 (hipótese de 24 meses)",
      {},
      ESPERA,
    );
    expect(paragrafo.id).toBe("calculadora-PARCELA-linha");
    expect(screen.getByLabelText("Parcela da dívida?")).toHaveValue("");
    expect(
      screen.queryByText(/Sem prazo nem pagamento informados/),
    ).not.toBeInTheDocument();
    expect(document.getElementById("calculadora-PRAZO-linha")).toBeNull();
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

  it("EC-103: Continuar desabilitado enquanto a prévia não chega e depois de falha de rede", async () => {
    gravado();
    let rejeitar: (erro: unknown) => void = () => {};
    const prever = vi.spyOn(api, "preverCalculadora").mockImplementation(
      () =>
        new Promise<RespostaDaPrevia>((_resolver, rejeitarAgora) => {
          rejeitar = rejeitarAgora;
        }),
    );
    montar();
    await waitFor(() => expect(prever).toHaveBeenCalled(), ESPERA);
    expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();
    rejeitar(new api.ErroHttp(503, "Não foi possível calcular."));
    expect(await screen.findByRole("alert", {}, ESPERA)).toHaveTextContent(
      "Não foi possível calcular.",
    );
    expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();
  });

  it("confirmar envia o mesmo corpo e entrega a confirmação; 422 mostra o erro e não avança", async () => {
    gravado();
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(previa());
    const confirmar = vi
      .spyOn(api, "confirmarCalculadora")
      .mockRejectedValueOnce(new api.ErroHttp(422, "Taxa acima do limite."))
      .mockResolvedValueOnce(CONFIRMACAO);
    const user = userEvent.setup();
    const { aoConfirmar } = montar();
    await user.click(await continuarHabilitado());
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

  it("EC-105: falha ao salvar com o popup aberto mantém o popup e mostra o erro só dentro dele", async () => {
    gravado(AC_534);
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(INCOMPATIVEL);
    vi.spyOn(api, "confirmarCalculadora").mockRejectedValue(
      new api.ErroHttp(503, "Serviço indisponível."),
    );
    const user = userEvent.setup();
    const { aoConfirmar } = montar();
    await user.click(await continuarHabilitado());
    await user.click(
      screen.getByRole("button", { name: "Confirmar e continuar" }),
    );
    const alerta = await screen.findByRole("alert", {}, ESPERA);
    expect(alerta).toHaveTextContent("Serviço indisponível.");
    const dialog = screen.getByRole("dialog", { name: TITULO });
    expect(dialog).toContainElement(alerta);
    expect(screen.getAllByRole("alert")).toHaveLength(1);
    expect(aoConfirmar).not.toHaveBeenCalled();
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

  // ------------------------------------------------------------- T-678 (RF-562)

  const EXPLICACAO = { o_que_e: "O que é.", onde_encontrar: "Onde encontrar." };

  it("RF-562: com `explicacao` nas quatro perguntas, os quatro ícones ⓘ aparecem", async () => {
    gravado({
      "B5.B03": { explicacao: EXPLICACAO },
      "B5.C02": { explicacao: EXPLICACAO },
      "B5.C02B": { explicacao: EXPLICACAO },
      "B5.D06": { explicacao: EXPLICACAO },
    });
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(previa());
    montar();

    await screen.findByLabelText("Saldo devedor da dívida?");
    expect(
      screen.getByRole("button", { name: "O que é Saldo devedor?" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "O que é Parcela?" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "O que é Taxa?" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "O que é Prazo?" }),
    ).toBeInTheDocument();
  });

  it("RF-562: sem `explicacao` nas perguntas, nenhum ícone ⓘ aparece", async () => {
    gravado();
    vi.spyOn(api, "preverCalculadora").mockResolvedValue(previa());
    montar();

    await screen.findByLabelText("Saldo devedor da dívida?");
    expect(screen.queryByRole("button", { name: /^O que é/ })).toBeNull();
  });
});
