/**
 * O popup da divergência da dívida — os quatro valores não batem e o aluno
 * decide ao clicar "Continuar" (`RF-566`; `T-682`).
 *
 * **`<dialog>` nativo aberto por `showModal()`**, sem biblioteca (`PD-19`): o
 * navegador prende o foco, deixa o fundo inerte, fecha no Esc e dispara
 * `close`. O popup só existe montado enquanto está aberto (`PD-20`): a opção
 * marcada morre ao fechar, e o próximo "Continuar" reabre com "Manter" marcada
 * sem código de reset (`OQ-105`, `EC-100`). O único caminho de "fechar sem
 * salvar" é o `close` do `<dialog>` (`PD-21`): Esc, "Voltar e corrigir" e o
 * navegador caem todos em `aoVoltar`.
 *
 * Marcar "Recalcular o …" pede ao servidor a prévia com esse recálculo
 * (`RF-567`; `T-683`); trocar de opção aborta o pedido anterior, e o resultado
 * só vale para a opção que o pediu — a mesma técnica do `resultado.corpo ===
 * corpo` da página.
 *
 * Não grava e **não calcula nem formata valor financeiro** (Lei nº 3): mostra o
 * que o servidor devolveu e entrega a escolha ao pai por `aoConfirmar`. Os
 * rótulos de `TEXTOS` são sugestão, a validar com o especialista (`T-681`).
 */
import { useEffect, useRef, useState } from "react";

import { ErroHttp, preverCalculadora } from "../services/api";
import type {
  CampoDaDivida,
  CorpoDaCalculadora,
  RespostaDaPrevia,
} from "../tipos";
import Botao from "./Botao";

const TEXTOS = {
  titulo: "Os valores desta dívida não batem",
  parcelaSeria: "Com esse saldo, taxa e prazo, a parcela seria",
  voceInformou: "Você informou",
  escolhaDoRecalculo: "Qual informação recalcular?",
  manterOriginais: "Manter os valores que informei",
  saldo: "Saldo",
  taxa: "Taxa",
  confirmar: "Confirmar e continuar",
  salvando: "Salvando…",
  voltar: "Voltar e corrigir",
  falhaDeRede: "Não foi possível calcular.",
  meses: "meses",
} as const;

const RECALCULAR: Readonly<Record<CampoDaDivida, string>> = {
  SALDO: "Recalcular o saldo",
  PARCELA: "Recalcular a parcela",
  TAXA: "Recalcular a taxa",
  PRAZO: "Recalcular o prazo",
};

const RECALCULADO: Readonly<Record<CampoDaDivida, string>> = {
  SALDO: "Saldo recalculado",
  PARCELA: "Parcela recalculada",
  TAXA: "Taxa recalculada",
  PRAZO: "Prazo recalculado",
};

/** Valor do servidor pronto para a frase: o prazo ganha " meses"; o resto vai como veio (`PD-25`). */
export function textoDoValor(campo: CampoDaDivida, texto: string): string {
  return campo === "PRAZO" ? `${texto} ${TEXTOS.meses}` : texto;
}

export interface DivergenciaDaDividaProps {
  casoId: string;
  /** Os quatro valores como digitados, com `recalcular: null` (o corpo que gerou `previa`). */
  corpo: CorpoDaCalculadora;
  /** A prévia `INCOMPATIVEL` que abriu o popup. Abrir não chama o servidor. */
  previa: RespostaDaPrevia;
  gravando: boolean;
  /** `EC-105`: falha ao salvar aparece aqui dentro, com o popup aberto. */
  erroAoSalvar: string | null;
  /** "Confirmar e continuar": `null` = "Manter os valores que informei". */
  aoConfirmar: (recalcular: CampoDaDivida | null) => void;
  /** Evento `close` do `<dialog>`: Esc, "Voltar e corrigir" ou o navegador (`PD-21`). */
  aoVoltar: () => void;
}

export default function DivergenciaDaDivida({
  casoId,
  corpo,
  previa,
  gravando,
  erroAoSalvar,
  aoConfirmar,
  aoVoltar,
}: DivergenciaDaDividaProps) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const radioManter = useRef<HTMLInputElement>(null);
  /** `null` = "Manter" (`OQ-105`). */
  const [escolha, setEscolha] = useState<CampoDaDivida | null>(null);
  const [recalculo, setRecalculo] = useState<{
    campo: CampoDaDivida;
    previa?: RespostaDaPrevia;
    falha?: string;
  } | null>(null);

  // A guarda cobre o efeito rodando duas vezes (StrictMode): `showModal()` num
  // diálogo já aberto lança. O foco vai a "Manter" à mão: o Chrome trata o
  // `div` que rola como focável e o `showModal()` o escolheria antes.
  useEffect(() => {
    const dialog = dialogo.current;
    if (dialog && !dialog.open) dialog.showModal();
    radioManter.current?.focus();
  }, []);

  // "Manter" não chama o servidor.
  useEffect(() => {
    if (escolha === null) return;
    const controle = new AbortController();
    preverCalculadora(casoId, { ...corpo, recalcular: escolha }, controle.signal)
      .then((resposta) => {
        if (!controle.signal.aborted)
          setRecalculo({ campo: escolha, previa: resposta });
      })
      .catch((erro: unknown) => {
        if (controle.signal.aborted) return;
        setRecalculo({
          campo: escolha,
          falha:
            erro instanceof ErroHttp && erro.message
              ? erro.message
              : TEXTOS.falhaDeRede,
        });
      });
    return () => controle.abort();
  }, [casoId, corpo, escolha]);

  function marcar(campo: CampoDaDivida | null) {
    setEscolha(campo);
    setRecalculo(null);
  }

  const hipotese = previa.hipotese_conservadora;
  const atual = recalculo?.campo === escolha ? recalculo : null;
  const recalculada =
    atual?.previa?.estado === "CALCULADO" && escolha !== null
      ? atual.previa.valores[escolha]
      : undefined;
  const mensagemDeErro =
    atual?.previa?.estado === "ERRO" ? atual.previa.mensagem : atual?.falha;
  // Com uma opção de recálculo marcada, só confirma com o valor dela na tela.
  const podeConfirmar =
    !gravando && (escolha === null || recalculada !== undefined);

  return (
    <dialog
      ref={dialogo}
      aria-labelledby="divergencia-titulo"
      onClose={aoVoltar}
      className="w-[calc(100%-2rem)] max-w-lg border-0 bg-transparent p-0 backdrop:bg-ink/40"
    >
      <div className="cartao max-h-[calc(100dvh-2rem)] overflow-y-auto">
        <h2
          id="divergencia-titulo"
          className="m-0 font-serif text-[1.3rem] font-semibold"
        >
          {TEXTOS.titulo}
        </h2>
        <p className="aviso-atencao">
          {TEXTOS.parcelaSeria} {previa.teorico?.texto}. {TEXTOS.voceInformou}{" "}
          {previa.valores.PARCELA?.texto}.
        </p>

        <fieldset className="flex flex-col gap-2 border-0 p-0">
          <legend className="sr-only">{TEXTOS.escolhaDoRecalculo}</legend>
          <label className="opt">
            <input
              ref={radioManter}
              type="radio"
              name="divergencia-recalcular"
              className="h-[26px] w-[26px] accent-accent"
              checked={escolha === null}
              onChange={() => marcar(null)}
            />
            <span>{TEXTOS.manterOriginais}</span>
          </label>
          {hipotese && (
            // `RF-538`/`RF-539`: só saldo e taxa da hipótese, como o servidor devolve.
            <div className="flex flex-col gap-1">
              <p className="m-0 tabular-nums">
                {TEXTOS.saldo}: {hipotese.saldo} · {TEXTOS.taxa}:{" "}
                {hipotese.taxa} ({hipotese.rotulo})
              </p>
              <p className="nota m-0">{hipotese.aviso}</p>
            </div>
          )}
          {previa.alternativas.map((campo) => (
            <label key={campo} className="opt">
              <input
                type="radio"
                name="divergencia-recalcular"
                className="h-[26px] w-[26px] accent-accent"
                checked={escolha === campo}
                onChange={() => marcar(campo)}
              />
              <span>{RECALCULAR[campo]}</span>
            </label>
          ))}
        </fieldset>

        <div role="status">
          {escolha !== null && recalculada && (
            <p className="m-0 tabular-nums">
              {RECALCULADO[escolha]}: {textoDoValor(escolha, recalculada.texto)}{" "}
              ({recalculada.rotulo})
            </p>
          )}
        </div>
        {mensagemDeErro && (
          <p role="alert" className="aviso-erro">
            {mensagemDeErro}
          </p>
        )}

        {erroAoSalvar && (
          <p role="alert" className="aviso-erro">
            {erroAoSalvar}
          </p>
        )}

        <div className="flex flex-col gap-2">
          <Botao onClick={() => aoConfirmar(escolha)} disabled={!podeConfirmar}>
            {gravando ? TEXTOS.salvando : TEXTOS.confirmar}
          </Botao>
          <Botao variante="secundario" onClick={() => dialogo.current?.close()}>
            {TEXTOS.voltar}
          </Botao>
        </div>
      </div>
    </dialog>
  );
}
