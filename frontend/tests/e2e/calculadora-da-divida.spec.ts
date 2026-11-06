/**
 * A calculadora da dívida no navegador — `T-516` (`RF-525`, `RF-526`, `AC-529`,
 * `AC-536`, `AC-538`).
 *
 * A rede é toda interceptada (`page.route`): o "servidor" aqui devolve as
 * respostas já calculadas, porque quem calcula é o backend (Lei nº 3, coberto
 * em `tests/app_aluno/test_rotas_calculadora.py`). O que se verifica é o
 * COMPORTAMENTO da tela: quais campos existem, o que é enviado à prévia, o que
 * aparece e some, a escolha de recálculo por teclado, a confirmação e a
 * navegação. Nenhum texto de redação provisória (`[PROVISORIO ...]`) é afirmado:
 * as asserções usam só os valores que a rota interceptada devolve.
 *
 * Os dois projetos (desktop e 360px) rodam estes testes.
 */
import { expect, test, type Page } from "@playwright/test";

import { abrirTela, interceptarBase } from "./apoio/navegacao";

const CASO = "CASO-E2E-CALC";
const SEGUINTE = "Qual é o credor da próxima dívida?";

const BASE = {
  CASO_ID: CASO,
  bloco: 5,
  escopo_repeticao: "DIVIDA_ID",
  item_id: "D001",
  posicao: 1,
  total_na_ficha: 2,
  admite_nao_sei: false,
  valor_atual: null,
  respondida_como_nao_sei: false,
  valores_marcados: [],
  aviso: null,
};

const PERGUNTAS: Record<string, Record<string, unknown>> = {
  "B5.CALC01": {
    tipo: "CALCULO_DIVIDA",
    enunciado: "Conferência da dívida",
    opcoes: [],
    sistema: "PRICE",
  },
  "B5.B03": { tipo: "MOEDA", enunciado: "Saldo devedor da dívida", opcoes: [] },
  "B5.C02": { tipo: "MOEDA", enunciado: "Parcela da dívida", opcoes: [] },
  "B5.C02B": {
    tipo: "NUMERO",
    enunciado: "Meses restantes da dívida",
    opcoes: [],
  },
  "B5.D06": {
    tipo: "SELECAO_UNICA",
    enunciado: "Taxa de juros da dívida",
    opcoes: [
      { rotulo: "ao mês", valor_interno: "MENSAL", admite_nao_sei: false },
      { rotulo: "ao ano", valor_interno: "ANUAL", admite_nao_sei: false },
    ],
  },
  "B5.C02A": {
    tipo: "SELECAO_UNICA",
    enunciado: "Sistema de amortização",
    opcoes: [
      { rotulo: "Price", valor_interno: "PRICE", admite_nao_sei: false },
      { rotulo: "SAC", valor_interno: "SAC", admite_nao_sei: false },
    ],
  },
};

type Corpo = {
  sistema: string;
  periodicidade: string;
  saldo: string | null;
  parcela: string | null;
  taxa: string | null;
  prazo: string | null;
  recalcular: string | null;
};

const VALOR = (texto: string, marca = "INFORMADO") => ({
  texto,
  entrada: texto,
  marca,
  rotulo: marca === "INFORMADO" ? "informado" : "calculado",
});

const PREVIA_VAZIA = {
  campo_calculado: null,
  valores: {},
  teorico: null,
  alternativas: [],
  resumo: null,
  parcela_estimada: null,
  erros: [],
  mensagem: null,
};

interface Rede {
  previas: Corpo[];
  confirmacoes: Corpo[];
  gravacoesComuns: number;
}

/** Intercepta a ficha, a prévia e a confirmação; `previa` decide a resposta de cada corpo. */
async function preparar(
  page: Page,
  previa: (corpo: Corpo) => Record<string, unknown>,
): Promise<Rede> {
  const rede: Rede = { previas: [], confirmacoes: [], gravacoesComuns: 0 };
  await interceptarBase(page, CASO, {
    inicio: {
      proxima_etapa: {
        destino: "pergunta",
        ID_PERGUNTA: "B5.CALC01",
        item_id: "D001",
      },
    },
  });
  await page.route(
    new RegExp(`/caso/${CASO}/pergunta(/[^/?]+)?(\\?.*)?$`),
    async (rota) => {
      const id = decodeURIComponent(
        new URL(rota.request().url()).pathname.split("/pergunta/")[1] ??
          "B5.CALC01",
      );
      await rota.fulfill({
        json: {
          pergunta: { ...BASE, ID: id, ...PERGUNTAS[id] },
          avanco_permitido: false,
          total_pendencias: 0,
        },
      });
    },
  );
  await page.route(`**/caso/${CASO}/calculadora/previa`, async (rota) => {
    const corpo = rota.request().postDataJSON() as Corpo;
    rede.previas.push(corpo);
    await rota.fulfill({
      json: { ...PREVIA_VAZIA, estado: "CALCULADO", ...previa(corpo) },
    });
  });
  await page.route(
    `**/caso/${CASO}/divida/D001/calculadora/confirmar`,
    async (rota) => {
      rede.confirmacoes.push(rota.request().postDataJSON() as Corpo);
      await rota.fulfill({
        json: {
          ID_PERGUNTA: "B5.CALC01",
          avisos: [],
          proxima: {
            pergunta: {
              ...BASE,
              ID: "B5.A02",
              tipo: "TEXTO_CURTO",
              enunciado: SEGUINTE,
              opcoes: [],
              item_id: "D002",
              posicao: 2,
            },
            coleta_completa: false,
          },
        },
      });
    },
  );
  // A calculadora nunca grava pelo caminho comum (`POST /resposta`): a confirmação é a única gravação.
  await page.route(`**/caso/${CASO}/resposta`, async (rota) => {
    rede.gravacoesComuns += 1;
    await rota.abort();
  });
  return rede;
}

const campo = (page: Page, nome: "SALDO" | "PARCELA" | "TAXA" | "PRAZO") =>
  page.locator(`#calculadora-${nome}`);
const naoSei = (page: Page, nome: string) =>
  page.getByRole("checkbox", { name: new RegExp(`Não sei.*${nome}`) });
const resultado = (page: Page) =>
  page.getByRole("status").filter({ hasText: /./ });

async function abrir(page: Page) {
  await abrirTela(page, CASO, "pergunta");
  await expect(campo(page, "SALDO")).toBeVisible();
}

test.describe("calculadora da dívida", () => {
  test('RF-526: três dados e "não sei" na taxa — a prévia calcula, a confirmação envia a taxa vazia e segue', async ({
    page,
  }) => {
    const rede = await preparar(page, (corpo) =>
      corpo.saldo && corpo.parcela && corpo.prazo && corpo.taxa === null
        ? {
            campo_calculado: "TAXA",
            valores: {
              SALDO: VALOR("R$ 10.000,00"),
              PARCELA: VALOR("R$ 528,72"),
              TAXA: VALOR("2,00%", "CALCULADO"),
              PRAZO: VALOR("24"),
            },
          }
        : { estado: "PENDENTE" },
    );
    await abrir(page);

    // os quatro campos, o "não sei" de cada um e o sistema com Price pré-selecionado
    for (const nome of ["SALDO", "PARCELA", "TAXA", "PRAZO"] as const) {
      await expect(campo(page, nome)).toBeVisible();
    }
    await expect(page.getByRole("radio", { name: "Price" })).toBeChecked();

    await campo(page, "SALDO").pressSequentially("1000000");
    await campo(page, "PARCELA").pressSequentially("52872");
    await campo(page, "PRAZO").pressSequentially("24");
    await naoSei(page, "Taxa").check();

    // a prévia calculada aparece, com a marca; a taxa foi como "desconhecida" (null), nunca 0
    await expect(resultado(page).getByText("2,00%")).toBeVisible();
    await expect(resultado(page).getByText("calculado")).toBeVisible();
    const ultima = rede.previas.at(-1);
    expect(ultima).toMatchObject({
      saldo: "10.000,00",
      parcela: "528,72",
      prazo: "24",
      taxa: null,
    });

    await page.getByRole("button", { name: "Continuar" }).click();

    await expect(page.getByText(SEGUINTE).first()).toBeVisible();
    expect(rede.confirmacoes).toHaveLength(1);
    expect(rede.confirmacoes[0]).toMatchObject({
      taxa: null,
      parcela: "528,72",
      recalcular: null,
    });
    expect(rede.gravacoesComuns).toBe(0);
  });

  test('AC-536: quatro valores incompatíveis — escolher "parcela" por teclado mostra o valor calculado e confirma a escolha', async ({
    page,
  }) => {
    const rede = await preparar(page, (corpo) =>
      corpo.recalcular === "PARCELA"
        ? {
            campo_calculado: "PARCELA",
            valores: { PARCELA: VALOR("R$ 528,72", "CALCULADO") },
          }
        : {
            estado: "INCOMPATIVEL",
            mensagem: "Os valores informados não batem.",
            valores: { PARCELA: VALOR("R$ 400,00") },
            teorico: { campo: "PARCELA", texto: "R$ 528,72" },
            alternativas: ["SALDO", "PARCELA", "TAXA", "PRAZO"],
          },
    );
    await abrir(page);
    await campo(page, "SALDO").pressSequentially("1000000");
    await campo(page, "PARCELA").pressSequentially("40000");
    await campo(page, "TAXA").pressSequentially("200");
    await campo(page, "PRAZO").pressSequentially("24");

    // sinalização em texto (não só cor): o valor teórico e o original ficam lado a lado
    await expect(resultado(page).getByText("R$ 528,72")).toBeVisible();
    await expect(resultado(page).getByText("R$ 400,00")).toBeVisible();
    // sem escolha, os originais permanecem
    expect(rede.confirmacoes).toHaveLength(0);

    // escolha operável só com teclado
    const parcela = page.getByRole("radio", { name: "Parcela", exact: true });
    await parcela.focus();
    await page.keyboard.press("Space");
    await expect(parcela).toBeChecked();
    await expect(resultado(page).getByText("calculado")).toBeVisible();
    expect(rede.previas.at(-1)).toMatchObject({ recalcular: "PARCELA" });

    await page.getByRole("button", { name: "Continuar" }).click();
    await expect(page.getByText(SEGUINTE).first()).toBeVisible();
    expect(rede.confirmacoes[0]).toMatchObject({
      recalcular: "PARCELA",
      saldo: "10.000,00",
    });
  });

  test("AC-529: trocar a parcela por uma que gera erro apaga o prazo antigo e não deixa confirmar", async ({
    page,
  }) => {
    const rede = await preparar(page, (corpo) =>
      corpo.parcela === "200,00"
        ? {
            estado: "ERRO",
            erros: [],
            mensagem: "A parcela não reduz o saldo.",
          }
        : {
            campo_calculado: "PRAZO",
            valores: { PRAZO: VALOR("24", "CALCULADO") },
          },
    );
    await abrir(page);
    await campo(page, "SALDO").pressSequentially("1000000");
    await campo(page, "TAXA").pressSequentially("200");
    await campo(page, "PARCELA").pressSequentially("52872");
    await naoSei(page, "Prazo").check();
    await expect(
      resultado(page).getByText("24", { exact: true }),
    ).toBeVisible();

    await campo(page, "PARCELA").fill("");
    await campo(page, "PARCELA").pressSequentially("20000");

    await expect(
      page
        .getByRole("alert")
        .filter({ hasText: "A parcela não reduz o saldo." }),
    ).toBeVisible();
    await expect(resultado(page).getByText("24", { exact: true })).toHaveCount(
      0,
    );
    await expect(
      page.getByRole("button", { name: "Continuar" }),
    ).toBeDisabled();
    expect(rede.confirmacoes).toHaveLength(0);
  });
});
