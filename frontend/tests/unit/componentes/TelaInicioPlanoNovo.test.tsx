// @vitest-environment happy-dom
/**
 * `T-342` (`RF-118`) — com plano liberado e o caso de volta à coleta, o plano
 * atual continua à vista e a tela diz por quê.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import TelaInicio from "../../../src/telas/TelaInicio";
import * as api from "../../../src/services/api";
import type { Inicio } from "../../../src/tipos";

afterEach(() => {
  vi.restoreAllMocks();
});

function inicio(extra: Partial<Inicio>): Inicio {
  return {
    CASO_ID: "CASO-1",
    estado: "COLETA_INICIAL",
    fase: "coleta",
    mensagem: "Sua coleta está em andamento.",
    proxima_etapa: { destino: "calculando", ID_PERGUNTA: null, item_id: null },
    progresso: { respondidas: 337, total: 337 },
    valor_em_destaque: null,
    plano_liberado: true,
    versao_do_plano: 1,
    correcao_pedida: null,
    ...extra,
  } as Inicio;
}

const renderizar = (i: Inicio, irPara = vi.fn()) => {
  render(
    <TelaInicio inicio={i} irPara={irPara} eRevisor={false} aoSair={vi.fn()} />,
  );
  return irPara;
};

describe("Início — plano novo depois da liberação", () => {
  it('em coleta COM plano liberado: "Ver meu plano" continua e a nota explica', () => {
    renderizar(inicio({}));

    expect(
      screen.getByRole("button", { name: "Ver meu plano" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Seu plano atual continua disponível."),
    ).toBeInTheDocument();
  });

  it("primeira coleta (sem plano liberado): nada disso aparece", () => {
    renderizar(inicio({ plano_liberado: false, versao_do_plano: null }));

    expect(
      screen.queryByRole("button", { name: "Ver meu plano" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Seu plano atual continua disponível."),
    ).not.toBeInTheDocument();
  });
});

describe("Início — plano entregue é definitivo (RF-401, RF-409, T-388)", () => {
  // O que o servidor devolve hoje para PLANO_LIBERADO: fase "plano", destino
  // "plano", sem refazer. `valor_em_destaque` ainda vem preenchido.
  const ENTREGUE = {
    estado: "PLANO_LIBERADO",
    fase: "plano",
    mensagem: "Seu plano está liberado.",
    proxima_etapa: { destino: "plano", ID_PERGUNTA: null, item_id: null },
    valor_em_destaque: "3000.00",
  } as const;

  it("com a fase plano: só o plano, sem acompanhamento, refazer ou decisão do ataque", () => {
    const irPara = renderizar(inicio(ENTREGUE));

    const botao = screen.getByRole("button", { name: "Ver o seu plano" });
    expect(botao).toBeInTheDocument();
    fireEvent.click(botao);
    expect(irPara).toHaveBeenCalledWith({ tela: "plano" });

    // Nada de plano novo, de decisão sobre o ataque, de valor em destaque nem
    // de acompanhamento (nem como botão, nem como etapa da trilha).
    expect(screen.queryByText(/novo plano|plano novo/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Decidir sobre/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/R\$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/acompanhamento/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/ver o que fazer agora/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/conte como foi/i)).not.toBeInTheDocument();
    expect(screen.getAllByRole("button").map((b) => b.textContent)).toEqual([
      "Sair",
      "Ver o seu plano",
      "Ver e editar minhas respostas",
    ]);
  });

  it("um destino pós-plano que o servidor ainda mandasse cai no plano", () => {
    const irPara = renderizar(
      inicio({
        ...ENTREGUE,
        proxima_etapa: { destino: "bloco10" as never, ID_PERGUNTA: null, item_id: null },
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Ver o seu plano" }));
    expect(irPara).toHaveBeenCalledWith({ tela: "plano" });
  });
});

describe('Início — "Quero editar minhas respostas" em conferência (AC-187)', () => {
  const EM_CONFERENCIA = {
    estado: "AGUARDANDO_REVISAO",
    fase: "revisao",
    mensagem: "Seu plano está em revisão.",
    proxima_etapa: { destino: "aguardando", ID_PERGUNTA: null, item_id: null },
    plano_liberado: false,
    versao_do_plano: null,
    pode_retomar_edicao: true,
  } as const;

  it('oferece a retirada, confirma e leva a "Minhas respostas"', async () => {
    const retomar = vi
      .spyOn(api, "retomarEdicao")
      .mockResolvedValue({ estado: "COLETA_INICIAL" });
    const irPara = renderizar(inicio(EM_CONFERENCIA));

    fireEvent.click(
      screen.getByRole("button", { name: "Quero editar minhas respostas" }),
    );
    expect(
      screen.getByText(
        "Seu plano sai da conferência. Quando você enviar de novo, ele volta para a fila.",
      ),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Retirar o plano e editar" }),
    );

    await vi.waitFor(() =>
      expect(irPara).toHaveBeenCalledWith({ tela: "respostas" }),
    );
    expect(retomar).toHaveBeenCalledWith("CASO-1");
  });

  it("fora da conferência a ação não existe", () => {
    renderizar(inicio({}));
    expect(
      screen.queryByRole("button", { name: "Quero editar minhas respostas" }),
    ).not.toBeInTheDocument();
  });
});
