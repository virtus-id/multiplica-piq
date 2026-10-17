/**
 * Tabela de casos do revisor — `RF-502`, `RF-505`, `RF-507` (T-409).
 *
 * A partir de 768px é tabela com cabeçalho fixo; abaixo disso, a mesma
 * linha vira cartão (sem rolagem horizontal a 360px). Os dois são
 * renderizados e o CSS esconde um — por isso cada um tem o seu `data-testid`.
 *
 * Os dois sinais (`entra_por_politica`, `e_metodologico`) são chips
 * SEPARADOS, como em `AC-28`. Status e tipo chegam em código, mas a tela
 * só mostra `status_rotulo`/`tipo_rotulo`.
 */
import type { CampoDeOrdem, LinhaDeCaso } from '../tipos'
import Botao from './Botao'
import Icone from './Icone'

export interface Ordem {
  campo: CampoDeOrdem
  direcao: 'asc' | 'desc'
}

interface TabelaDeCasosProps {
  itens: LinhaDeCaso[]
  ordem: Ordem
  aoOrdenar: (campo: CampoDeOrdem) => void
  abrirCaso?: (casoId: string) => void
}

const COLUNAS: { titulo: string; campo?: CampoDeOrdem }[] = [
  { titulo: 'Aluno', campo: 'aluno' },
  { titulo: 'Chegou em', campo: 'chegou_em' },
  { titulo: 'Tempo na fila', campo: 'tempo_na_fila' },
  { titulo: 'Status', campo: 'status' },
  { titulo: 'Tipo', campo: 'tipo' },
  { titulo: 'Situação do mês', campo: 'situacao_mes' },
  { titulo: 'Dívidas', campo: 'dividas' },
  { titulo: 'Método', campo: 'metodo' },
  { titulo: 'Motivo da revisão' },
  { titulo: 'Revisor e decisão', campo: 'decidido_em' },
  { titulo: 'Ação' },
]

export function formatarData(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

/** `53` → "2 d 5 h"; menos de um dia → "5 h". */
export function formatarTempo(horas: number): string {
  const h = Math.floor(horas)
  if (h < 1) return 'menos de 1 h'
  const d = Math.floor(h / 24)
  return d > 0 ? `${d} d ${h % 24} h` : `${h} h`
}

function classeDoStatus(status: string): string {
  if (status === 'AGUARDANDO_REVISAO') return 'chip chip-atencao'
  if (status === 'PLANO_LIBERADO') return 'chip chip-ok'
  return 'chip chip-mudo'
}

function Aluno({ c }: { c: LinhaDeCaso }) {
  return (
    <>
      <span className="block font-bold">{c.nome || c.email_do_aluno || c.CASO_ID}</span>
      {c.nome && c.email_do_aluno && (
        <small className="block break-all text-muted">{c.email_do_aluno}</small>
      )}
    </>
  )
}

function Chegada({ c }: { c: LinhaDeCaso }) {
  return (
    <>
      <span className="tabular-nums">{formatarData(c.chegou_em)}</span>
      {c.chegada_aproximada && <small className="ml-1 text-muted">aprox.</small>}
    </>
  )
}

function Tempo({ c }: { c: LinhaDeCaso }) {
  return (
    <>
      <span className="tabular-nums">{formatarTempo(c.tempo_na_fila_horas)}</span>
      {c.atrasado && (
        <span className="mt-1 flex items-center gap-1 font-bold text-warn">
          <Icone nome="prazo" />
          Parado há 5 dias ou mais
        </span>
      )}
    </>
  )
}

function Sinais({ c }: { c: LinhaDeCaso }) {
  return (
    <div className="mt-1 flex flex-wrap gap-2">
      {c.entra_por_politica && <span className="chip bg-line text-muted">Política 100%</span>}
      {c.e_metodologico && (
        <span className="chip bg-warn-soft text-warn">Revisão obrigatória pelo motor</span>
      )}
    </div>
  )
}

function Decisao({ c }: { c: LinhaDeCaso }) {
  if (!c.decidido_em) return <span className="text-muted">—</span>
  return (
    <>
      <span className="block">{c.revisor}</span>
      <small className="block text-muted tabular-nums">{formatarData(c.decidido_em)}</small>
    </>
  )
}

function Abrir({ c, abrirCaso }: { c: LinhaDeCaso; abrirCaso?: (id: string) => void }) {
  if (!abrirCaso) return null
  return (
    <Botao
      variante="secundario"
      onClick={(e) => {
        e.stopPropagation()
        abrirCaso(c.CASO_ID)
      }}
    >
      Abrir
      <span className="sr-only"> {c.nome || c.email_do_aluno || c.CASO_ID}</span>
    </Botao>
  )
}

function Cartao({ c, abrirCaso }: { c: LinhaDeCaso; abrirCaso?: (id: string) => void }) {
  return (
    <li className="cartao" onClick={() => abrirCaso?.(c.CASO_ID)}>
      <div className="linha flex-wrap">
        <div className="min-w-0 flex-1">
          <Aluno c={c} />
        </div>
        <span className={classeDoStatus(c.status)}>{c.status_rotulo}</span>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
        <dt className="text-muted">Chegou em</dt>
        <dd className="m-0"><Chegada c={c} /></dd>
        <dt className="text-muted">Tempo na fila</dt>
        <dd className="m-0"><Tempo c={c} /></dd>
        <dt className="text-muted">Tipo</dt>
        <dd className="m-0">{c.tipo_rotulo}</dd>
        <dt className="text-muted">Situação do mês</dt>
        <dd className="m-0">{c.situacao_mes_rotulo}</dd>
        <dt className="text-muted">Dívidas</dt>
        <dd className="m-0 tabular-nums">{c.dividas}</dd>
        <dt className="text-muted">Método</dt>
        <dd className="m-0">{c.metodo} · {c.status_metodo}</dd>
        <dt className="text-muted">Motivo da revisão</dt>
        <dd className="m-0">{c.motivo_rotulo}<Sinais c={c} /></dd>
        {c.decidido_em && (
          <>
            <dt className="text-muted">Revisor e decisão</dt>
            <dd className="m-0"><Decisao c={c} /></dd>
          </>
        )}
      </dl>
      <Abrir c={c} abrirCaso={abrirCaso} />
    </li>
  )
}

export default function TabelaDeCasos({ itens, ordem, aoOrdenar, abrirCaso }: TabelaDeCasosProps) {
  return (
    <>
      <div data-testid="tabela-de-casos" className="hidden max-h-[70vh] overflow-auto md:block">
        <table className="w-full border-collapse text-left">
          <thead>
            {/* `top-0`: o cabeçalho fica fixo dentro do contêiner de rolagem. */}
            <tr className="sticky top-0 bg-surface">
              {COLUNAS.map(({ titulo, campo }) => {
                const ativa = campo !== undefined && campo === ordem.campo
                return (
                  <th
                    key={titulo}
                    scope="col"
                    className="border-b-2 border-line px-2 py-2 align-bottom"
                    aria-sort={
                      campo === undefined
                        ? undefined
                        : ativa
                          ? ordem.direcao === 'asc'
                            ? 'ascending'
                            : 'descending'
                          : 'none'
                    }
                  >
                    {campo ? (
                      <button
                        type="button"
                        className="font-bold"
                        onClick={() => aoOrdenar(campo)}
                      >
                        {titulo}
                        {ativa && <span aria-hidden="true">{ordem.direcao === 'asc' ? ' ▲' : ' ▼'}</span>}
                      </button>
                    ) : (
                      titulo
                    )}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {itens.map((c) => (
              <tr
                key={c.CASO_ID}
                className="cursor-pointer border-b border-line align-top hover:bg-line"
                onClick={() => abrirCaso?.(c.CASO_ID)}
              >
                <td className="px-2 py-2"><Aluno c={c} /></td>
                <td className="px-2 py-2"><Chegada c={c} /></td>
                <td className="px-2 py-2"><Tempo c={c} /></td>
                <td className="px-2 py-2">
                  <span className={classeDoStatus(c.status)}>{c.status_rotulo}</span>
                </td>
                <td className="px-2 py-2">{c.tipo_rotulo}</td>
                <td className="px-2 py-2">{c.situacao_mes_rotulo}</td>
                <td className="px-2 py-2 tabular-nums">{c.dividas}</td>
                <td className="px-2 py-2">
                  {c.metodo}
                  <small className="block text-muted">{c.status_metodo}</small>
                </td>
                <td className="px-2 py-2">
                  {c.motivo_rotulo}
                  <Sinais c={c} />
                </td>
                <td className="px-2 py-2"><Decisao c={c} /></td>
                <td className="px-2 py-2"><Abrir c={c} abrirCaso={abrirCaso} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul data-testid="cartoes-de-casos" className="lista list-none p-0 md:hidden">
        {itens.map((c) => (
          <Cartao key={c.CASO_ID} c={c} abrirCaso={abrirCaso} />
        ))}
      </ul>
    </>
  )
}
