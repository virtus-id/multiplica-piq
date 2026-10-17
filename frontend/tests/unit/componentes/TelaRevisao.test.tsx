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
    expect(tabela().getByText("2 d 4 h")).toBeInTheDocument();
    expect(tabela().getByText("Em revisão")).toBeInTheDocument();
    expect(tabela().getByText("Primeiro plano")).toBeInTheDocument();
    expect(tabela().getByText("Fecha positivo")).toBeInTheDocument();
    expect(tabela().getByText("Híbrido")).toBeInTheDocument();
    expect(tabela().getByText("Definitivo na data")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/[A-Z]+_[A-Z_]+/);
  });

  it("sem nome, só o e-mail; sem e-mail, o CASO_ID", async () => {
    espiar(resposta({}, { nome: null }));
    render(<TelaRevisao aoSair={vi.fn()} />);
    expect((await aTabela()).getByText("fulana@exemplo.com")).toHaveClass("font-bold");
  });

  it("chegada aproximada vem marcada", async () => {
    espiar(resposta({}, { chegada_aproximada: true }));
    render(<TelaRevisao aoSair={vi.fn()} />);
    expect((await aTabela()).getByText("aprox.")).toBeInTheDocument();
  });

  it("pendente atrasado ganha texto, não só cor", async () => {
    espiar(resposta({}, { atrasado: true, tempo_na_fila_horas: 130 }));
    render(<TelaRevisao aoSair={vi.fn()} />);
    expect((await aTabela()).getByText("Parado há 5 dias ou mais")).toBeInTheDocument();
  });

  it("os dois sinais são chips separados", async () => {
    espiar(resposta({}, { entra_por_politica: true, e_metodologico: true }));
    render(<TelaRevisao aoSair={vi.fn()} />);
    const politica = (await aTabela()).getByText("Política 100%");
    const motor = tabela().getByText("Revisão obrigatória pelo motor");
    expect(politica).not.toBe(motor);
    expect(politica.textContent).not.toContain("motor");
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
    await userEvent.click(tabela().getByText("Primeiro plano"));
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

  it("filtros viram parâmetros e chips; 'Limpar filtros' desfaz", async () => {
    const s = espiar();
    render(<TelaRevisao aoSair={vi.fn()} />);
    await screen.findByRole("button", { name: "Pendentes (1)" });

    await userEvent.selectOptions(screen.getByLabelText("Tipo"), "recalculo");
    await userEvent.selectOptions(screen.getByLabelText("Mês no negativo"), "sim");
    await userEvent.click(screen.getByLabelText("Entregue"));
    await userEvent.selectOptions(screen.getByLabelText("Revisor"), "R1");
    await waitFor(() =>
      expect(ultima(s)).toMatchObject({
        tipo: "recalculo",
        mes_negativo: "sim",
        status: ["PLANO_LIBERADO"],
        revisor: "R1",
        pagina: 1,
      }),
    );
    expect(screen.getByRole("button", { name: /Revisor: Rodrigo/ })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Limpar filtros" }));
    await waitFor(() => expect(ultima(s).tipo).toBeUndefined());
    expect(ultima(s).status).toBeUndefined();
    expect(screen.queryByRole("button", { name: "Limpar filtros" })).toBeNull();
  });

  it("a busca espera a pausa na digitação", async () => {
    const s = espiar();
    render(<TelaRevisao aoSair={vi.fn()} />);
    await screen.findByRole("button", { name: "Pendentes (1)" });
    await userEvent.type(screen.getByLabelText("Buscar por nome ou e-mail"), "fula");
    await waitFor(() => expect(ultima(s).q).toBe("fula"));
  });

  it("os filtros ficam guardados na sessão", async () => {
    espiar();
    const { unmount } = render(<TelaRevisao aoSair={vi.fn()} />);
    await screen.findByRole("button", { name: "Pendentes (1)" });
    await userEvent.selectOptions(screen.getByLabelText("Tipo"), "primeiro");
    unmount();

    const s = espiar();
    render(<TelaRevisao aoSair={vi.fn()} />);
    await screen.findByRole("button", { name: "Pendentes (1)" });
    expect(ultima(s).tipo).toBe("primeiro");
  });

  it("cabeçalho ordenável: aria-sort e clique alternam a direção", async () => {
    const s = espiar();
    render(<TelaRevisao aoSair={vi.fn()} />);
    const cab = (await aTabela()).getByRole("columnheader", { name: /Chegou em/ });
    expect(cab).toHaveAttribute("aria-sort", "ascending");
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

  it("vazio: 'Nenhum plano encontrado' com 'Limpar filtros'", async () => {
    espiar(resposta({ itens: [], total: 0 }));
    render(<TelaRevisao aoSair={vi.fn()} />);
    expect(await screen.findByText("Nenhum plano encontrado.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Limpar filtros" })).toBeInTheDocument();
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
