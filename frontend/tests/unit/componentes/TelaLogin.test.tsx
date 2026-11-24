// @vitest-environment happy-dom
/**
 * `TelaLogin` — a primeira tela que quem comprou vê (`RF-50`).
 *
 * `happy-dom`, não `jsdom`: a cadeia de dependências do jsdom quebra neste
 * Node 22.9 (`ERR_REQUIRE_ESM` em `@csstools/css-calc`) — mesma nota de
 * `TelaDefinirSenha.test.tsx`.
 *
 * Queries acessíveis (`getByLabelText`, `getByRole`), nunca seletor por
 * classe. Isso testa a acessibilidade de graça: se o rótulo não estiver
 * associado ao campo, a query falha — e esta tela ganhou layout próprio
 * (`AC-82` isenta a entrada), então é justamente aqui que uma regressão de
 * marcação passaria despercebida.
 *
 * **Os testes de texto apontam para `textosDaEntrada.ts`, não para
 * literais.** A redação é revisada pelo especialista e vai mudar; um teste
 * que repetisse a frase quebraria a cada revisão de copy e ensinaria a
 * equipe a atualizar o teste sem ler o que mudou.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import TelaLogin from "../../../src/telas/TelaLogin";
import {
  ERROS,
  FORMULARIO,
  PROVAS,
  RECUPERACAO,
  RODAPE_SEGURANCA,
  SUBTITULO,
  TITULO,
} from "../../../src/telas/textosDaEntrada";
import * as api from "../../../src/services/api";

function resposta(ok: boolean, corpo: object = {}): Response {
  return { ok, json: async () => corpo } as Response;
}

/** O `401` do revisor na etapa de e-mail (`RF-702`). */
function exigeSenha(): Response {
  return resposta(false, {
    erro: "E-mail ou senha inválidos.",
    exige_senha: true,
  });
}

async function digitarEmailEEntrar(email: string): Promise<void> {
  await userEvent.type(screen.getByLabelText(FORMULARIO.rotuloEmail), email);
  await userEvent.click(
    screen.getByRole("button", { name: FORMULARIO.entrar }),
  );
}

/** Etapa de e-mail ⇒ etapa de senha. O `entrar` já precisa estar simulado. */
async function irParaEtapaDeSenha(email: string): Promise<void> {
  await digitarEmailEEntrar(email);
  await screen.findByLabelText(FORMULARIO.rotuloSenha);
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("TelaLogin", () => {
  // -------------------------------------------------------------------
  // O que a tela afirma antes de pedir o e-mail.
  // -------------------------------------------------------------------

  it("mostra a promessa do produto, não o tamanho do questionário", () => {
    // O motivo da tela existir assim: quem acabou de pagar precisa ver o
    // que ganha. Anunciar quantas perguntas existem é anunciar o preço.
    render(<TelaLogin onEntrou={() => undefined} />);

    const titulo = screen.getByRole("heading", { level: 1 });
    expect(titulo).toHaveTextContent(TITULO.antes.trim());
    expect(titulo).toHaveTextContent(TITULO.destaque);
    expect(screen.getByText(SUBTITULO)).toBeInTheDocument();
  });

  it("não anuncia número de perguntas nem de métodos", () => {
    // Guarda de regressão da decisão de copy: se alguém reintroduzir "177
    // perguntas" ou "3 métodos", este teste cai.
    render(<TelaLogin onEntrou={() => undefined} />);

    const texto = document.body.textContent ?? "";
    expect(texto).not.toMatch(/\d+\s*perguntas/i);
    expect(texto).not.toMatch(/\d+\s*métodos/i);
  });

  it("lista as três respostas do plano", () => {
    render(<TelaLogin onEntrou={() => undefined} />);

    for (const prova of PROVAS) {
      expect(screen.getByText(prova.titulo)).toBeInTheDocument();
      expect(screen.getByText(prova.detalhe)).toBeInTheDocument();
    }
  });

  it("diz a verdade sobre quem vê os dados", () => {
    // A redação anterior dizia "ninguém mais vê o que você respondeu", o
    // que é falso: o plano é conferido por uma pessoa da equipe (`RF-23`).
    // Promessa de sigilo que o produto quebra é pior que nenhuma.
    render(<TelaLogin onEntrou={() => undefined} />);

    expect(screen.getByText(RODAPE_SEGURANCA)).toBeInTheDocument();
    expect(document.body.textContent ?? "").not.toMatch(/ninguém mais vê/i);
  });

  it("tem exatamente um h1 — a tela não usa a casca, e sem ele não há o que anunciar", () => {
    render(<TelaLogin onEntrou={() => undefined} />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("o gráfico de fundo não é anunciado a leitor de tela", () => {
    // Decoração que repete o que o texto ao lado já diz só atrapalha.
    const { container } = render(<TelaLogin onEntrou={() => undefined} />);

    for (const svg of container.querySelectorAll("svg")) {
      expect(svg).toHaveAttribute("aria-hidden", "true");
    }
  });

  // -------------------------------------------------------------------
  // O login em si.
  // -------------------------------------------------------------------

  it("a etapa de e-mail envia só o e-mail; a de senha envia os dois", async () => {
    const login = vi
      .spyOn(api, "entrar")
      .mockResolvedValueOnce(exigeSenha())
      .mockResolvedValueOnce(resposta(true, { e_revisor: true }));
    render(<TelaLogin onEntrou={() => undefined} />);

    await irParaEtapaDeSenha("revisor@exemplo.br");
    expect(login).toHaveBeenNthCalledWith(1, "revisor@exemplo.br");

    await userEvent.type(
      screen.getByLabelText(FORMULARIO.rotuloSenha),
      "senha-secreta",
    );
    await userEvent.click(
      screen.getByRole("button", { name: FORMULARIO.entrar }),
    );

    await waitFor(() =>
      expect(login).toHaveBeenNthCalledWith(
        2,
        "revisor@exemplo.br",
        "senha-secreta",
      ),
    );
  });

  it("o Enter envia a etapa atual — no e-mail e na senha", async () => {
    // Esta tela não usa a casca `Tela`, onde o botão fica FORA do form e
    // precisa de `form={ID}`. Aqui o botão é filho do form — se alguém o
    // mover para fora, o teclado para de funcionar em silêncio, e o
    // teclado é o único caminho de quem não usa mouse.
    const login = vi
      .spyOn(api, "entrar")
      .mockResolvedValueOnce(exigeSenha())
      .mockResolvedValueOnce(resposta(true));
    const recuperacao = vi.spyOn(api, "pedirRecuperacao");
    render(<TelaLogin onEntrou={() => undefined} />);

    await userEvent.type(
      screen.getByLabelText(FORMULARIO.rotuloEmail),
      "revisor@exemplo.br{Enter}",
    );
    await userEvent.type(
      await screen.findByLabelText(FORMULARIO.rotuloSenha),
      "senha-secreta{Enter}",
    );

    await waitFor(() => expect(login).toHaveBeenCalledTimes(2));
    expect(login).toHaveBeenLastCalledWith(
      "revisor@exemplo.br",
      "senha-secreta",
    );
    // "Esqueci minha senha" é `type="button"`: o Enter não o aciona.
    expect(recuperacao).not.toHaveBeenCalled();
  });

  it("sobe a sessão com o papel para o App", async () => {
    // `e_revisor` é dica de interface (`RF-59`, `AC-80`): decide o que
    // oferecer, nunca o que autorizar.
    vi.spyOn(api, "entrar").mockResolvedValue(
      resposta(true, { e_revisor: false }),
    );
    const onEntrou = vi.fn();
    render(<TelaLogin onEntrou={onEntrou} />);

    await digitarEmailEEntrar("aluno@exemplo.br");

    await waitFor(() =>
      expect(onEntrou).toHaveBeenCalledWith({ e_revisor: false }),
    );
  });

  it("entra mesmo quando o corpo da resposta é ilegível", async () => {
    // Corpo quebrado não pode barrar quem tem credencial válida: `null`
    // significa "não sabemos o papel", e o App trata como não-revisor.
    vi.spyOn(api, "entrar").mockResolvedValue({
      ok: true,
      json: async () => {
        throw new Error("sem JSON");
      },
    } as unknown as Response);
    const onEntrou = vi.fn();
    render(<TelaLogin onEntrou={onEntrou} />);

    await digitarEmailEEntrar("aluno@exemplo.br");

    await waitFor(() => expect(onEntrou).toHaveBeenCalledWith(null));
  });

  it("credencial recusada não revela se o e-mail existe", async () => {
    // O servidor devolve 401 sem distinguir os dois casos — deliberado. A
    // mensagem da tela precisa respeitar isso, senão a interface desfaz a
    // proteção do servidor.
    vi.spyOn(api, "entrar").mockResolvedValue(
      resposta(false, { erro: "E-mail ou senha inválidos." }),
    );
    render(<TelaLogin onEntrou={() => undefined} />);

    await digitarEmailEEntrar("naoexiste@exemplo.br");

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(ERROS.credenciais);
    expect(alerta.textContent ?? "").not.toMatch(/não (existe|cadastrad)/i);
  });

  it("rede fora do ar mostra mensagem diferente de credencial errada", async () => {
    // Quem errou a senha tenta outra; quem está sem rede tenta de novo
    // depois. Mensagens iguais mandariam a pessoa para o caminho errado.
    vi.spyOn(api, "entrar").mockRejectedValue(new Error("offline"));
    render(<TelaLogin onEntrou={() => undefined} />);

    await digitarEmailEEntrar("aluno@exemplo.br");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      ERROS.indisponivel,
    );
    expect(ERROS.indisponivel).not.toBe(ERROS.credenciais);
  });

  it("o botão desabilita durante o envio", async () => {
    // Sem isso, dois cliques viram duas requisições de login.
    let liberar: (r: Response) => void = () => undefined;
    vi.spyOn(api, "entrar").mockReturnValue(
      new Promise<Response>((resolve) => {
        liberar = resolve;
      }),
    );
    render(<TelaLogin onEntrou={() => undefined} />);

    await digitarEmailEEntrar("aluno@exemplo.br");

    const botao = await screen.findByRole("button", {
      name: FORMULARIO.entrando,
    });
    expect(botao).toBeDisabled();

    liberar(resposta(true));
    await waitFor(() => expect(screen.getByRole("button")).toBeEnabled());
  });

  it("os campos pedem ao gerenciador de senhas o preenchimento certo", async () => {
    vi.spyOn(api, "entrar").mockResolvedValue(exigeSenha());
    render(<TelaLogin onEntrou={() => undefined} />);

    expect(screen.getByLabelText(FORMULARIO.rotuloEmail)).toHaveAttribute(
      "autocomplete",
      "username",
    );

    await irParaEtapaDeSenha("revisor@exemplo.br");

    const senha = screen.getByLabelText(FORMULARIO.rotuloSenha);
    expect(senha).toHaveAttribute("type", "password");
    expect(senha).toHaveAttribute("autocomplete", "current-password");
  });
  // -------------------------------------------------------------------
  // As duas etapas — `RF-705`, `RF-706`, `RF-707` (T-701).
  // -------------------------------------------------------------------

  it("AC-714: a tela abre só com o e-mail — sem senha e sem 'Esqueci minha senha'", () => {
    render(<TelaLogin onEntrou={() => undefined} />);

    expect(screen.getByLabelText(FORMULARIO.rotuloEmail)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: FORMULARIO.entrar }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(FORMULARIO.rotuloSenha)).toBeNull();
    expect(
      screen.queryByRole("button", { name: FORMULARIO.esqueciSenha }),
    ).toBeNull();
  });

  it("AC-716: 401 com exige_senha abre a etapa de senha com foco, sem erro", async () => {
    vi.spyOn(api, "entrar").mockResolvedValue(exigeSenha());
    render(<TelaLogin onEntrou={() => undefined} />);

    await irParaEtapaDeSenha("revisor@exemplo.br");

    await waitFor(() =>
      expect(screen.getByLabelText(FORMULARIO.rotuloSenha)).toHaveFocus(),
    );
    expect(
      screen.getByRole("button", { name: FORMULARIO.esqueciSenha }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(FORMULARIO.rotuloEmail)).toHaveValue(
      "revisor@exemplo.br",
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("AC-717: 401 sem exige_senha mostra a mensagem genérica e não pede senha", async () => {
    vi.spyOn(api, "entrar").mockResolvedValue(
      resposta(false, { erro: "E-mail ou senha inválidos." }),
    );
    render(<TelaLogin onEntrou={() => undefined} />);

    await digitarEmailEEntrar("naoexiste@exemplo.br");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      ERROS.credenciais,
    );
    expect(screen.queryByLabelText(FORMULARIO.rotuloSenha)).toBeNull();
  });

  it("AC-717: 401 com corpo ilegível é tratado como sem exige_senha", async () => {
    // Lado seguro: na dúvida, não revelar que a conta é de revisor.
    vi.spyOn(api, "entrar").mockResolvedValue({
      ok: false,
      json: async () => {
        throw new Error("sem JSON");
      },
    } as unknown as Response);
    render(<TelaLogin onEntrou={() => undefined} />);

    await digitarEmailEEntrar("revisor@exemplo.br");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      ERROS.credenciais,
    );
    expect(screen.queryByLabelText(FORMULARIO.rotuloSenha)).toBeNull();
  });

  it("AC-718: editar o e-mail na etapa de senha volta à etapa de e-mail", async () => {
    vi.spyOn(api, "entrar").mockResolvedValue(exigeSenha());
    render(<TelaLogin onEntrou={() => undefined} />);

    await irParaEtapaDeSenha("revisor@exemplo.br");
    await userEvent.type(
      screen.getByLabelText(FORMULARIO.rotuloEmail),
      "x",
    );

    expect(screen.queryByLabelText(FORMULARIO.rotuloSenha)).toBeNull();
    expect(
      screen.queryByRole("button", { name: FORMULARIO.esqueciSenha }),
    ).toBeNull();
  });

  it("AC-719: senha recusada mostra o erro e mantém o campo de senha", async () => {
    vi.spyOn(api, "entrar").mockResolvedValue(exigeSenha());
    render(<TelaLogin onEntrou={() => undefined} />);

    await irParaEtapaDeSenha("revisor@exemplo.br");
    await userEvent.type(
      screen.getByLabelText(FORMULARIO.rotuloSenha),
      "errada",
    );
    await userEvent.click(
      screen.getByRole("button", { name: FORMULARIO.entrar }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      ERROS.credenciais,
    );
    expect(screen.getByLabelText(FORMULARIO.rotuloSenha)).toBeInTheDocument();
  });

  it("AC-719: senha aceita entra com o papel de revisor", async () => {
    vi.spyOn(api, "entrar")
      .mockResolvedValueOnce(exigeSenha())
      .mockResolvedValueOnce(resposta(true, { e_revisor: true }));
    const onEntrou = vi.fn();
    render(<TelaLogin onEntrou={onEntrou} />);

    await irParaEtapaDeSenha("revisor@exemplo.br");
    await userEvent.type(
      screen.getByLabelText(FORMULARIO.rotuloSenha),
      "certa",
    );
    await userEvent.click(
      screen.getByRole("button", { name: FORMULARIO.entrar }),
    );

    await waitFor(() =>
      expect(onEntrou).toHaveBeenCalledWith({ e_revisor: true }),
    );
  });

  it("AC-720: 'Esqueci minha senha' pede o link, confirma e não abre sessão", async () => {
    const login = vi.spyOn(api, "entrar").mockResolvedValue(exigeSenha());
    const recuperacao = vi
      .spyOn(api, "pedirRecuperacao")
      .mockResolvedValue(resposta(true, { pedido_registrado: true }));
    const onEntrou = vi.fn();
    render(<TelaLogin onEntrou={onEntrou} />);

    await irParaEtapaDeSenha("revisor@exemplo.br");
    await userEvent.click(
      screen.getByRole("button", { name: FORMULARIO.esqueciSenha }),
    );

    expect(await screen.findByRole("status")).toHaveTextContent(
      RECUPERACAO.enviada("revisor@exemplo.br"),
    );
    expect(recuperacao).toHaveBeenCalledWith("revisor@exemplo.br");
    expect(onEntrou).not.toHaveBeenCalled();
    // `type="button"`: o clique não submete o formulário.
    expect(login).toHaveBeenCalledOnce();
  });

  it("EC-712: rede fora no login da etapa de senha mantém a etapa", async () => {
    vi.spyOn(api, "entrar")
      .mockResolvedValueOnce(exigeSenha())
      .mockRejectedValueOnce(new Error("offline"));
    render(<TelaLogin onEntrou={() => undefined} />);

    await irParaEtapaDeSenha("revisor@exemplo.br");
    await userEvent.type(
      screen.getByLabelText(FORMULARIO.rotuloSenha),
      "senha",
    );
    await userEvent.click(
      screen.getByRole("button", { name: FORMULARIO.entrar }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      ERROS.indisponivel,
    );
    expect(screen.getByLabelText(FORMULARIO.rotuloSenha)).toBeInTheDocument();
  });

  it("EC-712: recuperação sem rede ou recusada mostra indisponível e mantém a etapa", async () => {
    vi.spyOn(api, "entrar").mockResolvedValue(exigeSenha());
    vi.spyOn(api, "pedirRecuperacao")
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(resposta(false));
    render(<TelaLogin onEntrou={() => undefined} />);

    await irParaEtapaDeSenha("revisor@exemplo.br");
    const esqueci = screen.getByRole("button", {
      name: FORMULARIO.esqueciSenha,
    });

    await userEvent.click(esqueci);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      ERROS.indisponivel,
    );

    await userEvent.click(esqueci);
    await waitFor(() => expect(esqueci).toBeEnabled());
    expect(screen.getByRole("alert")).toHaveTextContent(ERROS.indisponivel);
    expect(screen.queryByRole("status")).toBeNull();
    expect(screen.getByLabelText(FORMULARIO.rotuloSenha)).toBeInTheDocument();
  });

  it("durante o envio, 'Entrar' e 'Esqueci minha senha' ficam desabilitados", async () => {
    let liberar: (r: Response) => void = () => undefined;
    vi.spyOn(api, "entrar").mockResolvedValue(exigeSenha());
    vi.spyOn(api, "pedirRecuperacao").mockReturnValue(
      new Promise<Response>((resolve) => {
        liberar = resolve;
      }),
    );
    render(<TelaLogin onEntrou={() => undefined} />);

    await irParaEtapaDeSenha("revisor@exemplo.br");
    const esqueci = screen.getByRole("button", {
      name: FORMULARIO.esqueciSenha,
    });
    await userEvent.click(esqueci);

    expect(
      screen.getByRole("button", { name: FORMULARIO.entrando }),
    ).toBeDisabled();
    expect(esqueci).toBeDisabled();

    liberar(resposta(true));
    await waitFor(() => expect(esqueci).toBeEnabled());
  });
});
