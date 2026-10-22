/**
 * Uma pergunta e a sua resposta — `T-422`. Mesma linha nos dois modos:
 *
 * - **visualizar:** a pergunta em texto secundário e a resposta em destaque;
 * - **editar:** o campo de sempre (`CampoPergunta`, com máscaras, validações,
 *   seletores e "Não sei" onde ainda existe), no lugar do texto.
 *
 * No modo de edição o campo só é buscado quando a linha chega perto da tela
 * (`GET /caso/{id}/pergunta/{ID}`, a rota que já existe): cem campos de uma
 * vez seriam cem requisições antes de o aluno ler a primeira. A alteração
 * fica no rascunho da tela; quem grava é o "Salvar alterações", uma resposta
 * por vez, pela rota de sempre (`RF-69`).
 */
import { useEffect, useRef, useState } from 'react'

import { obterPergunta } from '../../services/api'
import type { Pergunta, RespostaDada } from '../../tipos'
import CampoPergunta from '../CampoPergunta'
import { valorInicial } from '../CamposDoItem'
import { textoDaResposta } from './textoDasRespostas'

/** O que o aluno mudou numa linha, ainda sem gravar. */
export interface Rascunho {
  valor: string | string[]
  naoSei: boolean
}

interface LinhaDaRespostaProps {
  casoId: string
  modo: 'visualizar' | 'editar'
  resposta: RespostaDada
  domId: string
  destacada: boolean
  larga: boolean
  rascunho?: Rascunho
  erro?: string
  aoAlterar: (rascunho: Rascunho) => void
}

export default function LinhaDaResposta({
  casoId,
  modo,
  resposta,
  domId,
  destacada,
  larga,
  rascunho,
  erro,
  aoAlterar,
}: LinhaDaRespostaProps) {
  const item = useRef<HTMLLIElement>(null)
  const [pergunta, setPergunta] = useState<Pergunta | null>(null)
  const [falhou, setFalhou] = useState(false)

  useEffect(() => {
    if (modo !== 'editar' || pergunta || falhou) return
    let ativo = true
    async function carregar() {
      try {
        const dados = await obterPergunta(casoId, resposta.ID, resposta.item_id ?? undefined)
        if (!ativo) return
        if (dados.pergunta) setPergunta(dados.pergunta)
        else setFalhou(true)
      } catch {
        if (ativo) setFalhou(true)
      }
    }
    if (typeof IntersectionObserver === 'undefined' || !item.current) {
      void carregar()
      return () => {
        ativo = false
      }
    }
    const observador = new IntersectionObserver(
      (entradas) => {
        if (entradas.some((entrada) => entrada.isIntersecting)) {
          observador.disconnect()
          void carregar()
        }
      },
      { rootMargin: '400px 0px' },
    )
    observador.observe(item.current)
    return () => {
      ativo = false
      observador.disconnect()
    }
  }, [modo, pergunta, falhou, casoId, resposta.ID, resposta.item_id])

  const classe = `scroll-mt-32 border-b border-line py-3 transition-colors ${
    destacada ? 'bg-accent-soft' : ''
  } ${larga ? 'md:col-span-2' : ''}`

  if (modo === 'editar' && pergunta) {
    const valor = rascunho?.valor ?? valorInicial(pergunta)
    const naoSei = rascunho?.naoSei ?? pergunta.respondida_como_nao_sei
    return (
      <li
        ref={item}
        id={domId}
        className={`${classe} [&_legend]:!text-base [&_label.font-serif]:!text-base`}
      >
        <CampoPergunta
          pergunta={pergunta}
          valor={valor}
          naoSei={naoSei}
          onValor={(novo) => aoAlterar({ valor: novo, naoSei: false })}
          onNaoSei={(marcado) => aoAlterar({ valor, naoSei: marcado })}
        />
        {rascunho && !erro && <small className="block text-muted">Alteração ainda não salva.</small>}
        {erro && (
          <p role="alert" className="aviso-erro">
            {erro}
          </p>
        )}
      </li>
    )
  }

  return (
    <li ref={item} id={domId} className={classe}>
      <small className="block text-muted">{resposta.enunciado}</small>
      <strong className="block break-words text-base">
        {textoDaResposta(resposta)}
        {resposta.respondida_como_nao_sei && (
          <span className="chip chip-mudo ml-2 align-middle">Não sei</span>
        )}
      </strong>
      {modo === 'editar' && (
        <small className="block text-muted">{falhou ? 'Não foi possível abrir este campo.' : 'Carregando o campo…'}</small>
      )}
    </li>
  )
}
