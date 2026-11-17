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
 * Não grava e **não calcula nem formata valor financeiro** (Lei nº 3): mostra o
 * que o servidor devolveu e entrega a escolha ao pai por `aoConfirmar`. Os
 * rótulos de `TEXTOS` são sugestão, a validar com o especialista (`T-681`).
 */
import { useEffect, useRef, useState } from "react";

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
  meses: "meses",
} as const;

const RECALCULAR: Readonly<Record<CampoDaDivida, string>> = {
  SALDO: "Recalcular o saldo",
  PARCELA: "Recalcular a parcela",
  TAXA: "Recalcular a taxa",
  PRAZO: "Recalcular o prazo",
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
  previa,
  gravando,
  erroAoSalvar,
  aoConfirmar,
  aoVoltar,
}: DivergenciaDaDividaProps) {
  const dialogo = useRef<HTMLDialogElement>(null);
  /** `null` = "Manter" (`OQ-105`). */
  const [escolha, setEscolha] = useState<CampoDaDivida | null>(null);

  // A guarda cobre o efeito rodando duas vezes (StrictMode): `showModal()` num
  // diálogo já aberto lança.
  useEffect(() => {
    const dialog = dialogo.current;
    if (dialog && !dialog.open) dialog.showModal();
  }, []);

  const hipotese = previa.hipotese_conservadora;
  const podeConfirmar = !gravando;

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
              type="radio"
              name="divergencia-recalcular"
              className="h-[26px] w-[26px] accent-accent"
              checked={escolha === null}
              onChange={() => setEscolha(null)}
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
                onChange={() => setEscolha(campo)}
              />
              <span>{RECALCULAR[campo]}</span>
            </label>
          ))}
        </fieldset>

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
