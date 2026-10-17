// @vitest-environment happy-dom
/**
 * `TelaRevisao` — a tabela de casos do revisor (`RF-502`, `RF-504`, `RF-505`,
 * `RF-507`, T-409; linguagem humana: `RF-111`, `AC-174`).
 */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TelaRevisao from "../../../src/telas/TelaRevisao";
import * as api from "../../../src/services/api";
import type { LinhaDeCaso, RespostaDeCasos } from "../../../src/tipos";

beforeEach(() => sessionStorage.clear());
afterEach(() => vi.restoreAllMocks());

const LINHA: LinhaDeCaso = {
  CASO_ID: "CASO-1",
  nome: "Fulana de Tal",
  email_do_aluno: "fulana@exemplo.com",
  chegou_em: "2026-10-01T12:00:00+00:00",
  chegada_aproximada: false,
  tempo_na_fila_horas: 52,
  atrasado: false,
  status: "AGUARDANDO_REVISAO",
  status_rotulo: "Em revisão",
  tipo: "primeiro",
  tipo_rotulo: "Primeiro plano",
  motivo_rotulo: "Primeiro cálculo, sem evento de recálculo",
  mes_negativo: false,
  situacao_mes_rotulo: "Fecha positivo",
  dividas: 3,
  metodo: "Híbrido",
  status_metodo: "Definitivo na data",
  entra_por_politica: true,
  e_metodologico: false,
  revisor: null,
  decidido_em: null,
};

function resposta(extra: Partial<RespostaDeCasos> = {}, linha: Partial<LinhaDeCaso> = {}): RespostaDeCasos {
  return {
    itens: [{ ...LINHA, ...linha }],
    total: 1,
    pagina: 1,
    por_pagina: 25,
    contagens: { pendentes: 1, entregues: 2, devolvidos: 3, todos: 6 },
    opcoes: {
      metodos: [{ codigo: "HIBRIDO", rotulo: "Híbrido" }],
      motivos: [{ codigo: "M1", rotulo: "Primeiro cálculo, sem evento de recálculo" }],
      revisores: [{ codigo: "R1", rotulo: "Rodrigo" }],
    },
    ...extra,
  };
}

function espiar(r: RespostaDeCasos = resposta()) {
  return vi.spyOn(api, "obterCasosParaRevisao").mockResolvedValue(r);
}
const ultima = (s: ReturnType<typeof espiar>) => s.mock.calls[s.mock.calls.length - 1][0];
const tabela = () => within(screen.getByTestId("tabela-de-casos"));
const aTabela = async () => within(await screen.findByTestId("tabela-de-casos"));

describe("TelaRevisao — colunas e linguagem humana", () => {
  it("mostra as colunas por rótulo, sem nenhum código do motor", async () => {
    espiar();
    const { container } = render(<TelaRevisao aoSair={vi.fn()} />);

    expect((await aTabela()).getByText("Fulana de Tal")).toBeInTheDocument();
    expect(tabela().getByText("fulana@exemplo.com")).toBeInTheDocument();
    expect(tabela().getByText("2 d")).toBeInTheDocument();
    expect(tabela().getByText("Em revisão")).toBeInTheDocument();
    expect(tabela().getByText("Positivo")).toBeInTheDocument();
    expect(tabela().getByText("Híbrido")).toBeInTheDocument();
    expect(tabela().getByText("Definitivo na data")).toBeInTheDocument();
    expect(tabela().getByText("Fulana de Tal")).toHaveAttribute("title", "Fulana de Tal");
    expect(container.textContent).not.toMatch(/[A-Z]+_[A-Z_]+/);
  });

  it("sem nome, só o e-mail; sem e-mail, o CASO_ID", async () => {
    espiar(resposta({}, { nome: null }));
    render(<TelaRevisao aoSair={vi.fn()} />);
    expect((await aTabela()).getByText("fulana@exemplo.com")).toHaveClass("font-bold");
  });

  it("tempo na fila mostra só os dias, sem a frase de alerta", async () => {
    espiar(resposta({}, { atrasado: true, tempo_na_fila_horas: 9 * 24 + 23 }));
    const { container } = render(<TelaRevisao aoSair={vi.fn()} />);
    expect((await aTabela()).getByText("9 d")).toBeInTheDocument();
    expect(container.textContent).not.toContain("Parado há");
    expect(container.textContent).not.toMatch(/\d h\b/);
  });

  it("menos de um dia vira '0 d'", async () => {
    espiar(resposta({}, { tempo_na_fila_horas: 5 }));
    render(<TelaRevisao aoSair={vi.fn()} />);
    expect((await aTabela()).getByText("0 d")).toBeInTheDocument();
  });

  it("atrasado tem nome acessível (aria-label), não texto visível; em dia não tem", async () => {
    espiar(resposta({}, { atrasado: true, tempo_na_fila_horas: 130 }));
    const { unmount } = render(<TelaRevisao aoSair={vi.fn()} />);
    const alerta = (await aTabela()).getByRole("img", { name: "Parado há 5 dias ou mais" });
    expect(alerta).toHaveAttribute("aria-label", "Parado há 5 dias ou mais");
    expect(alerta).toHaveAttribute("title", "Parado há 5 dias ou mais");
    unmount();

    espiar(resposta({}, { atrasado: false }));
    render(<TelaRevisao aoSair={vi.fn()} />);
    await aTabela();
    expect(screen.queryByRole("img", { name: /Parado há/ })).toBeNull();
  });

  it("cabeçalhos: só as colunas decididas pelo produto", async () => {
    espiar();
    render(<TelaRevisao aoSair={vi.fn()} />);
    const nomes = (await aTabela()).getAllByRole("columnheader").map((h) => h.textContent?.replace(/ [▲▼]$/, ""));
    expect(nomes).toEqual(["Aluno", "Tempo na fila", "Status", "Fecha no mês", "Dívidas", "Método", "Revisor e decisão", "Ação"]);
    for (const fora of ["Chegou em", "Tipo", "Motivo da revisão", "Política 100%", "Revisão obrigatória pelo motor"]) {
      expect(screen.queryByText(fora)).toBeNull();
    }
  });

  it("Fecha no mês: Positivo (verde) e Negativo (vermelho), sempre com texto", async () => {
    espiar(resposta({}, { mes_negativo: false }));
    const { unmount } = render(<TelaRevisao aoSair={vi.fn()} />);
    const positivo = (await aTabela()).getByText("Positivo");
    expect(positivo).toHaveClass("chip-ok");
    unmount();

    espiar(resposta({}, { mes_negativo: true }));
    render(<TelaRevisao aoSair={vi.fn()} />);
    const negativo = (await aTabela()).getByText("Negativo");
    expect(negativo).toHaveClass("text-bad");
    expect(negativo).not.toHaveClass("chip-ok");
    expect(within(screen.getByTestId("cartoes-de-casos")).getByText("Negativo")).toBeInTheDocument();
  });

  it("decidido mostra quem e quando", async () => {
    espiar(resposta({}, { status: "PLANO_LIBERADO", status_rotulo: "Entregue", revisor: "Rodrigo", decidido_em: "2026-10-03T15:00:00+00:00" }));
    render(<TelaRevisao aoSair={vi.fn()} />);
    expect((await aTabela()).getByText("Rodrigo")).toBeInTheDocument();
  });

  it("'Abrir' chama abrirCaso com o CASO_ID, também pela linha", async () => {
    espiar();
    const abrir = vi.fn();
    render(<TelaRevisao aoSair={vi.fn()} abrirCaso={abrir} />);
    await userEvent.click((await aTabela()).getByRole("button", { name: /Abrir/ }));
    expect(abrir).toHaveBeenCalledTimes(1);
    expect(abrir).toHaveBeenCalledWith("CASO-1");
    await userEvent.click(tabela().getByText("Híbrido"));
    expect(abrir).toHaveBeenCalledTimes(2);
  });

  it("os cartões do celular trazem os mesmos dados", async () => {
    espiar();
    render(<TelaRevisao aoSair={vi.fn()} />);
    const cartoes = within(await screen.findByTestId("cartoes-de-casos"));
    expect(cartoes.getByText("Fulana de Tal")).toBeInTheDocument();
    expect(cartoes.getByText("Em revisão")).toBeInTheDocument();
  });
});

describe("TelaRevisao — abas, filtros, ordem e páginas", () => {
  it("abas com contagem; trocar de aba consulta com a aba nova", async () => {
    const s = espiar();
    render(<TelaRevisao aoSair={vi.fn()} />);
    expect(await screen.findByRole("button", { name: "Entregues (2)" })).toBeInTheDocument();
    expect(ultima(s)).toMatchObject({ aba: "pendentes", ordenar: "chegou_em", direcao: "asc" });

    await userEvent.click(screen.getByRole("button", { name: "Todos (6)" }));
    await waitFor(() =>
      expect(ultima(s)).toMatchObject({ aba: "todos", ordenar: "chegou_em", direcao: "desc" }),
    );
  });

  it("a busca é o único filtro: sem período, tipo, mês, método, motivo, revisor, parado nem status", async () => {
    espiar();
    render(<TelaRevisao aoSair={vi.fn()} />);
    await screen.findByRole("button", { name: "Pendentes (1)" });
    expect(screen.getByLabelText("Buscar por nome ou e-mail")).toBeInTheDocument();
    for (const rotulo of ["Chegou a partir de", "Chegou até", "Tipo", "Mês no negativo", "Motivo da revisão", "Revisor", "Parado há mais de (horas)", "Status"]) {
      expect(screen.queryByLabelText(rotulo)).toBeNull();
    }
    expect(screen.queryByRole("button", { name: /Limpar filtros/ })).toBeNull();
    expect(screen.queryByRole("group", { name: "Filtros ativos" })).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
    // Só a busca (texto) e o "Por página" são campos; nenhum seletor de filtro.
    expect(screen.getAllByRole("combobox")).toHaveLength(1);
  });

  it("a busca fica no mesmo contêiner das abas", async () => {
    espiar();
    render(<TelaRevisao aoSair={vi.fn()} />);
    await screen.findByRole("button", { name: "Pendentes (1)" });
    const linha = within(screen.getByTestId("abas-e-busca"));
    expect(linha.getByRole("group", { name: "Situação dos planos" })).toBeInTheDocument();
    expect(linha.getByLabelText("Buscar por nome ou e-mail")).toBeInTheDocument();
  });

  it("a busca vira o parâmetro q e o 'x' limpa", async () => {
    const s = espiar();
    render(<TelaRevisao aoSair={vi.fn()} />);
    await screen.findByRole("button", { name: "Pendentes (1)" });
    await userEvent.type(screen.getByLabelText("Buscar por nome ou e-mail"), "fula");
    await waitFor(() => expect(ultima(s)).toMatchObject({ q: "fula", pagina: 1 }));

    await userEvent.click(screen.getByRole("button", { name: "Limpar busca" }));
    await waitFor(() => expect(ultima(s).q).toBeUndefined());
    expect(screen.getByLabelText("Buscar por nome ou e-mail")).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Limpar busca" })).toBeNull();
  });

  it("a busca espera a pausa na digitação", async () => {
    const s = espiar();
    render(<TelaRevisao aoSair={vi.fn()} />);
    await screen.findByRole("button", { name: "Pendentes (1)" });
    await userEvent.type(screen.getByLabelText("Buscar por nome ou e-mail"), "fula");
    await waitFor(() => expect(ultima(s).q).toBe("fula"));
  });

  it("o termo de busca fica guardado na sessão", async () => {
    espiar();
    const { unmount } = render(<TelaRevisao aoSair={vi.fn()} />);
    await screen.findByRole("button", { name: "Pendentes (1)" });
    await userEvent.type(screen.getByLabelText("Buscar por nome ou e-mail"), "fula");
    await waitFor(() => expect(sessionStorage.getItem("piq.fila.busca")).toBe("fula"));
    unmount();

    const s = espiar();
    render(<TelaRevisao aoSair={vi.fn()} />);
    await screen.findByRole("button", { name: "Pendentes (1)" });
    expect(ultima(s).q).toBe("fula");
    expect(screen.getByLabelText("Buscar por nome ou e-mail")).toHaveValue("fula");
  });

  it("cabeçalho ordenável: aria-sort e clique alternam a direção", async () => {
    const s = espiar();
    render(<TelaRevisao aoSair={vi.fn()} />);
    expect((await aTabela()).getByRole("columnheader", { name: "Aluno" })).toHaveAttribute("aria-sort", "none");
    expect(tabela().getByRole("columnheader", { name: "Aluno" })).toHaveAttribute("aria-sort", "none");

    await userEvent.click(tabela().getByRole("button", { name: "Aluno" }));
    await waitFor(() => expect(ultima(s)).toMatchObject({ ordenar: "aluno", direcao: "asc" }));
    await userEvent.click(tabela().getByRole("button", { name: /Aluno/ }));
    await waitFor(() => expect(ultima(s)).toMatchObject({ ordenar: "aluno", direcao: "desc" }));
    expect(tabela().getByRole("columnheader", { name: /Aluno/ })).toHaveAttribute("aria-sort", "descending");
  });

  it("paginação: 'mostrando N–M de T', próxima e 50 por página", async () => {
    const s = espiar(resposta({ total: 60 }));
    render(<TelaRevisao aoSair={vi.fn()} />);
    expect(await screen.findByText("Mostrando 1–25 de 60")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Próxima" }));
    await waitFor(() => expect(ultima(s).pagina).toBe(2));

    await userEvent.selectOptions(screen.getByLabelText("Por página"), "50");
    await waitFor(() => expect(ultima(s)).toMatchObject({ por_pagina: 50, pagina: 1 }));
  });
});

describe("TelaRevisao — estados", () => {
  it("carregando: esqueleto só na primeira carga", async () => {
    vi.spyOn(api, "obterCasosParaRevisao").mockReturnValue(new Promise(() => {}));
    render(<TelaRevisao aoSair={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando a fila");
  });

  it("vazio: só 'Nenhum plano encontrado.'", async () => {
    espiar(resposta({ itens: [], total: 0 }));
    render(<TelaRevisao aoSair={vi.fn()} />);
    expect(await screen.findByText("Nenhum plano encontrado.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Limpar/ })).toBeNull();
  });

  it.each([
    [401, "Sua sessão expirou. Entre novamente."],
    [403, "Esta tela é da equipe de conferência. Sua conta não tem esse acesso."],
  ])("erro %i vira mensagem humana", async (status, texto) => {
    vi.spyOn(api, "obterCasosParaRevisao").mockRejectedValue(new api.ErroHttp(status, `HTTP ${status}`, []));
    render(<TelaRevisao aoSair={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(texto);
  });

  it("erro geral cai na mensagem padrão; 'Atualizar a fila' e o painel seguem", async () => {
    vi.spyOn(api, "obterCasosParaRevisao").mockRejectedValue(new Error("x"));
    const painel = vi.fn();
    render(<TelaRevisao aoSair={vi.fn()} abrirPainel={painel} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível carregar a fila.");
    await userEvent.click(screen.getByRole("button", { name: "Ver painel de usuários" }));
    expect(painel).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Atualizar a fila" })).toBeInTheDocument();
  });
});
