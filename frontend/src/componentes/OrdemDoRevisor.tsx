/**
 * Seção "Ordem de quitação" da conferência — `RF-548`, `AC-569`, `AC-570`
 * (T-597).
 *
 * A lista é a **ordem de ataque** vigente (a sequência em que as dívidas
 * recebem o valor extra), como o servidor a lê do snapshot. Mover uma dívida
 * muda só a lista na tela; quem recalcula é "Recalcular nesta ordem", que
 * chama `POST /api/revisao/caso/{id}/ordem`. Subir/descer em vez de arrastar:
 * operável por teclado sem biblioteca (`R18.2`).
 *
 * Nenhuma conta aqui: prazo e custo, antes e depois, são os da resposta do
 * servidor (`AC-42`). `editavel` também é veredito dele.
 */
import { useEffect, useState } from 'react'

import {
  type OrdemNaConferencia,
  type PrazoECusto,
  type ResultadoDoAjusteDaOrdem,
  ajustarOrdem,
} from '../services/api'
import Botao from './Botao'

interface OrdemDoRevisorProps {
  casoId: string
  ordem: OrdemNaConferencia
  ultimoAjuste: ResultadoDoAjusteDaOrdem | null
  aoAjustar: (resultado: ResultadoDoAjusteDaOrdem) => void
}

function textoDoPrazo({ prazo }: PrazoECusto): string {
  return prazo.estourou_horizonte ? 'não quita no horizonte' : `${prazo.meses} meses`
}

function idDoBotao(divida: string, direcao: 'subir' | 'descer'): string {
  return `ordem-${divida}-${direcao}`
}

export default function OrdemDoRevisor({
  casoId,
  ordem,
  ultimoAjuste,
  aoAjustar,
}: OrdemDoRevisorProps) {
  const [lista, setLista] = useState(ordem.vigente)
  const [motivo, setMotivo] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [anuncio, setAnuncio] = useState('')
  // O botão que chegou à ponta fica desativado e perde o foco; o foco vai
  // para o outro botão da mesma dívida.
  const [foco, setFoco] = useState<string | null>(null)

  useEffect(() => {
    if (foco) document.getElementById(foco)?.focus()
  }, [foco, lista])

  const igualAVigente = lista.every((d, i) => d.DIVIDA_ID === ordem.vigente[i]?.DIVIDA_ID)
  const podeRecalcular = !enviando && !igualAVigente && motivo.trim() !== ''

  function mover(indice: number, passo: -1 | 1) {
    const destino = indice + passo
    const nova = [...lista]
    ;[nova[indice], nova[destino]] = [nova[destino], nova[indice]]
    setLista(nova)
    const divida = nova[destino]
    setAnuncio(`${divida.nome}: posição ${destino + 1} de ${nova.length}.`)
    const naPonta = destino === 0 || destino === nova.length - 1
    setFoco(
      naPonta
        ? idDoBotao(divida.DIVIDA_ID, passo === -1 ? 'descer' : 'subir')
        : idDoBotao(divida.DIVIDA_ID, passo === -1 ? 'subir' : 'descer'),
    )
  }

  async function recalcular(ids: string[], motivoEnviado: string) {
    setEnviando(true)
    setErro(null)
    setAnuncio('Recalculando…')
    try {
      const resultado = await ajustarOrdem(casoId, ids, motivoEnviado)
      setAnuncio('Plano recalculado.')
      aoAjustar(resultado)
    } catch (falha) {
      // `409`/`422`: a frase é do servidor; lista e motivo ficam (`AC-570`).
      setAnuncio('')
      setErro(falha instanceof Error ? falha.message : 'Não foi possível recalcular.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="cartao" aria-labelledby="titulo-ordem-do-revisor">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="titulo-ordem-do-revisor" className="m-0">
          Ordem de quitação
        </h2>
        <span className={ordem.ajustada ? 'chip chip-atencao' : 'chip chip-mudo'}>
          {ordem.ajustada ? 'Ajustada na conferência' : 'Ordem do método'}
        </span>
      </div>
      <p className="nota m-0">A sequência em que as dívidas recebem o valor extra.</p>

      <ol className="m-0 flex list-none flex-col gap-2 p-0">
        {lista.map((divida, i) => (
          <li
            key={divida.DIVIDA_ID}
            className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-2"
          >
            <span>
              <span className="tabular-nums text-muted">{i + 1}º</span> {divida.nome}
            </span>
            {ordem.editavel && (
              <span className="flex gap-2">
                <Botao
                  id={idDoBotao(divida.DIVIDA_ID, 'subir')}
                  type="button"
                  variante="discreto"
                  className="!w-auto"
                  aria-label={`Subir ${divida.nome}`}
                  disabled={enviando || i === 0}
                  onClick={() => mover(i, -1)}
                >
                  Subir
                </Botao>
                <Botao
                  id={idDoBotao(divida.DIVIDA_ID, 'descer')}
                  type="button"
                  variante="discreto"
                  className="!w-auto"
                  aria-label={`Descer ${divida.nome}`}
                  disabled={enviando || i === lista.length - 1}
                  onClick={() => mover(i, 1)}
                >
                  Descer
                </Botao>
              </span>
            )}
          </li>
        ))}
      </ol>

      {ordem.editavel && (
        <>
          <div className="field">
            <label htmlFor="motivo-da-ordem">Motivo interno</label>
            <input
              id="motivo-da-ordem"
              type="text"
              className="campo-texto"
              aria-describedby="motivo-da-ordem-nota"
              value={motivo}
              disabled={enviando}
              onChange={(e) => setMotivo(e.target.value)}
            />
            <p id="motivo-da-ordem-nota" className="nota">
              Obrigatório para recalcular. Fica só na trilha do caso; o aluno não lê.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Botao
              type="button"
              className="flex-1"
              disabled={!podeRecalcular}
              onClick={() => void recalcular(lista.map((d) => d.DIVIDA_ID), motivo.trim())}
            >
              Recalcular nesta ordem
            </Botao>
            {/* `OQ-99`: voltar não pede motivo — a trilha registra autor e data. */}
            {ordem.ajustada && (
              <Botao
                type="button"
                variante="secundario"
                className="flex-1"
                disabled={enviando}
                onClick={() => void recalcular([], '')}
              >
                Voltar à ordem do método
              </Botao>
            )}
          </div>
        </>
      )}

      <p role="status" aria-live="polite" className="nota m-0">
        {anuncio}
      </p>
      {erro && (
        <p role="alert" className="aviso-erro">
          {erro}
        </p>
      )}

      {ultimoAjuste && (
        <table className="w-full text-left">
          <caption className="eyebrow text-left">Antes e depois do recálculo</caption>
          <thead>
            <tr>
              <td />
              <th scope="col">Antes</th>
              <th scope="col">Depois</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row" className="text-muted">
                Prazo
              </th>
              <td className="tabular-nums">{textoDoPrazo(ultimoAjuste.antes)}</td>
              <td className="tabular-nums font-bold">{textoDoPrazo(ultimoAjuste.depois)}</td>
            </tr>
            <tr>
              <th scope="row" className="text-muted">
                Custo total de juros
              </th>
              {[ultimoAjuste.antes, ultimoAjuste.depois].map((lado, i) => (
                <td key={lado.SNAPSHOT_ID} className={i === 1 ? 'tabular-nums font-bold' : 'tabular-nums'}>
                  {lado.custo_total_de_juros.valor}
                  {lado.custo_total_de_juros.motivo && (
                    <small className="block text-muted">{lado.custo_total_de_juros.motivo}</small>
                  )}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      )}
    </section>
  )
}
