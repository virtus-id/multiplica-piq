/**
 * As partes da mesa de conferência do revisor — `T-429` (`RF-441`).
 *
 * Só apresentação: cada peça lê campos que a API da conferência já entrega
 * (`GET /api/revisao/caso/{id}` e `GET /revisao/caso/{id}/decisao`), já
 * formatados pelo servidor. Nenhuma conta, nenhum critério de homologação e
 * nenhum dado inventado aqui; o que falta é dito "não disponível", nunca zero.
 * As dívidas se ligam aos seus dados pelo `DIVIDA_ID`, nunca pela posição.
 */
import { type ReactNode, useState } from 'react'

import type { CampoDeEntrada, CasoParaRevisao, EstadoInputs } from '../../services/api'
import type { Plano, PosicaoDaOrdem } from '../../tipos'
import Icone, { type NomeDoIcone } from '../Icone'
import ListaDeDados from '../ListaDeDados'

const NAO_DISPONIVEL = 'não disponível'

function campo(campos: readonly CampoDeEntrada[], codigo: string): string | undefined {
  return campos.find((c) => c.codigo === codigo)?.valor
}

/** Só realça: o texto já traz o sinal, e a cor nunca é o único portador. */
function eNegativo(valor: string): boolean {
  return /(^|\s|R\$)[-−]/.test(valor)
}

type Tom = 'neutro' | 'positivo' | 'negativo' | 'atencao'

const COR_DO_TOM: Readonly<Record<Tom, string>> = {
  neutro: 'text-ink',
  positivo: 'text-accent',
  negativo: 'text-bad',
  atencao: 'text-warn',
}

interface Indicador {
  rotulo: string
  valor: string
  icone: NomeDoIcone
  tom: Tom
  detalhe?: string
}

/** A faixa de leitura rápida. Indicador sem dado real não aparece. */
export function ResumoExecutivo({
  plano,
  entradas,
  resumo,
}: {
  plano: Plano
  entradas: EstadoInputs
  resumo: CasoParaRevisao['resumo']
}) {
  const renda = campo(entradas.campos, 'RENDA_TOTAL_RECORRENTE')
  const resultado = plano.RESULTADO_CAIXA_OBSERVADO
  const indicadores: Indicador[] = []
  if (renda) indicadores.push({ rotulo: 'Renda total recorrente', valor: renda, icone: 'dinheiro', tom: 'neutro' })
  // Saídas = despesas + não mensais + parcelas das dívidas (soma do servidor);
  // renda − saídas = o resultado do mês logo ao lado.
  if (resumo?.saidas_totais) {
    indicadores.push({
      rotulo: 'Saídas totais do mês',
      valor: resumo.saidas_totais,
      icone: 'reserva',
      tom: 'neutro',
    })
  }
  if (resultado) {
    indicadores.push({
      rotulo: 'Resultado do mês',
      valor: resultado,
      icone: 'taxa',
      tom: eNegativo(resultado) ? 'negativo' : 'neutro',
    })
  }
  indicadores.push({
    rotulo: 'Total de dívidas',
    valor: String(entradas.dividas.length),
    icone: 'bandeira',
    tom: 'neutro',
  })
  if (resumo?.total_em_dividas) {
    indicadores.push({
      rotulo: 'Total em dívidas',
      valor: resumo.total_em_dividas,
      icone: 'taxa',
      tom: 'neutro',
      detalhe: resumo.total_em_dividas_parcial ? 'Parcial: há dívida sem saldo informado' : 'Soma dos saldos devedores',
    })
  }
  const existe = campo(entradas.campos, 'RESERVA_EXISTE')
  if (existe) {
    const total = campo(entradas.campos, 'RESERVA_TOTAL')
    const valor = total && /\d/.test(total) ? total : undefined
    const disposicao = campo(entradas.campos, 'DISPOSICAO_USO_RESERVA')
    const maximo = campo(entradas.campos, 'VALOR_MAXIMO_RESERVA_INFORMADO_USUARIO')
    // Com valor salvo pelo aluno, o destaque é o total; sem ele, só o "tem reserva".
    // "Aceita usar" só entra quando há valor (nada de "Não informado" como ruído).
    indicadores.push({
      rotulo: valor ? 'Total em reserva' : 'Possui reserva',
      valor: valor ?? existe,
      icone: 'reserva',
      tom: 'neutro',
      detalhe:
        [disposicao && `Uso: ${disposicao}`, maximo && /\d/.test(maximo) && `Aceita usar: ${maximo}`]
          .filter(Boolean)
          .join(' · ') || undefined,
    })
  }

  return (
    <dl className="m-0 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-3 2xl:grid-cols-6">
      {indicadores.map((i) => (
        <div key={i.rotulo} className="min-w-0 rounded-piq border border-line bg-surface px-3 py-2.5">
          <dt className="flex items-center gap-1.5 text-xs text-muted">
            <Icone nome={i.icone} /> {i.rotulo}
          </dt>
          <dd className={`m-0 mt-1 text-lg font-bold tabular-nums [overflow-wrap:anywhere] ${COR_DO_TOM[i.tom]}`}>
            {i.valor}
          </dd>
          {i.detalhe && (
            // Uma linha só: o que não cabe vira reticências e o texto inteiro fica no `title`.
            <dd className="m-0 truncate text-xs text-muted" title={i.detalhe}>
              {i.detalhe}
            </dd>
          )}
        </div>
      ))}
    </dl>
  )
}

/** A estratégia do plano e os avisos que o servidor mandou. */
export function AnaliseFinanceira({ plano }: { plano: Plano }) {
  const itens: [string, string][] = [
    ['Método', plano.metodo],
    ['Cenário', plano.cenario],
    ['Prazo total', plano.PRAZO_TOTAL],
    ['Custo futuro total', plano.CUSTO_FUTURO_TOTAL],
  ]
  if (plano.valor_mensal_destinado) itens.push(['Valor mensal destinado', plano.valor_mensal_destinado])
  itens.push([
    'Reserva mobilizável',
    plano.reserva_mobilizavel.pendente_de_decisao ? 'decisão pendente' : plano.reserva_mobilizavel.valor,
  ])
  const avisos = [plano.aviso_sem_valor_extra, ...(plano.avisos_gerais ?? [])].filter(Boolean)

  return (
    <section className="cartao" aria-labelledby="titulo-analise">
      <h2 id="titulo-analise" className="m-0">
        Análise financeira e estratégia
      </h2>
      <p className="nota m-0">
        Confira os principais dados financeiros e a estratégia definida para este plano.
      </p>
      {plano.MODO_ESTABILIZACAO && (
        <div className="aviso-atencao" role="status">
          <div>
            <strong className="block">Primeiro, equilibrar o seu mês.</strong>
            Resultado do mês: {plano.RESULTADO_CAIXA_OBSERVADO}. Faltam cortar {plano.FALTA_CORTAR} por
            mês para chegar a zero.
          </div>
        </div>
      )}
      {avisos.map((aviso) => (
        <p key={aviso} className="aviso-atencao m-0" role="status">
          {aviso}
        </p>
      ))}
      <dl className="m-0 grid grid-cols-1 gap-x-6 sm:grid-cols-2">
        {itens.map(([rotulo, valor]) => (
          <div key={rotulo} className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-x-3 border-b border-line py-1.5">
            <dt className="text-sm text-muted">{rotulo}</dt>
            <dd className="m-0 font-medium tabular-nums [overflow-wrap:anywhere]">{valor}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function Celula({ valor }: { valor: string | undefined }) {
  return (
    <td className="px-2 py-2 tabular-nums [overflow-wrap:anywhere]">
      {valor && valor.length > 0 ? valor : <span className="text-muted">{NAO_DISPONIVEL}</span>}
    </td>
  )
}

/**
 * As dívidas na ordem do plano. Saldo, taxa, parcela e situação vêm dos campos
 * da própria dívida (`estado_inputs.dividas`, ligados pelo `DIVIDA_ID`); o mês
 * de quitação, da posição no plano. O valor mensal destinado é do plano
 * inteiro e não existe por dívida, então não ganha coluna.
 */
export function TabelaDeDividas({ plano, entradas }: { plano: Plano; entradas: EstadoInputs }) {
  const [abertas, setAbertas] = useState<Record<string, boolean>>({})
  const foraDaOrdem = entradas.dividas.filter((d) => !plano.ordem.some((p) => p.DIVIDA_ID === d.DIVIDA_ID))
  if (plano.ordem.length === 0 && foraDaOrdem.length === 0) {
    return (
      <section className="cartao" aria-labelledby="titulo-dividas-plano">
        <h2 id="titulo-dividas-plano" className="m-0">
          Dívidas do plano
        </h2>
        <p className="nota m-0">Este plano não tem dívidas na ordem de quitação.</p>
      </section>
    )
  }

  return (
    <section className="cartao" aria-labelledby="titulo-dividas-plano">
      <h2 id="titulo-dividas-plano" className="m-0">
        Dívidas do plano
      </h2>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b-2 border-line">
              {['Ordem', 'Dívida', 'Saldo devedor', 'Taxa de juros', 'Parcela atual', 'Mês de quitação', 'Situação', ''].map(
                (titulo, i) => (
                  <th key={`${titulo}-${i}`} scope="col" className="px-2 py-2 font-bold">
                    {titulo || <span className="sr-only">Detalhes</span>}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {plano.ordem.map((p: PosicaoDaOrdem) => {
              const divida = entradas.dividas.find((d) => d.DIVIDA_ID === p.DIVIDA_ID)
              const campos = divida?.campos ?? []
              const aberta = abertas[p.DIVIDA_ID] === true
              return (
                <FragmentoDaDivida key={p.DIVIDA_ID}>
                  <tr className="border-b border-line align-top">
                    <td className="px-2 py-2 font-bold tabular-nums">{p.posicao}</td>
                    <td className="px-2 py-2">
                      <strong className="block [overflow-wrap:anywhere]">{p.nome}</strong>
                      <small className="text-muted">{p.DIVIDA_ID}</small>
                    </td>
                    <Celula valor={campo(campos, 'SALDO_DEVEDOR_ATUAL')} />
                    <Celula valor={campo(campos, 'TAXA_EFETIVA_MENSAL_NORMALIZADA')} />
                    <Celula valor={campo(campos, 'PARCELA_CONTRATUAL')} />
                    <Celula valor={p.mes_de_quitacao != null ? `mês ${p.mes_de_quitacao}` : undefined} />
                    <Celula valor={campo(campos, 'STATUS_DIVIDA')} />
                    <td className="px-2 py-2 text-right">
                      <button
                        type="button"
                        className="btn-discreto !min-h-0 !w-auto !px-2 !py-1 !text-xs"
                        aria-expanded={aberta}
                        onClick={() => setAbertas((atual) => ({ ...atual, [p.DIVIDA_ID]: !aberta }))}
                      >
                        {aberta ? 'Recolher' : 'Detalhes'}
                        <span className="sr-only"> de {p.nome}</span>
                      </button>
                    </td>
                  </tr>
                  {aberta && (
                    <tr className="border-b border-line bg-bg">
                      <td colSpan={8} className="px-3 py-3">
                        {p.JUSTIFICATIVA_POSICAO && (
                          <p className="m-0 mb-2 text-sm text-muted">{p.JUSTIFICATIVA_POSICAO}</p>
                        )}
                        {p.fonte && <p className="m-0 mb-2 text-sm">Fonte dos dados: {p.fonte}</p>}
                        {(p.fatos_de_risco ?? []).length > 0 && (
                          <ul className="m-0 mb-2 list-none p-0 text-sm">
                            {(p.fatos_de_risco ?? []).map((fato) => (
                              <li key={fato.nome}>
                                {fato.nome}: <strong>{fato.valor}</strong>
                              </li>
                            ))}
                          </ul>
                        )}
                        {campos.length > 0 ? (
                          <ListaDeDados campos={campos} />
                        ) : (
                          <p className="nota m-0">Esta dívida não tem dados de entrada nesta versão.</p>
                        )}
                      </td>
                    </tr>
                  )}
                </FragmentoDaDivida>
              )
            })}
            {foraDaOrdem.map((d) => (
              <FragmentoDaDivida key={d.DIVIDA_ID}>
                <tr className="border-b border-line align-top">
                  <td className="px-2 py-2 text-muted">—</td>
                  <td className="px-2 py-2">
                    <strong className="block [overflow-wrap:anywhere]">{d.nome}</strong>
                    <small className="text-muted">{d.DIVIDA_ID}</small>
                  </td>
                  <Celula valor={campo(d.campos, 'SALDO_DEVEDOR_ATUAL')} />
                  <Celula valor={campo(d.campos, 'TAXA_EFETIVA_MENSAL_NORMALIZADA')} />
                  <Celula valor={campo(d.campos, 'PARCELA_CONTRATUAL')} />
                  <Celula valor={undefined} />
                  <Celula valor={campo(d.campos, 'STATUS_DIVIDA')} />
                  <td className="px-2 py-2" />
                </tr>
              </FragmentoDaDivida>
            ))}
          </tbody>
        </table>
      </div>
      {foraDaOrdem.length > 0 && (
        <p className="nota m-0">
          Dívidas com "—" estão cadastradas, mas fora da ordem de quitação do plano. Os dados delas estão em
          "Dados que produziram o plano".
        </p>
      )}
    </section>
  )
}

function FragmentoDaDivida({ children }: { children: ReactNode }) {
  return <>{children}</>
}

const CODIGOS_DA_RESERVA: ReadonlySet<string> = new Set([
  'RESERVA_EXISTE',
  'RESERVA_TOTAL',
  'RESERVA_MOBILIZAVEL',
  'DISPOSICAO_USO_RESERVA',
  'VALOR_MAXIMO_RESERVA_INFORMADO_USUARIO',
  'DINHEIRO_DISPONIVEL',
])

function Grupo({
  titulo,
  campos,
  aberto = false,
}: {
  titulo: string
  campos: CampoDeEntrada[]
  aberto?: boolean
}) {
  if (campos.length === 0) return null
  return (
    <details open={aberto} className="border-t border-line py-2">
      <summary className="cursor-pointer font-bold">
        {titulo} <small className="font-normal text-muted">· {campos.length}</small>
      </summary>
      <ListaDeDados campos={campos} />
    </details>
  )
}

/**
 * Todos os campos de `estado_inputs`, agrupados — nenhum é omitido. O revisor
 * compara o plano contra o estado COMPLETO; os valores já vêm formatados pelo
 * servidor (`DESCONHECIDO` nunca vira `0`). São dados do estado do motor, não
 * as respostas pergunta a pergunta do aluno.
 */
export function DadosQueProduziramOPlano({ entradas }: { entradas: EstadoInputs }) {
  const reserva = entradas.campos.filter((c) => CODIGOS_DA_RESERVA.has(c.codigo))
  const financeiros = entradas.campos.filter((c) => !CODIGOS_DA_RESERVA.has(c.codigo))
  return (
    <section className="cartao min-w-0" aria-labelledby="titulo-dados-plano">
      <h2 id="titulo-dados-plano" className="m-0">
        Dados que produziram o plano
      </h2>
      <p className="nota m-0">Estado completo usado no cálculo, como o servidor o registrou.</p>
      <Grupo titulo="Informações financeiras" campos={financeiros} aberto />
      <Grupo titulo="Reserva e patrimônio" campos={reserva} />
      {entradas.dividas.length > 0 && (
        <details className="border-t border-line py-2">
          <summary className="cursor-pointer font-bold">
            Dívidas individuais <small className="font-normal text-muted">· {entradas.dividas.length}</small>
          </summary>
          {entradas.dividas.map((divida) => (
            <Grupo key={divida.DIVIDA_ID} titulo={divida.nome} campos={divida.campos} />
          ))}
        </details>
      )}
      <Grupo titulo="Como lida com os gastos" campos={entradas.perfil_comportamental} />
      <Grupo titulo="Sinais de comportamento" campos={entradas.sinais_comportamentais} />
    </section>
  )
}
