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
  PeriodicidadeDaTaxa,
  Pergunta,
  RespostaDaPrevia,
  SistemaDaDivida,
  TipoResposta,
} from "../tipos";
import Botao from "./Botao";

/** Espera depois da última edição antes de pedir a prévia. */
export const ESPERA_DA_PREVIA_MS = 400;

// Provisórios: a redação aprovada é `T-507`/`T-509`. Texto que o servidor já
// devolve (mensagens, rótulo de marca, valores) nunca é escrito aqui.
const TEXTOS = {
  naoSei: "Não sei",
  falhaAoCarregar: "Não foi possível carregar a pergunta.",
  falhaAoSalvar: "Não foi possível salvar.",
  falhaDeRede: "Não foi possível calcular.",
  escolhaDoRecalculo: "Qual informação recalcular?",
  manterOriginais: "Manter os valores que informei",
  valorTeorico: "Valor teórico",
  incompativel: "Valores incompatíveis",
  resumo: "Resumo do cálculo",
  prazo: "Prazo (meses)",
  primeiraParcela: "Primeira parcela",
  ultimoPagamento: "Último pagamento",
  totalDeJuros: "Total de juros",
  calculando: "Calculando…",
  parcelaEstimada: "Parcela estimada [PROVISORIO T-532]",
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
  const [recalcular, setRecalcular] = useState<CampoDaDivida | null>(null);
  /** As opções de recálculo ficam enquanto o aluno não edita um valor. */
  const [opcoesDeRecalculo, setOpcoesDeRecalculo] = useState<CampoDaDivida[]>(
    [],
  );
  /** O resultado vale só para o `corpo` que o pediu: editou, deixa de valer na hora (`AC-529`). */
  const [resultado, setResultado] = useState<{
    corpo: CorpoDaCalculadora;
    previa?: RespostaDaPrevia;
    falha?: string;
  } | null>(null);
  const [gravando, setGravando] = useState(false);
  const [erroAoSalvar, setErroAoSalvar] = useState<string | null>(null);

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
  // leva o valor que o servidor calculou (risco 9).
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
      recalcular,
    };
  }, [campos, sistema, periodicidade, recalcular]);

  useEffect(() => {
    if (!inicial) return;
    const controle = new AbortController();
    const espera = setTimeout(() => {
      preverCalculadora(casoId, corpo, controle.signal)
        .then((previa) => {
          if (controle.signal.aborted) return;
          setResultado({ corpo, previa });
          if (previa.alternativas.length > 0)
            setOpcoesDeRecalculo(previa.alternativas);
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

  /** Mudou um valor: a escolha de recálculo anterior deixa de valer (`EC-70`). */
  function mudarCampo(campo: CampoDaDivida, novo: EstadoDoCampo) {
    editou();
    setRecalcular(null);
    setOpcoesDeRecalculo([]);
    setCampos((atual) => ({ ...atual, [campo]: novo }));
  }

  function mudarPremissa(mudanca: () => void) {
    editou();
    setRecalcular(null);
    setOpcoesDeRecalculo([]);
    mudanca();
  }

  async function confirmar() {
    if (pergunta.item_id === null) return;
    setGravando(true);
    setErroAoSalvar(null);
    try {
      aoConfirmar(await confirmarCalculadora(casoId, pergunta.item_id, corpo));
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
  const calculando = atual === null;
  const erros = previa?.estado === "ERRO" ? previa.erros : [];
  const mensagemDeErro =
    previa?.estado === "ERRO"
      ? erros.length > 0
        ? erros.map((e) => e.mensagem).join(" ")
        : previa.mensagem
      : falha;
  const idDoErro = "calculadora-erro";
  const incompativel = previa?.estado === "INCOMPATIVEL";
  const valores = previa?.valores ?? {};
  const podeConfirmar =
    previa !== null && previa.estado !== "ERRO" && !gravando;

  return (
    <div className="flex flex-col gap-4">
      {CAMPOS.map((campo) => {
        const { texto, naoSei } = campos[campo];
        const id = `calculadora-${campo}`;
        const invalido = erros.some((e) => e.campo === campo);
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
            aria-describedby={invalido ? idDoErro : undefined}
            onChange={(e) =>
              mudarCampo(campo, {
                texto: aplicarMascara(MASCARA[campo], e.target.value),
                naoSei: false,
              })
            }
          />
        );
        return (
          <div key={campo} className="field flex flex-col gap-2">
            <label
              htmlFor={id}
              className="font-serif text-[1.15rem] font-semibold"
            >
              {rotulo}
            </label>
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

      <div role="status" aria-busy={calculando} className="flex flex-col gap-3">
        {calculando && <p className="nota m-0">{TEXTOS.calculando}</p>}
        {previa && previa.estado !== "ERRO" && (
          <>
            {previa.mensagem && (
              <p className={incompativel ? "aviso-atencao" : "nota m-0"}>
                {incompativel && <strong>{TEXTOS.incompativel}. </strong>}
                {previa.mensagem}
              </p>
            )}
            {CAMPOS.map((campo) => {
              const valor = valores[campo];
              return (
                valor && (
                  <p
                    key={campo}
                    className="m-0 flex flex-wrap items-center gap-2"
                  >
                    <span>{NOMES[campo]}:</span>
                    <strong className="tabular-nums">{valor.texto}</strong>
                    <span
                      className={
                        valor.marca === "INFORMADO"
                          ? "chip chip-mudo"
                          : "chip chip-ok"
                      }
                    >
                      {valor.rotulo}
                    </span>
                  </p>
                )
              );
            })}
            {previa.parcela_estimada && (
              // `RF-533`: a estimada fica FORA dos campos digitados, em linha própria e marcada.
              <p
                className="m-0 flex flex-wrap items-center gap-2"
                data-testid="parcela-estimada"
              >
                <span>{TEXTOS.parcelaEstimada}:</span>
                <strong className="tabular-nums">
                  {previa.parcela_estimada.texto}
                </strong>
                <span className="chip chip-mudo">
                  {previa.parcela_estimada.rotulo}
                </span>
                <span className="nota">{previa.parcela_estimada.hipotese}</span>
              </p>
            )}
            {previa.hipotese_conservadora && (
              // `RF-538`/`RF-539`: só saldo e taxa da hipótese; parcela e prazo dela não aparecem.
              <div
                className="m-0 flex flex-col gap-1"
                data-testid="hipotese-conservadora"
              >
                <p className="m-0 flex flex-wrap items-center gap-2">
                  <span>{NOMES.SALDO}:</span>
                  <strong className="tabular-nums">
                    {previa.hipotese_conservadora.saldo}
                  </strong>
                  <span>{NOMES.TAXA}:</span>
                  <strong className="tabular-nums">
                    {previa.hipotese_conservadora.taxa}
                  </strong>
                  <span className="chip chip-mudo">
                    {previa.hipotese_conservadora.rotulo}
                  </span>
                </p>
                <span className="nota">
                  {previa.hipotese_conservadora.aviso}
                </span>
              </div>
            )}
            {previa.teorico && (
              <p className="m-0">
                {TEXTOS.valorTeorico} — {NOMES[previa.teorico.campo]}:{" "}
                <strong className="tabular-nums">{previa.teorico.texto}</strong>
              </p>
            )}
            {previa.resumo && (
              <dl
                className="m-0 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1"
                aria-label={TEXTOS.resumo}
              >
                <dt>{TEXTOS.prazo}</dt>
                <dd className="m-0 tabular-nums">{previa.resumo.prazo}</dd>
                <dt>{TEXTOS.primeiraParcela}</dt>
                <dd className="m-0 tabular-nums">
                  {previa.resumo.primeira_parcela}
                </dd>
                <dt>{TEXTOS.ultimoPagamento}</dt>
                <dd className="m-0 tabular-nums">
                  {previa.resumo.ultimo_pagamento}
                </dd>
                <dt>{TEXTOS.totalDeJuros}</dt>
                <dd className="m-0 tabular-nums">
                  {previa.resumo.total_de_juros}
                </dd>
              </dl>
            )}
          </>
        )}
      </div>

      {opcoesDeRecalculo.length > 0 && (
        // `RF-525`: a escolha é do aluno; sem ela, os originais e o sinal permanecem.
        <fieldset className="flex flex-col gap-2 border-0 p-0">
          <legend className="mb-2 font-serif text-[1.15rem] font-semibold">
            {TEXTOS.escolhaDoRecalculo}
          </legend>
          {opcoesDeRecalculo.map((campo) => (
            <label key={campo} className="opt">
              <input
                type="radio"
                name="calculadora-recalcular"
                className="h-[26px] w-[26px] accent-accent"
                checked={recalcular === campo}
                onChange={() => {
                  editou();
                  setRecalcular(campo);
                }}
              />
              <span>{NOMES[campo]}</span>
            </label>
          ))}
          <label className="opt">
            <input
              type="radio"
              name="calculadora-recalcular"
              className="h-[26px] w-[26px] accent-accent"
              checked={recalcular === null}
              onChange={() => {
                editou();
                setRecalcular(null);
              }}
            />
            <span>{TEXTOS.manterOriginais}</span>
          </label>
        </fieldset>
      )}

      {erroAoSalvar && (
        <p role="alert" className="aviso-erro">
          {erroAoSalvar}
        </p>
      )}

      <div>
        <Botao onClick={() => void confirmar()} disabled={!podeConfirmar}>
          {gravando ? "Salvando…" : rotuloConfirmar}
        </Botao>
      </div>
    </div>
  );
}
