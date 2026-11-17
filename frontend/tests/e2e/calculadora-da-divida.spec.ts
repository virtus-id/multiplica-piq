/**
 * A calculadora da dívida no navegador — `T-516`, `T-688` (`RF-526`,
 * `RF-564` a `RF-568`, `AC-604`, `AC-606`, `AC-608` a `AC-612`, `AC-614`,
 * `AC-616`, `EC-100`).
 *
 * A rede é toda interceptada (`page.route`): o "servidor" aqui devolve as
 * respostas já calculadas, porque quem calcula é o backend (Lei nº 3, coberto
 * em `tests/app_aluno/test_rotas_calculadora.py`). O que se verifica é o
 * COMPORTAMENTO da tela: quais campos existem, o que é enviado à prévia, o que
 * aparece e some, o popup da divergência (modal de verdade, Esc, teclado), a
 * confirmação e a navegação. Nenhum texto de redação provisória
 * (`[PROVISORIO ...]`) é afirmado; os textos do popup e da linha marcada são a
 * sugestão de `T-681`.
 *
 * É o único lugar com prova do comportamento modal real (`AC-610`, o Esc de
 * `AC-611`): o happy-dom dos unitários não implementa foco preso nem Esc.
 *
 * Os dois projetos (desktop e 360px) rodam estes testes.
 */
import { expect, test, type Page } from "@playwright/test";

import { abrirTela, interceptarBase } from "./apoio/navegacao";

const CASO = "CASO-E2E-CALC";
const SEGUINTE = "Qual é o credor da próxima dívida?";
const TITULO = "Os valores desta dívida não batem";

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
    // `T-679` (RF-563): sem o parêntese de ajuda — o conteúdo equivalente
    // vive só no ⓘ (`explicacao` abaixo, RF-562).
    enunciado: "Taxa de juros da dívida",
    opcoes: [
      { rotulo: "ao mês", valor_interno: "MENSAL", admite_nao_sei: false },
      { rotulo: "ao ano", valor_interno: "ANUAL", admite_nao_sei: false },
    ],
    explicacao: {
      o_que_e: "Quanto a dívida cobra de juros.",
      onde_encontrar: "No DDC ou no aplicativo do banco.",
    },
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
const linha = (page: Page, nome: "SALDO" | "PARCELA" | "TAXA" | "PRAZO") =>
  page.locator(`#calculadora-${nome}-linha`);
const continuar = (page: Page) =>
  page.getByRole("button", { name: "Continuar" });
const popup = (page: Page) => page.getByRole("dialog", { name: TITULO });
const manter = (page: Page) =>
  page.getByRole("radio", { name: "Manter os valores que informei" });

async function abrir(page: Page) {
  await abrirTela(page, CASO, "pergunta");
  await expect(campo(page, "SALDO")).toBeVisible();
}

/** `AC-534`: saldo R$ 10.000,00, 2% ao mês, 24 meses e parcela R$ 400,00 — incompatíveis. */
function incompativel(corpo: Corpo): Record<string, unknown> {
  return corpo.recalcular === "PARCELA"
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
        hipotese_conservadora: {
          saldo: "R$ 13.240,00",
          taxa: "2,00% a.m.",
          marca: "HIPOTESE",
          rotulo: "hipótese",
          aviso: "Só o saldo e a taxa contam para o plano.",
        },
      };
}

/** Digita o `AC-534` e espera a prévia chegar ("Continuar" habilita). */
async function digitarIncompativeis(page: Page) {
  await campo(page, "SALDO").pressSequentially("1000000");
  await campo(page, "PARCELA").pressSequentially("40000");
  await campo(page, "TAXA").pressSequentially("200");
  await campo(page, "PRAZO").pressSequentially("24");
  await expect(continuar(page)).toBeEnabled();
}

test.describe("calculadora da dívida", () => {
  test('RF-526, AC-614: três dados e "não sei" na taxa — a linha "Calculado" aparece abaixo da taxa e a confirmação segue sem popup', async ({
    page,
  }) => {
    const rede = await preparar(page, (corpo) =>
      corpo.saldo && corpo.parcela && corpo.prazo && corpo.taxa === null
        ? {
            campo_calculado: "TAXA",
            valores: {
              SALDO: VALOR("R$ 10.000,00"),
              PARCELA: VALOR("R$ 528,72"),
              TAXA: VALOR("2,00% a.m.", "CALCULADO"),
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

    // a linha marcada fica abaixo da taxa, fora do campo; a taxa foi como "desconhecida" (null), nunca 0
    await expect(linha(page, "TAXA")).toHaveText("Calculado: 2,00% a.m.");
    await expect(campo(page, "TAXA")).toHaveValue("");
    await expect(page.getByRole("status").filter({ hasText: /./ })).toHaveCount(
      0,
    );
    const ultima = rede.previas.at(-1);
    expect(ultima).toMatchObject({
      saldo: "10.000,00",
      parcela: "528,72",
      prazo: "24",
      taxa: null,
    });

    await continuar(page).click();

    await expect(page.getByText(SEGUINTE).first()).toBeVisible();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    expect(rede.confirmacoes).toHaveLength(1);
    expect(rede.confirmacoes[0]).toMatchObject({
      taxa: null,
      parcela: "528,72",
      recalcular: null,
    });
    expect(rede.gravacoesComuns).toBe(0);
  });

  test('AC-604, AC-606, AC-608, AC-612: incompatíveis — nada abaixo dos campos; "Continuar" abre o popup; "Recalcular a parcela" por teclado confirma a escolha', async ({
    page,
  }, infoDoTeste) => {
    const rede = await preparar(page, incompativel);
    await abrir(page);
    await digitarIncompativeis(page);

    // AC-604: nada da divergência na página, e nenhum popup antes do clique
    await expect(page.getByText("R$ 528,72")).toHaveCount(0);
    await expect(page.getByText("R$ 13.240,00")).toHaveCount(0);
    await expect(page.getByRole("radio", { name: /Recalcular/ })).toHaveCount(0);
    await expect(page.getByRole("dialog")).toHaveCount(0);

    // AC-606: "Continuar" abre o popup e nada é gravado
    await continuar(page).click();
    await expect(popup(page)).toBeVisible();
    await expect(
      popup(page).getByText(
        "Com esse saldo, taxa e prazo, a parcela seria R$ 528,72. Você informou R$ 400,00.",
      ),
    ).toBeVisible();
    expect(rede.confirmacoes).toHaveLength(0);

    if (infoDoTeste.project.name === "mobile-360") {
      const caixa = await popup(page).boundingBox();
      expect(caixa?.width ?? Infinity).toBeLessThanOrEqual(360);
      const confirmar = popup(page).getByRole("button", {
        name: "Confirmar e continuar",
      });
      await confirmar.scrollIntoViewIfNeeded();
      await expect(confirmar).toBeInViewport();
    }

    // escolha só pelo teclado: o foco abre em "Manter"; as setas percorrem o grupo
    await expect(manter(page)).toBeFocused();
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("ArrowDown");
    const parcela = page.getByRole("radio", { name: "Recalcular a parcela" });
    await expect(parcela).toBeChecked();
    await expect(
      popup(page).getByText("Parcela recalculada: R$ 528,72 (calculado)"),
    ).toBeVisible();
    expect(rede.previas.at(-1)).toMatchObject({ recalcular: "PARCELA" });

    await popup(page)
      .getByRole("button", { name: "Confirmar e continuar" })
      .click();
    await expect(page.getByText(SEGUINTE).first()).toBeVisible();
    expect(rede.confirmacoes).toHaveLength(1);
    expect(rede.confirmacoes[0]).toMatchObject({
      recalcular: "PARCELA",
      saldo: "10.000,00",
    });
  });

  test('AC-609: "Manter os valores que informei" grava os quatro como digitados, sem escolha', async ({
    page,
  }) => {
    const rede = await preparar(page, incompativel);
    await abrir(page);
    await digitarIncompativeis(page);
    await continuar(page).click();
    await expect(manter(page)).toBeChecked();

    await popup(page)
      .getByRole("button", { name: "Confirmar e continuar" })
      .click();
    await expect(page.getByText(SEGUINTE).first()).toBeVisible();
    expect(rede.confirmacoes).toHaveLength(1);
    expect(rede.confirmacoes[0]).toMatchObject({
      recalcular: null,
      parcela: "400,00",
      saldo: "10.000,00",
      prazo: "24",
    });
  });

  test("AC-610: o popup é modal — o foco entra nele e Tab/Shift+Tab nunca chegam aos campos atrás", async ({
    page,
  }) => {
    await preparar(page, incompativel);
    await abrir(page);
    await digitarIncompativeis(page);
    await continuar(page).click();
    await expect(popup(page)).toBeVisible();

    expect(await popup(page).evaluate((d) => d.matches(":modal"))).toBe(true);
    const focoNoPopup = () =>
      page.evaluate(() => document.activeElement?.closest("dialog") !== null);
    const focoNumCampo = () =>
      page.evaluate(
        () => document.activeElement?.id.startsWith("calculadora-") ?? false,
      );
    expect(await focoNoPopup()).toBe(true);

    // três paradas (o grupo de opções e os dois botões): duas voltas de cada lado
    for (const tecla of ["Tab", "Shift+Tab"]) {
      for (let i = 0; i < 6; i += 1) {
        await page.keyboard.press(tecla);
        expect(await focoNumCampo()).toBe(false);
      }
    }
    await expect(popup(page)).toBeVisible();
  });

  for (const saida of ["Esc", "Voltar e corrigir"] as const) {
    test(`AC-611, EC-100: ${saida} fecha sem gravar, deixa os campos, foca o saldo e reabre com "Manter"`, async ({
      page,
    }) => {
      const rede = await preparar(page, incompativel);
      await abrir(page);
      await digitarIncompativeis(page);
      await continuar(page).click();
      await page.getByRole("radio", { name: "Recalcular a parcela" }).check();
      await expect(
        popup(page).getByText("Parcela recalculada: R$ 528,72 (calculado)"),
      ).toBeVisible();

      if (saida === "Esc") await page.keyboard.press("Escape");
      else
        await popup(page)
          .getByRole("button", { name: "Voltar e corrigir" })
          .click();

      await expect(page.getByRole("dialog")).toHaveCount(0);
      expect(rede.confirmacoes).toHaveLength(0);
      await expect(campo(page, "PARCELA")).toHaveValue("400,00");
      await expect(campo(page, "SALDO")).toBeFocused();

      await continuar(page).click();
      await expect(popup(page)).toBeVisible();
      await expect(manter(page)).toBeChecked();
      expect(rede.confirmacoes).toHaveLength(0);
    });
  }

  test('AC-616: trocar a parcela por uma que gera erro apaga "Calculado: 24 meses" e não deixa confirmar', async ({
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
    await expect(linha(page, "PRAZO")).toHaveText("Calculado: 24 meses");

    await campo(page, "PARCELA").fill("");
    await campo(page, "PARCELA").pressSequentially("20000");

    await expect(
      page
        .getByRole("alert")
        .filter({ hasText: "A parcela não reduz o saldo." }),
    ).toBeVisible();
    await expect(linha(page, "PRAZO")).toHaveCount(0);
    await expect(page.getByText("Calculado: 24 meses")).toHaveCount(0);
    await expect(continuar(page)).toBeDisabled();
    expect(rede.confirmacoes).toHaveLength(0);
  });

  test("RF-562/RF-563: o rótulo da taxa não traz o parêntese, e o ⓘ abre a mesma ajuda do registro", async ({
    page,
  }) => {
    await preparar(page, () => ({ estado: "PENDENTE" }));
    await abrir(page);

    // `AC-602`: o rótulo do campo de taxa não traz mais o parêntese de ajuda.
    await expect(
      page.getByText("No seu contrato, extrato ou aplicativo do banco"),
    ).toHaveCount(0);

    const botaoDaAjuda = page.getByRole("button", { name: "O que é Taxa?" });
    await expect(botaoDaAjuda).toBeVisible();
    await botaoDaAjuda.hover();
    await expect(page.getByRole("tooltip")).toContainText(
      "Quanto a dívida cobra de juros.",
    );
    await expect(page.getByRole("tooltip")).toContainText(
      "No DDC ou no aplicativo do banco.",
    );
  });
});
