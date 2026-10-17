/**
 * Tabela de casos do revisor — `RF-502`, `RF-505`, `RF-507` (T-409).
 *
 * A partir de 768px é tabela com cabeçalho fixo; abaixo disso, a mesma
 * linha vira cartão (sem rolagem horizontal a 360px). Os dois são
 * renderizados e o CSS esconde um — por isso cada um tem o seu `data-testid`.
 *
 * Os sinais `entra_por_politica`/`e_metodologico` não aparecem aqui
 * (T-412); nunca serão combinados num só (`AC-28`). Status chega em código,
 * mas a tela só mostra `status_rotulo`.
 *
 * Compacta (`RF-508`, T-411): `table-fixed` com larguras em %, uma linha por
 * caso, texto longo truncado com reticências e o texto inteiro em `title`.
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

/** `largura` em % da tabela (soma 100). */
const COLUNAS: { titulo: string; largura: number; campo?: CampoDeOrdem }[] = [
  { titulo: 'Aluno', largura: 22, campo: 'aluno' },
  { titulo: 'Tempo na fila', largura: 9, campo: 'tempo_na_fila' },
  { titulo: 'Status', largura: 11, campo: 'status' },
  { titulo: 'Fecha no mês', largura: 11, campo: 'situacao_mes' },
  { titulo: 'Dívidas', largura: 7, campo: 'dividas' },
  { titulo: 'Método', largura: 18, campo: 'metodo' },
  { titulo: 'Revisor e decisão', largura: 14, campo: 'decidido_em' },
  { titulo: 'Ação', largura: 8 },
]

const CELULA = 'truncate px-1.5 py-1'
const CHIP = 'chip !px-2 !py-0 !text-[11px]'

export function formatarData(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

/** Só os dias: `53` → "2 d"; menos de um dia → "0 d". */
export function formatarTempo(horas: number): string {
  return `${Math.floor(horas / 24)} d`
}

function classeDoStatus(status: string): string {
  if (status === 'AGUARDANDO_REVISAO') return `${CHIP} chip-atencao`
  if (status === 'PLANO_LIBERADO') return `${CHIP} chip-ok`
  return `${CHIP} chip-mudo`
}

/** Sempre com texto: a cor sozinha não basta (`RF-502`). */
function FechaNoMes({ c }: { c: LinhaDeCaso }) {
  return c.mes_negativo ? (
    <span className={`${CHIP} bg-bad-soft text-bad`}>Negativo</span>
  ) : (
    <span className={`${CHIP} chip-ok`}>Positivo</span>
  )
}

function Aluno({ c }: { c: LinhaDeCaso }) {
  const principal = c.nome || c.email_do_aluno || c.CASO_ID
  return (
    <>
      <span className="block truncate font-bold" title={principal}>{principal}</span>
      {c.nome && c.email_do_aluno && (
        <small className="block truncate text-[11px] leading-tight text-muted" title={c.email_do_aluno}>
          {c.email_do_aluno}
        </small>
      )}
    </>
  )
}

function Tempo({ c }: { c: LinhaDeCaso }) {
  return (
    <>
      <span className="tabular-nums">{formatarTempo(c.tempo_na_fila_horas)}</span>
      {c.atrasado && (
        // O ícone é decorativo (`aria-hidden`); o nome acessível vem do invólucro.
        <span
          role="img"
          aria-label="Parado há 5 dias ou mais"
          title="Parado há 5 dias ou mais"
          className="ml-1 inline-flex align-middle text-warn"
        >
          <Icone nome="prazo" />
        </span>
      )}
    </>
  )
}

function Decisao({ c }: { c: LinhaDeCaso }) {
  if (!c.decidido_em) return <span className="text-muted">—</span>
  return (
    <>
      <span className="block truncate" title={c.revisor ?? undefined}>{c.revisor}</span>
      <small className="block truncate text-[11px] leading-tight text-muted tabular-nums">{formatarData(c.decidido_em)}</small>
    </>
  )
}

function Abrir({ c, abrirCaso }: { c: LinhaDeCaso; abrirCaso?: (id: string) => void }) {
  if (!abrirCaso) return null
  return (
    <Botao
      variante="secundario"
      className="!min-h-0 !w-auto !px-2 !py-0.5 !text-xs"
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
        <dt className="text-muted">Tempo na fila</dt>
        <dd className="m-0"><Tempo c={c} /></dd>
        <dt className="text-muted">Fecha no mês</dt>
        <dd className="m-0"><FechaNoMes c={c} /></dd>
        <dt className="text-muted">Dívidas</dt>
        <dd className="m-0 tabular-nums">{c.dividas}</dd>
        <dt className="text-muted">Método</dt>
        <dd className="m-0">{c.metodo} · {c.status_metodo}</dd>
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
        <table className="w-full table-fixed border-collapse text-left text-xs">
          <colgroup>
            {COLUNAS.map(({ titulo, largura }) => (
              <col key={titulo} style={{ width: `${largura}%` }} />
            ))}
          </colgroup>
          <thead>
            {/* `top-0`: o cabeçalho fica fixo dentro do contêiner de rolagem. */}
            <tr className="sticky top-0 bg-surface">
              {COLUNAS.map(({ titulo, campo }) => {
                const ativa = campo !== undefined && campo === ordem.campo
                return (
                  <th
                    key={titulo}
                    scope="col"
                    className="truncate border-b-2 border-line px-1.5 py-1 align-bottom"
                    title={titulo}
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
                        className="max-w-full truncate font-bold"
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
                className="cursor-pointer border-b border-line align-middle hover:bg-line"
                onClick={() => abrirCaso?.(c.CASO_ID)}
              >
                <td className={CELULA}><Aluno c={c} /></td>
                <td className={CELULA}><Tempo c={c} /></td>
                <td className={CELULA}>
                  <span className={classeDoStatus(c.status)}>{c.status_rotulo}</span>
                </td>
                <td className={CELULA}><FechaNoMes c={c} /></td>
                <td className={`${CELULA} tabular-nums`}>{c.dividas}</td>
                <td className={CELULA} title={`${c.metodo} · ${c.status_metodo}`}>
                  {c.metodo}
                  <small className="block truncate text-[11px] leading-tight text-muted">{c.status_metodo}</small>
                </td>
                <td className={CELULA}><Decisao c={c} /></td>
                <td className={CELULA}><Abrir c={c} abrirCaso={abrirCaso} /></td>
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
