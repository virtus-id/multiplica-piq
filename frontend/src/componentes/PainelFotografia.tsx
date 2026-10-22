/**
 * A fotografia do mês na `B3.C00` — `RF-79`, `RF-80`, `EC-28` (T-228).
 *
 * Três números, todos do SERVIDOR (`app/montagem/entrada.py`): nenhuma soma
 * aqui — nem das decomposições, que são só consulta. `null` é "não
 * informado", nunca `R$ 0,00` (`EC-28`); a marca "parcial (há itens sem
 * valor)" é a decisão do produto `R9-2`. A sobra é a do orçamento **antes
 * das dívidas** — o rótulo diz isso (`AC-117`).
 *
 * As decomposições aparecem sempre (`T-413`), sem botão de abrir: em tabela
 * compacta a partir de 768px — o mesmo desenho da fila do revisor
 * (`TabelaDeCasos`) — e como lista de cartões abaixo disso. Cada linha leva
 * ao "corrigir" pela rota de correção de `RF-69`, com o botão à direita.
 */
import { moeda } from '../moeda'
import type { LinhaDaFotografia, PainelFotografia as Painel } from '../tipos'
import Botao from './Botao'

const PARCIAL = 'parcial (há itens sem valor)'

type AoCorrigir = (idPergunta: string, itemId: string) => void

function Numero({ rotulo, valor, parcial }: { rotulo: string; valor: string | null; parcial: boolean }) {
  return (
    <div>
      <dt className="text-muted">{rotulo}</dt>
      <dd className="m-0 font-bold tabular-nums">
        {moeda(valor)}
        {parcial && valor !== null && <span className="nota"> — {PARCIAL}</span>}
      </dd>
    </div>
  )
}

function Corrigir({ linha, aoCorrigir }: { linha: LinhaDaFotografia; aoCorrigir?: AoCorrigir }) {
  if (!aoCorrigir || !linha.corrigir.ID_PERGUNTA) return null
  return (
    <Botao
      variante="secundario"
      className="!min-h-0 !w-auto !px-2 !py-0.5 !text-xs"
      onClick={() => aoCorrigir(linha.corrigir.ID_PERGUNTA ?? '', linha.corrigir.item_id)}
    >
      Corrigir<span className="sr-only"> {linha.rotulo ?? linha.item_id}</span>
    </Botao>
  )
}

/** Tabela (≥768px) e cartões (<768px) da mesma lista; o CSS esconde um deles. */
function Linhas({
  titulo,
  linhas,
  aoCorrigir,
  id,
}: {
  titulo: string
  linhas: LinhaDaFotografia[]
  aoCorrigir?: AoCorrigir
  id: string
}) {
  if (linhas.length === 0) return null
  return (
    <section aria-labelledby={id} className="min-w-0">
      <h3 id={id} className="eyebrow">
        {titulo}
      </h3>
      <div data-testid={`tabela-${id}`} className="hidden max-h-[60vh] overflow-auto md:block">
        <table className="w-full table-fixed border-collapse text-left text-xs">
          <colgroup>
            <col style={{ width: '8%' }} />
            <col style={{ width: '52%' }} />
            <col style={{ width: '22%' }} />
            <col style={{ width: '18%' }} />
          </colgroup>
          <thead>
            <tr className="sticky top-0 bg-surface">
              <th scope="col" className="border-b-2 border-line px-1.5 py-1">
                #
              </th>
              <th scope="col" className="border-b-2 border-line px-1.5 py-1">
                Despesa
              </th>
              <th scope="col" className="border-b-2 border-line px-1.5 py-1 text-right">
                Valor no mês
              </th>
              <th scope="col" className="border-b-2 border-line px-1.5 py-1 text-right">
                Ação
              </th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((linha, indice) => (
              <tr key={linha.item_id} className="border-b border-line align-middle hover:bg-line">
                <td className="px-1.5 py-1 tabular-nums text-muted">{indice + 1}</td>
                <td className="truncate px-1.5 py-1" title={linha.rotulo ?? linha.item_id}>
                  {linha.rotulo ?? linha.item_id}
                </td>
                <td className="px-1.5 py-1 text-right tabular-nums">{moeda(linha.valor_mensal)}</td>
                <td className="px-1.5 py-1 text-right">
                  <Corrigir linha={linha} aoCorrigir={aoCorrigir} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul
        data-testid={`cartoes-${id}`}
        className="m-0 flex list-none flex-col gap-2 p-0 md:hidden"
      >
        {linhas.map((linha) => (
          <li key={linha.item_id} className="linha flex-wrap">
            <span>{linha.rotulo ?? linha.item_id}</span>
            <span className="tabular-nums">{moeda(linha.valor_mensal)}</span>
            <Corrigir linha={linha} aoCorrigir={aoCorrigir} />
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function PainelFotografia({
  painel,
  aoCorrigir,
}: {
  painel: Painel
  /** Sem ela, as linhas são só consulta (nenhum botão que não leva a nada). */
  aoCorrigir?: AoCorrigir
}) {
  return (
    <section className="cartao" aria-label="Fotografia do seu mês">
      <dl className="m-0 grid gap-3 md:grid-cols-3">
        <Numero rotulo="Renda total" valor={painel.renda_total} parcial={painel.parcial.renda} />
        <Numero
          rotulo="Despesas totais"
          valor={painel.despesas_totais}
          parcial={painel.parcial.despesas}
        />
        <Numero
          rotulo="Sobra do mês, antes das dívidas"
          valor={painel.sobra_antes_das_dividas}
          parcial={painel.parcial.sobra}
        />
      </dl>
      <div className="grid gap-4 pt-3 xl:grid-cols-2">
        <Linhas
          id="despesas-por-item"
          titulo="Despesas por item"
          linhas={painel.despesas_por_item}
          aoCorrigir={aoCorrigir}
        />
        <Linhas
          id="despesas-nao-mensais"
          titulo="Despesas não mensais, convertidas para o mês"
          linhas={painel.nao_mensais_por_item}
          aoCorrigir={aoCorrigir}
        />
      </div>
    </section>
  )
}
