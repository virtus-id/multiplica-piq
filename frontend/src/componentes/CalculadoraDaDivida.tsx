/**
 * A calculadora da dívida — saldo, parcela, taxa e prazo (`RF-514`, `RF-519`,
 * `RF-522`, `RF-523`, `RF-524`, `RF-525`, `RF-526`, `RF-529`, `RF-530`; `T-511`,
 * `T-512`).
 *
 * **Este componente não calcula nem formata valor financeiro** (Lei nº 3): ele
 * manda o texto digitado, na grafia brasileira, e mostra o que o servidor
 * devolve. O resultado da prévia vive só aqui, em estado local: apagado a cada
 * edição, a cada erro e ao desmontar — nunca fica o valor antigo na tela
 * (`AC-529`). Campo que o sistema calculou volta como "não sei" ao reabrir; o
 * valor calculado nunca é reenviado como se fosse digitado (`RF-520`).
 *
 * A prévia espera ~400 ms depois da última edição, cancela a anterior
 * (`AbortController`) e descarta resposta fora de ordem.
 *
 * **Conferência silenciosa** (`RF-564`; `T-685`): a prévia não é desenhada
 * como painel. Abaixo dos campos ficam só a linha de erro (`RF-518`,
 * `RF-519`, falha de rede) e, abaixo de cada campo, a linha marcada do valor
 * que o servidor calculou ou estimou (`RF-568`) — nunca dentro do campo.
 * "Continuar" decide pela prévia que já está na tela (`RF-565`, `PD-22`):
 * `INCOMPATIVEL` abre o popup da divergência sem salvar; qualquer outro estado
 * sem erro salva direto (`T-686`).
 *
 * Os textos de cada campo (enunciados, "ao mês"/"ao ano", Price/SAC) vêm das
 * perguntas individuais do registro, lidas ao abrir — o mesmo caminho que traz
 * o que o aluno já gravou. Os rótulos de `TEXTOS` abaixo são provisórios.
 */
import { useEffect, useMemo, useState } from "react";

import {
  aplicarMascara,
  formatarDecimalDoServidor,
  formatarTaxaDoServidor,
} from "../mascaras";
import {
  confirmarCalculadora,
  obterPergunta,
  preverCalculadora,
} from "../services/api";
import type {
  CampoDaDivida,
  ConfirmacaoDaCalculadora,
  CorpoDaCalculadora,
  ExplicacaoDoCampo,
  PeriodicidadeDaTaxa,
  Pergunta,
  RespostaDaPrevia,
  SistemaDaDivida,
  TipoResposta,
} from "../tipos";
import Botao from "./Botao";
import DivergenciaDaDivida, { textoDoValor } from "./DivergenciaDaDivida";
import Explicacao from "./Explicacao";

/** Espera depois da última edição antes de pedir a prévia. */
export const ESPERA_DA_PREVIA_MS = 400;

// Provisórios: a redação aprovada é `T-507`/`T-509`. Texto que o servidor já
// devolve (mensagens, rótulo de marca, valores) nunca é escrito aqui.
const TEXTOS = {
  naoSei: "Não sei",
  falhaAoCarregar: "Não foi possível carregar a pergunta.",
  falhaAoSalvar: "Não foi possível salvar.",
  falhaDeRede: "Não foi possível calcular.",
  calculando: "Calculando…",
  calculado: "Calculado:",
  estimada: "Estimada:",
  hipoteseDe24Meses: "(hipótese de 24 meses)",
} as const;

const NOMES: Readonly<Record<CampoDaDivida, string>> = {
  SALDO: "Saldo devedor",
  PARCELA: "Parcela",
  TAXA: "Taxa",
  PRAZO: "Prazo",
};

const CAMPOS: readonly CampoDaDivida[] = ["SALDO", "PARCELA", "TAXA", "PRAZO"];

const MASCARA: Readonly<Record<CampoDaDivida, TipoResposta>> = {
  SALDO: "MOEDA",
  PARCELA: "MOEDA",
  TAXA: "TAXA",
  PRAZO: "NUMERO",
};

// As perguntas individuais que a composta resume (`B5.CALC01`, `T-492`).
const PERGUNTA_DO_CAMPO: Readonly<Record<CampoDaDivida, string>> = {
  SALDO: "B5.B03",
  PARCELA: "B5.C02",
  TAXA: "B5.D06",
  PRAZO: "B5.C02B",
};
const PERGUNTA_DO_SISTEMA = "B5.C02A";

interface EstadoDoCampo {
  texto: string;
  naoSei: boolean;
}
type Campos = Record<CampoDaDivida, EstadoDoCampo>;

const CAMPOS_EM_BRANCO: Campos = {
  SALDO: { texto: "", naoSei: false },
  PARCELA: { texto: "", naoSei: false },
  TAXA: { texto: "", naoSei: false },
  PRAZO: { texto: "", naoSei: false },
};

interface Inicial {
  campos: Campos;
  sistema: SistemaDaDivida;
  periodicidade: PeriodicidadeDaTaxa;
  enunciados: Partial<Record<CampoDaDivida, string>>;
  /** `RF-562`: o conteúdo do ícone ⓘ de cada campo — mesmo texto da tela de pergunta. */
  explicacoes: Partial<Record<CampoDaDivida, ExplicacaoDoCampo>>;
  /** O rótulo de cada opção do servidor, pelo `valor_interno`. */
  rotulosDoSistema: Partial<Record<SistemaDaDivida, string>>;
  rotulosDaPeriodicidade: Partial<Record<PeriodicidadeDaTaxa, string>>;
  enunciadoDoSistema: string | null;
  enunciadoDaPeriodicidade: string | null;
}

function rotulosDe(pergunta: Pergunta): Record<string, string> {
  const rotulos: Record<string, string> = {};
  for (const opcao of pergunta.opcoes) {
    if (opcao.valor_interno !== null)
      rotulos[opcao.valor_interno] = opcao.rotulo;
  }
  return rotulos;
}

/** O que o aluno já gravou, lido pelas perguntas individuais (`RF-526`, `EC-70`). */
async function carregarInicial(
  casoId: string,
  itemId: string | undefined,
  sistemaPadrao: SistemaDaDivida,
): Promise<Inicial> {
  const ler = async (id: string) =>
    (await obterPergunta(casoId, id, itemId)).pergunta;
  const [saldo, parcela, taxa, prazo, sistema] = await Promise.all([
    ler(PERGUNTA_DO_CAMPO.SALDO),
    ler(PERGUNTA_DO_CAMPO.PARCELA),
    ler(PERGUNTA_DO_CAMPO.TAXA),
    ler(PERGUNTA_DO_CAMPO.PRAZO),
    ler(PERGUNTA_DO_SISTEMA),
  ]);
  const texto = (
    p: Pergunta | null,
    formatar: (v: string | null) => string,
  ): EstadoDoCampo => ({
    texto:
      p && !p.respondida_como_nao_sei && typeof p.valor_atual === "string"
        ? formatar(p.valor_atual)
        : "",
    naoSei: p?.respondida_como_nao_sei ?? false,
  });
  const periodicidade =
    typeof taxa?.valor_atual === "string" ? taxa.valor_atual : null;
  const rotulosDaPeriodicidade = taxa ? rotulosDe(taxa) : {};
  const rotulosDoSistema = sistema ? rotulosDe(sistema) : {};
  return {
    campos: {
      SALDO: texto(saldo, formatarDecimalDoServidor),
      PARCELA: texto(parcela, formatarDecimalDoServidor),
      TAXA: {
        texto: formatarTaxaDoServidor(
          typeof taxa?.valor_do_campo === "string" ? taxa.valor_do_campo : null,
        ),
        naoSei: periodicidade === "DESCONHECIDA",
      },
      PRAZO: texto(prazo, (v) => v ?? ""),
    },
    sistema: sistema?.valor_atual === "SAC" ? "SAC" : sistemaPadrao,
    periodicidade: periodicidade === "ANUAL" ? "ANUAL" : "MENSAL",
    enunciados: {
      SALDO: saldo?.enunciado,
      PARCELA: parcela?.enunciado,
      PRAZO: prazo?.enunciado,
    },
    explicacoes: {
      ...(saldo?.explicacao ? { SALDO: saldo.explicacao } : {}),
      ...(parcela?.explicacao ? { PARCELA: parcela.explicacao } : {}),
      ...(taxa?.explicacao ? { TAXA: taxa.explicacao } : {}),
      ...(prazo?.explicacao ? { PRAZO: prazo.explicacao } : {}),
    },
    rotulosDoSistema: {
      PRICE: rotulosDoSistema.PRICE,
      SAC: rotulosDoSistema.SAC,
    },
    rotulosDaPeriodicidade: {
      MENSAL: rotulosDaPeriodicidade.MENSAL,
      ANUAL: rotulosDaPeriodicidade.ANUAL,
    },
    enunciadoDoSistema: sistema?.enunciado ?? null,
    enunciadoDaPeriodicidade: taxa?.enunciado ?? null,
  };
}

/**
 * `RF-568`: a linha marcada abaixo do campo, derivada da prévia do `corpo`
 * atual (`PD-24`) — editou, a prévia deixa de valer e a linha some no mesmo
 * render. O texto longo da hipótese de 24 meses não é exibido (`OQ-107`).
 */
function linhaDoCampo(
  campo: CampoDaDivida,
  previa: RespostaDaPrevia | null,
): string | null {
  if (!previa || previa.estado === "ERRO") return null;
  const valor = previa.valores[campo];
  if (previa.estado === "CALCULADO" && previa.campo_calculado === campo && valor)
    return `${TEXTOS.calculado} ${textoDoValor(campo, valor.texto)}`;
  if (campo === "PARCELA" && previa.parcela_estimada)
    return `${TEXTOS.estimada} ${previa.parcela_estimada.texto} ${TEXTOS.hipoteseDe24Meses}`;
  return null;
}

interface CalculadoraDaDividaProps {
  casoId: string;
  /** A pergunta composta (`CALCULO_DIVIDA`); `item_id` é a dívida. */
  pergunta: Pergunta;
  aoConfirmar: (confirmacao: ConfirmacaoDaCalculadora) => void;
  /** Qualquer edição: o aviso de gravação anterior não vale mais. */
  aoEditar?: () => void;
  rotuloConfirmar?: string;
}

export default function CalculadoraDaDivida({
  casoId,
  pergunta,
  aoConfirmar,
  aoEditar,
  rotuloConfirmar = "Continuar",
}: CalculadoraDaDividaProps) {
  const [inicial, setInicial] = useState<Inicial | null>(null);
  const [erroDeCarga, setErroDeCarga] = useState<string | null>(null);
  const [campos, setCampos] = useState<Campos>(CAMPOS_EM_BRANCO);
  const [sistema, setSistema] = useState<SistemaDaDivida>(
    pergunta.sistema ?? "PRICE",
  );
  const [periodicidade, setPeriodicidade] =
    useState<PeriodicidadeDaTaxa>("MENSAL");
  /** O resultado vale só para o `corpo` que o pediu: editou, deixa de valer na hora (`AC-529`). */
  const [resultado, setResultado] = useState<{
    corpo: CorpoDaCalculadora;
    previa?: RespostaDaPrevia;
    falha?: string;
  } | null>(null);
  const [gravando, setGravando] = useState(false);
  const [erroAoSalvar, setErroAoSalvar] = useState<string | null>(null);
  /** Montado só enquanto aberto: fechar descarta a opção marcada (`PD-20`). */
  const [divergenciaAberta, setDivergenciaAberta] = useState(false);

  const itemId = pergunta.item_id ?? undefined;
  const sistemaPadrao = pergunta.sistema ?? "PRICE";
  useEffect(() => {
    const controle = new AbortController();
    carregarInicial(casoId, itemId, sistemaPadrao)
      .then((dados) => {
        if (controle.signal.aborted) return;
        setInicial(dados);
        setCampos(dados.campos);
        setSistema(dados.sistema);
        setPeriodicidade(dados.periodicidade);
      })
      .catch(() => {
        if (!controle.signal.aborted) setErroDeCarga(TEXTOS.falhaAoCarregar);
      });
    return () => controle.abort();
  }, [casoId, itemId, sistemaPadrao]);

  // `null` = desconhecido: "não sei" ou em branco. O campo "a calcular" nunca
  // leva o valor que o servidor calculou (risco 9). A prévia da página nunca
  // pede recálculo: a escolha é feita no popup da divergência.
  const corpo: CorpoDaCalculadora = useMemo(() => {
    const valor = (campo: CampoDaDivida) =>
      campos[campo].naoSei || campos[campo].texto === ""
        ? null
        : campos[campo].texto;
    return {
      sistema,
      periodicidade,
      saldo: valor("SALDO"),
      parcela: valor("PARCELA"),
      taxa: valor("TAXA"),
      prazo: valor("PRAZO"),
      recalcular: null,
    };
  }, [campos, sistema, periodicidade]);

  useEffect(() => {
    if (!inicial) return;
    const controle = new AbortController();
    const espera = setTimeout(() => {
      preverCalculadora(casoId, corpo, controle.signal)
        .then((previa) => {
          if (controle.signal.aborted) return;
          setResultado({ corpo, previa });
        })
        .catch((erro: unknown) => {
          if (controle.signal.aborted) return;
          const falha =
            erro instanceof Error && erro.message
              ? erro.message
              : TEXTOS.falhaDeRede;
          setResultado({ corpo, falha });
        });
    }, ESPERA_DA_PREVIA_MS);
    return () => {
      clearTimeout(espera);
      controle.abort();
    };
  }, [casoId, inicial, corpo]);

  function editou() {
    setErroAoSalvar(null);
    aoEditar?.();
  }

  function mudarCampo(campo: CampoDaDivida, novo: EstadoDoCampo) {
    editou();
    setCampos((atual) => ({ ...atual, [campo]: novo }));
  }

  function mudarPremissa(mudanca: () => void) {
    editou();
    mudanca();
  }

  /** `recalcular` = a escolha do popup; `null` = salvar os quatro como digitados. */
  async function confirmar(recalcular: CampoDaDivida | null) {
    if (pergunta.item_id === null) return;
    setGravando(true);
    setErroAoSalvar(null);
    try {
      const confirmacao = await confirmarCalculadora(casoId, pergunta.item_id, {
        ...corpo,
        recalcular,
      });
      // Desmontar o `<dialog>` aberto não dispara `close` (`PD-21`).
      setDivergenciaAberta(false);
      aoConfirmar(confirmacao);
    } catch (erro) {
      setErroAoSalvar(
        erro instanceof Error && erro.message
          ? erro.message
          : TEXTOS.falhaAoSalvar,
      );
    } finally {
      setGravando(false);
    }
  }

  /** `PD-21`: o `close` do popup (Esc, "Voltar e corrigir", navegador) — nada é salvo. */
  function voltar() {
    setDivergenciaAberta(false);
    setErroAoSalvar(null);
    document.getElementById("calculadora-SALDO")?.focus();
  }

  if (erroDeCarga) {
    return (
      <p role="alert" className="aviso-erro">
        {erroDeCarga}
      </p>
    );
  }
  if (!inicial) return <p role="status">{TEXTOS.calculando}</p>;

  const atual = resultado?.corpo === corpo ? resultado : null;
  const previa = atual?.previa ?? null;
  const falha = atual?.falha ?? null;
  const erros = previa?.estado === "ERRO" ? previa.erros : [];
  const mensagemDeErro =
    previa?.estado === "ERRO"
      ? erros.length > 0
        ? erros.map((e) => e.mensagem).join(" ")
        : previa.mensagem
      : falha;
  const idDoErro = "calculadora-erro";
  const podeConfirmar =
    previa !== null && previa.estado !== "ERRO" && !gravando;

  /** `PD-22`: decide pela prévia na tela, sem nova chamada. */
  function continuar() {
    if (previa?.estado === "INCOMPATIVEL") setDivergenciaAberta(true);
    else void confirmar(null);
  }

  return (
    <div className="flex flex-col gap-4">
      {CAMPOS.map((campo) => {
        const { texto, naoSei } = campos[campo];
        const id = `calculadora-${campo}`;
        const invalido = erros.some((e) => e.campo === campo);
        const linha = linhaDoCampo(campo, previa);
        const idDaLinha = `${id}-linha`;
        const descricao = [invalido && idDoErro, linha && idDaLinha]
          .filter(Boolean)
          .join(" ");
        const rotulo =
          campo === "TAXA"
            ? (inicial.enunciadoDaPeriodicidade ?? NOMES.TAXA)
            : (inicial.enunciados[campo] ?? NOMES[campo]);
        const entrada = (
          <input
            id={id}
            inputMode={campo === "PRAZO" ? "numeric" : "decimal"}
            className={campo === "PRAZO" ? "campo-texto" : undefined}
            value={texto}
            aria-invalid={invalido || undefined}
            aria-describedby={descricao || undefined}
            onChange={(e) =>
              mudarCampo(campo, {
                texto: aplicarMascara(MASCARA[campo], e.target.value),
                naoSei: false,
              })
            }
          />
        );
        const explicacaoDoCampo = inicial.explicacoes[campo];
        return (
          <div key={campo} className="field flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <label
                htmlFor={id}
                className="font-serif text-[1.15rem] font-semibold"
              >
                {rotulo}
              </label>
              {explicacaoDoCampo && (
                <Explicacao
                  campo={NOMES[campo]}
                  oQueE={explicacaoDoCampo.o_que_e}
                  ondeEncontrar={explicacaoDoCampo.onde_encontrar}
                />
              )}
            </div>
            {campo === "PRAZO" ? (
              entrada
            ) : campo === "TAXA" ? (
              <div className="flex items-center gap-2">
                <div className="money flex-1">{entrada}</div>
                <span className="text-muted" aria-hidden="true">
                  %
                </span>
              </div>
            ) : (
              <div className="money">
                <span aria-hidden="true">R$</span>
                {entrada}
              </div>
            )}
            {campo === "TAXA" && (
              <fieldset className="flex flex-wrap gap-2 border-0 p-0">
                <legend className="sr-only">{NOMES.TAXA}</legend>
                {(["MENSAL", "ANUAL"] as const).map((valor) => (
                  <label key={valor} className="opt">
                    <input
                      type="radio"
                      name="calculadora-periodicidade"
                      className="h-[26px] w-[26px] accent-accent"
                      checked={periodicidade === valor}
                      onChange={() =>
                        mudarPremissa(() => setPeriodicidade(valor))
                      }
                    />
                    <span>
                      {inicial.rotulosDaPeriodicidade[valor] ?? valor}
                    </span>
                  </label>
                ))}
              </fieldset>
            )}
            <label className="opt">
              <input
                type="checkbox"
                className="h-[26px] w-[26px] accent-accent"
                checked={naoSei}
                onChange={(e) =>
                  mudarCampo(
                    campo,
                    e.target.checked
                      ? { texto: "", naoSei: true }
                      : { texto, naoSei: false },
                  )
                }
              />
              <span>{TEXTOS.naoSei}</span>
              <span className="sr-only"> — {NOMES[campo]}</span>
            </label>
            {linha && (
              <p id={idDaLinha} className="nota m-0">
                {linha}
              </p>
            )}
          </div>
        );
      })}

      <fieldset className="flex flex-wrap gap-2 border-0 p-0">
        <legend className="mb-2 font-serif text-[1.15rem] font-semibold">
          {inicial.enunciadoDoSistema ?? ""}
        </legend>
        {(["PRICE", "SAC"] as const).map((valor) => (
          <label key={valor} className="opt">
            <input
              type="radio"
              name="calculadora-sistema"
              className="h-[26px] w-[26px] accent-accent"
              checked={sistema === valor}
              onChange={() => mudarPremissa(() => setSistema(valor))}
            />
            <span>{inicial.rotulosDoSistema[valor] ?? valor}</span>
          </label>
        ))}
      </fieldset>

      {mensagemDeErro && (
        <p id={idDoErro} role="alert" className="aviso-erro">
          {mensagemDeErro}
        </p>
      )}

      {/* `EC-105`: com o popup aberto, o erro ao salvar aparece só dentro dele. */}
      {erroAoSalvar && !divergenciaAberta && (
        <p role="alert" className="aviso-erro">
          {erroAoSalvar}
        </p>
      )}

      <div>
        <Botao onClick={continuar} disabled={!podeConfirmar}>
          {gravando ? "Salvando…" : rotuloConfirmar}
        </Botao>
      </div>

      {divergenciaAberta && previa && (
        <DivergenciaDaDivida
          casoId={casoId}
          corpo={corpo}
          previa={previa}
          gravando={gravando}
          erroAoSalvar={erroAoSalvar}
          aoConfirmar={(recalcular) => void confirmar(recalcular)}
          aoVoltar={voltar}
        />
      )}
    </div>
  );
}
