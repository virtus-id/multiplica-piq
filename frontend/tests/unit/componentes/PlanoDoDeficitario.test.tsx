// @vitest-environment happy-dom
/**
 * Plano do aluno deficitário — `RF-468`, `RF-469`, `RF-453` (`T-437`): o resultado
 * negativo em destaque, "Primeiro, estancar o problema", os maiores gastos do
 * próprio aluno e a ordem de quitação como recomendação, sem prazo.
 */
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import PlanoDoAluno from "../../../src/componentes/PlanoDoAluno";
import type { Plano } from "../../../src/tipos";

const TEXTOS = {
  titulo: "Primeiro, estancar o problema",
  resultado_rotulo: "Seu mês fecha em",
  texto: "Hoje o seu mês fecha em {valor}: entra menos do que sai.",
  falta_cortar: "Para chegar a zero, faltam cortar {valor} por mês.",
  depois_de_zerar:
    "A partir daí, cada real que ficar livre vira dinheiro para atacar as dívidas.",
  gastos_titulo: "Onde olhar nos seus gastos",
  gastos_intro: "Estes são os seus maiores gastos do mês.",
  ordem_titulo: "A ordem de quitação, por enquanto provisória",
  ordem_intro: "É uma recomendação, não um cronograma de pagamento.",
  metodo_rotulo: "Método recomendado",
};

function posicao(indice: number, nome: string) {
  return {
    posicao: indice,
    indice,
    total: 2,
    DIVIDA_ID: `D${indice}`,
    nome,
    JUSTIFICATIVA_POSICAO: "",
    explicacao: "Todo o valor extra vai primeiro para esta dívida.",
    fonte: null,
    valores_de_apoio: [],
    fatos: [{ rotulo: "Quanto você deve hoje", valor: "R$ 1.000,00" }],
    mes_de_quitacao: null,
    incomodo: "",
    aviso_incomodo: "",
  };
}

function plano(extra: Partial<Plano>): Plano {
  return {
    titulo: "Plano",
    corpo: "corpo",
    ordem: [],
    PRAZO_TOTAL: "14 meses",
    PRAZO_TOTAL_INT: 14,
    CUSTO_FUTURO_TOTAL: "R$ 1,00",
    ENGINE_VERSION: "e",
    PARAMETROS_VERSION: "p",
    metodo: "Bola de neve",
    cenario: "x",
    acoes: [],
    pendencias: null,
    MODO_ESTABILIZACAO: true,
    RESULTADO_CAIXA_OBSERVADO: "R$ -6.987,11",
    FALTA_CORTAR: "R$ 6.987,11",
    reserva_mobilizavel: { pendente_de_decisao: false, valor: "" },
    cenario_adicional: null,
    nao_projetados: [],
    estabilizacao_textos: TEXTOS,
    maiores_gastos: [
      { nome: "Aluguel", valor: "R$ 2.500,00" },
      { nome: "Mercado", valor: "R$ 1.800,00" },
    ],
    ...extra,
  } as Plano;
}

describe("PlanoDoAluno — aluno deficitário", () => {
  it("abre com o resultado negativo em destaque e o valor para chegar a zero", () => {
    render(<PlanoDoAluno plano={plano({})} />);

    const secao = screen.getByRole("region", {
      name: "Primeiro, estancar o problema",
    });
    expect(within(secao).getByText("Seu mês fecha em")).toBeTruthy();
    expect(
      within(secao).getAllByText(/R\$ -6\.987,11/).length,
    ).toBeGreaterThanOrEqual(2);
    expect(
      within(secao).getByText(
        "Para chegar a zero, faltam cortar R$ 6.987,11 por mês.",
      ),
    ).toBeTruthy();
    expect(within(secao).getByText(/cada real que ficar livre/)).toBeTruthy();
  });

  it("mostra os maiores gastos do aluno, do maior para o menor", () => {
    render(<PlanoDoAluno plano={plano({})} />);

    const secao = screen.getByRole("region", {
      name: "Onde olhar nos seus gastos",
    });
    const nomes = within(secao)
      .getAllByRole("term")
      .map((no) => no.textContent);
    expect(nomes).toEqual(["Aluguel", "Mercado"]);
    expect(within(secao).getByText("R$ 2.500,00")).toBeTruthy();
  });

  it("mostra a ordem como recomendação provisória, sem mês de quitação", () => {
    render(
      <PlanoDoAluno
        plano={plano({
          ordem: [posicao(1, "Cartão"), posicao(2, "Consignado")],
        })}
      />,
    );

    const secao = screen.getByRole("region", {
      name: "A ordem de quitação, por enquanto provisória",
    });
    expect(
      within(secao).getByText(
        "É uma recomendação, não um cronograma de pagamento.",
      ),
    ).toBeTruthy();
    expect(within(secao).getByText("1. Cartão")).toBeTruthy();
    expect(within(secao).getByText("2. Consignado")).toBeTruthy();
    expect(screen.queryByText("Termina no")).toBeNull();
    expect(
      screen.queryByText("Todo o valor extra vai primeiro para esta dívida."),
    ).toBeNull();
  });

  it("sem gastos informados, o bloco dos gastos não aparece", () => {
    render(<PlanoDoAluno plano={plano({ maiores_gastos: [] })} />);

    expect(
      screen.queryByRole("region", { name: "Onde olhar nos seus gastos" }),
    ).toBeNull();
  });

  it("mês positivo com dívida que cresce tem mensagem própria, sem o texto do deficitário (RF-480)", () => {
    render(
      <PlanoDoAluno
        plano={plano({
          RESULTADO_CAIXA_OBSERVADO: "R$ 475,00",
          FALTA_CORTAR: "R$ 0,00",
          ESTABILIZACAO_POR_DIVIDA: true,
          FALTA_TOTAL_DE_JUROS: "R$ 898,00",
          dividas_que_crescem: [
            {
              nome: "Cheque especial",
              parcela: "R$ 500,00",
              juros: "R$ 1.000,00",
              falta: "R$ 500,00",
            },
          ],
          estabilizacao_por_divida_textos: {
            titulo: "Seu mês fecha positivo, mas suas dívidas estão crescendo",
            resultado_rotulo: "Valor livre no mês",
            texto:
              "Depois de pagar tudo, ficam {valor} livres por mês. As dívidas crescem {falta_total} por mês.",
            dividas_titulo: "Dívidas que crescem",
            divida_linha:
              "{nome}: parcela de {parcela}, juros de {juros} por mês. O saldo aumenta {falta} por mês.",
            passos_titulo: "O que fazer agora",
            passo_1: "Reduza os gastos: veja o que dá para reduzir.",
            passo_2: "Renegocie a dívida que mais cresce.",
          },
        })}
      />,
    );

    const secao = screen.getByRole("region", {
      name: "Seu mês fecha positivo, mas suas dívidas estão crescendo",
    });
    expect(
      within(secao).getByText(
        "Depois de pagar tudo, ficam R$ 475,00 livres por mês. As dívidas crescem R$ 898,00 por mês.",
      ),
    ).toBeTruthy();
    expect(
      within(secao).getByText(
        "Cheque especial: parcela de R$ 500,00, juros de R$ 1.000,00 por mês. O saldo aumenta R$ 500,00 por mês.",
      ),
    ).toBeTruthy();
    expect(screen.queryByText(/faltam cortar/)).toBeNull();
    expect(
      screen.queryByRole("region", { name: "Primeiro, estancar o problema" }),
    ).toBeNull();
    // OQ-71 (T-472): dois passos, nesta ordem, e a lista dos maiores gastos
    const passos = within(secao)
      .getAllByRole("listitem")
      .map((no) => no.textContent)
      .filter((texto) => texto?.startsWith("Reduza") || texto?.startsWith("Renegocie"));
    expect(passos).toEqual([
      "Reduza os gastos: veja o que dá para reduzir.",
      "Renegocie a dívida que mais cresce.",
    ]);
    expect(
      screen.getByRole("region", { name: "Onde olhar nos seus gastos" }),
    ).toBeTruthy();
  });

  it("marca na ordem a dívida que não quita no horizonte (RF-481)", () => {
    const quitavel = posicao(1, "Consignado");
    const semQuitacao = {
      ...posicao(2, "Cheque especial"),
      fora_do_horizonte: "Não será quitada com os valores de hoje",
    };
    render(<PlanoDoAluno plano={plano({ ordem: [quitavel, semQuitacao] })} />);

    const secao = screen.getByRole("region", {
      name: "A ordem de quitação, por enquanto provisória",
    });
    expect(within(secao).getByText("2. Cheque especial")).toBeTruthy();
    expect(
      within(secao).getAllByText("Não será quitada com os valores de hoje"),
    ).toHaveLength(1);
  });

  it("plano normal não mostra nada do deficitário", () => {
    render(
      <PlanoDoAluno
        plano={plano({
          MODO_ESTABILIZACAO: false,
          ordem: [posicao(1, "Cartão")],
        })}
      />,
    );

    expect(screen.queryByText("Primeiro, estancar o problema")).toBeNull();
    expect(
      screen.queryByRole("region", { name: "Onde olhar nos seus gastos" }),
    ).toBeNull();
    expect(screen.getByText("Termina no")).toBeTruthy();
  });
});
