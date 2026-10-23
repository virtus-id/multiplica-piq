/**
 * O layout compartilhado de "Minhas respostas" — `T-422` (`RF-433`).
 *
 * Uma página só, vertical, com TODAS as partes em sequência: cabeçalho da
 * seção, perguntas e respostas, e o índice fixo no topo que leva a cada uma
 * por âncora (rolagem suave, sem trocar de página nem desmontar nada). O
 * mesmo layout serve à visualização e à edição: o que muda é só o conteúdo
 * da linha (`renderLinha`) e as ações da casca.
 *
 * Nada aqui decide o que aparece: as partes e as respostas vêm do servidor
 * (`GET /caso/{id}/respostas`), inclusive as partes vazias (`AC-101`).
 */
import { Fragment, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type { ParteDasRespostas, RespostaDada } from '../../tipos'
import {
  agruparPorItem,
  chaveDaResposta,
  contagemDaParte,
  normalizar,
  textoDaResposta,
} from './textoDasRespostas'

type Modo = 'visualizar' | 'editar'

/** O que a linha precisa saber do layout para se desenhar. */
export interface ContextoDaLinha {
  /** O `id` do elemento, alvo da busca. */
  domId: string
  /** Realce temporário do resultado da busca. */
  destacada: boolean
  /** Ocupa as duas colunas (pergunta ou resposta longa, ou campo de edição). */
  larga: boolean
}

interface PaginaDeRespostasProps {
  modo: Modo
  partes: readonly ParteDasRespostas[]
  /** A faixa de status, logo abaixo do cabeçalho. */
  banner: ReactNode
  /** Muda a cada gravação: as linhas são refeitas com o que o servidor devolveu. */
  versao: number
  renderLinha: (resposta: RespostaDada, contexto: ContextoDaLinha) => ReactNode
}

function domIdDaLinha(bloco: number, resposta: RespostaDada): string {
  return `resposta-${bloco}-${resposta.ID}-${resposta.item_id ?? 'caso'}`
}

function reduzirMovimento(): boolean {
  return typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false
}

function rolarPara(id: string, bloco: 'start' | 'center' = 'start') {
  document.getElementById(id)?.scrollIntoView({
    behavior: reduzirMovimento() ? 'auto' : 'smooth',
    block: bloco,
  })
}

/**
 * O texto curto de cada parte no índice (`T-424`), para os cinco caberem numa
 * linha. É redação do produto, ligada ao número da parte; o título completo
 * segue na seção, no nome acessível e na dica do botão.
 */
const ROTULO_CURTO: Readonly<Record<number, string>> = {
  1: 'Compromisso',
  2: 'Controle dos gastos',
  3: 'Entradas e saídas',
  4: 'Salário e margem',
  5: 'Dívidas',
}

/**
 * O índice horizontal fixo no topo. São botões, não links com `#`: o `#` é da
 * rota do aplicativo, e um link de âncora a trocaria.
 */
function IndiceDeSecoes({
  partes,
  ativa,
  aoEscolher,
}: {
  partes: readonly ParteDasRespostas[]
  ativa: number | undefined
  aoEscolher: (bloco: number) => void
}) {
  const lista = useRef<HTMLUListElement>(null)
  const primeira = useRef(true)

  // O item ativo fica à vista no celular, onde o índice rola na horizontal.
  // Não na carga: ali a página não deve se mexer.
  useEffect(() => {
    if (primeira.current) {
      primeira.current = false
      return
    }
    lista.current
      ?.querySelector<HTMLElement>('[aria-current="true"]')
      ?.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'auto' })
  }, [ativa])

  return (
    <nav
      aria-label="Seções das respostas"
      className="sticky top-0 z-20 -mx-5 border-b border-line bg-bg px-5 py-2"
    >
      <ul className="m-0 flex list-none gap-1.5 overflow-x-auto p-0 lg:grid lg:grid-cols-5 lg:overflow-visible">
        {partes.map((parte) => {
          const eAtiva = parte.bloco === ativa
          return (
            <li key={parte.bloco} className="flex-none lg:flex-auto">
              <button
                type="button"
                aria-current={eAtiva ? 'true' : undefined}
                // O nome acessível e a dica são o título completo; o texto curto é
                // só para o índice caber numa linha.
                aria-label={parte.rotulo}
                title={parte.rotulo}
                onClick={() => aoEscolher(parte.bloco)}
                className={`w-full whitespace-nowrap rounded-full border px-2.5 py-1 text-center text-[0.82rem] font-bold ${
                  eAtiva
                    ? 'border-accent bg-accent-soft text-accent'
                    : 'border-line bg-surface text-muted'
                }`}
              >
                {ROTULO_CURTO[parte.bloco] ?? parte.rotulo}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

/** A busca por pergunta ou resposta — leve, sem dependência. */
function BuscaDeRespostas({
  partes,
  aoEscolher,
}: {
  partes: readonly ParteDasRespostas[]
  aoEscolher: (bloco: number, resposta: RespostaDada) => void
}) {
  const [termo, setTermo] = useState('')

  const resultados = useMemo(() => {
    const alvo = normalizar(termo.trim())
    if (alvo.length < 2) return []
    const achados: { bloco: number; rotuloDaParte: string; resposta: RespostaDada }[] = []
    for (const parte of partes) {
      for (const resposta of parte.respondidas) {
        if (normalizar(`${resposta.enunciado} ${textoDaResposta(resposta)}`).includes(alvo)) {
          achados.push({ bloco: parte.bloco, rotuloDaParte: parte.rotulo, resposta })
        }
      }
    }
    return achados
  }, [termo, partes])

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor="busca-de-respostas" className="sr-only">
        Buscar pergunta ou resposta
      </label>
      <input
        id="busca-de-respostas"
        type="search"
        className="campo-texto"
        placeholder="Buscar pergunta ou resposta..."
        value={termo}
        onChange={(e) => setTermo(e.target.value)}
      />
      {termo.trim().length >= 2 && (
        <div role="status" className="rounded-piq border border-line bg-surface">
          {resultados.length === 0 ? (
            <p className="nota m-0 px-3 py-2">Nada encontrado.</p>
          ) : (
            <ul className="m-0 max-h-72 list-none overflow-y-auto p-0">
              {resultados.slice(0, 12).map(({ bloco, rotuloDaParte, resposta }) => (
                <li key={`${bloco}-${chaveDaResposta(resposta)}`} className="border-b border-line last:border-b-0">
                  <button
                    type="button"
                    className="block w-full px-3 py-2 text-left"
                    onClick={() => {
                      aoEscolher(bloco, resposta)
                      setTermo('')
                    }}
                  >
                    <small className="block text-muted">{rotuloDaParte}</small>
                    <span className="block font-bold">{resposta.enunciado}</span>
                    <small className="block text-muted">{textoDaResposta(resposta)}</small>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

function eLarga(resposta: RespostaDada, modo: Modo): boolean {
  return (
    modo === 'editar' || resposta.enunciado.length > 80 || textoDaResposta(resposta).length > 48
  )
}

function SecaoDeRespostas({
  parte,
  modo,
  versao,
  destacada,
  renderLinha,
}: {
  parte: ParteDasRespostas
  modo: Modo
  versao: number
  destacada: string | null
  renderLinha: PaginaDeRespostasProps['renderLinha']
}) {
  const idDoTitulo = `titulo-da-secao-${parte.bloco}`
  return (
    <section
      id={`secao-${parte.bloco}`}
      data-bloco={parte.bloco}
      aria-labelledby={idDoTitulo}
      className="scroll-mt-24 rounded-piq border border-line bg-surface p-4 lg:p-6"
    >
      <header className="mb-3 flex items-start gap-3 border-b border-line pb-3">
        <span
          aria-hidden="true"
          className="grid h-8 w-8 flex-none place-items-center rounded-full bg-accent-soft font-bold text-accent"
        >
          {parte.bloco}
        </span>
        <div className="min-w-0">
          <h2 id={idDoTitulo} className="m-0">
            {parte.rotulo}
          </h2>
          <small className="block text-muted">{contagemDaParte(parte)}</small>
        </div>
      </header>

      {parte.respondidas.length === 0 ? (
        // `AC-101`: a parte vazia DIZ que está vazia.
        <p className="nota m-0">Você ainda não respondeu nada desta parte.</p>
      ) : (
        <div className="flex flex-col gap-4">
          {agruparPorItem(parte.respondidas).map((grupo) => (
            <div key={grupo.itemId ?? 'soltas'} className={grupo.titulo ? 'border-t border-line pt-3' : ''}>
              {grupo.titulo && <h3 className="eyebrow m-0 mb-1">{grupo.titulo}</h3>}
              <ul className="m-0 grid list-none gap-x-10 p-0 md:grid-cols-2">
                {grupo.respostas.map((resposta) => {
                  const domId = domIdDaLinha(parte.bloco, resposta)
                  return (
                    <Fragment key={`${chaveDaResposta(resposta)}#${versao}`}>
                      {renderLinha(resposta, {
                        domId,
                        destacada: destacada === domId,
                        larga: eLarga(resposta, modo),
                      })}
                    </Fragment>
                  )
                })}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default function PaginaDeRespostas({
  modo,
  partes,
  banner,
  versao,
  renderLinha,
}: PaginaDeRespostasProps) {
  const [ativa, setAtiva] = useState<number | undefined>(partes[0]?.bloco)
  const [destacada, setDestacada] = useState<string | null>(null)

  // A seção visível vira a ativa do índice. Uma faixa horizontal logo abaixo do
  // índice fixo: a seção cujo começo entra nela passa a ser a atual.
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return
    const visiveis = new Set<number>()
    const observador = new IntersectionObserver(
      (entradas) => {
        for (const entrada of entradas) {
          const bloco = Number((entrada.target as HTMLElement).dataset.bloco)
          if (entrada.isIntersecting) visiveis.add(bloco)
          else visiveis.delete(bloco)
        }
        if (visiveis.size > 0) setAtiva(Math.max(...visiveis))
      },
      { rootMargin: '-140px 0px -45% 0px' },
    )
    document.querySelectorAll('[data-bloco]').forEach((secao) => observador.observe(secao))

    // No fim da página a última seção pode ser curta demais para entrar na faixa.
    function noFimDaPagina() {
      const chegou = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4
      const ultima = partes[partes.length - 1]
      if (chegou && ultima) setAtiva(ultima.bloco)
    }
    window.addEventListener('scroll', noFimDaPagina, { passive: true })
    return () => {
      observador.disconnect()
      window.removeEventListener('scroll', noFimDaPagina)
    }
  }, [partes])

  const irParaSecao = useCallback((bloco: number) => {
    setAtiva(bloco)
    rolarPara(`secao-${bloco}`)
  }, [])

  const irParaResposta = useCallback((bloco: number, resposta: RespostaDada) => {
    const domId = domIdDaLinha(bloco, resposta)
    setAtiva(bloco)
    rolarPara(domId, 'center')
    setDestacada(domId)
    window.setTimeout(() => setDestacada((atual) => (atual === domId ? null : atual)), 2500)
  }, [])

  return (
    <div className="flex flex-col gap-4">
      {banner}
      <IndiceDeSecoes partes={partes} ativa={ativa} aoEscolher={irParaSecao} />
      <BuscaDeRespostas partes={partes} aoEscolher={irParaResposta} />
      {partes.map((parte) => (
        <SecaoDeRespostas
          key={parte.bloco}
          parte={parte}
          modo={modo}
          versao={versao}
          destacada={destacada}
          renderLinha={renderLinha}
        />
      ))}
    </div>
  )
}
