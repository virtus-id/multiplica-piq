/**
 * "Dívidas e despesas cadastradas" — o acesso às listas de fichas — `T-425`.
 *
 * É o que a tela de progresso oferecia e "Minhas respostas" não: adicionar,
 * remover ou abrir cada ficha (`RF-53`, `AC-04`). Quais listas estão abertas
 * quem diz é o servidor (`GET /caso/{id}/escopos`, `RF-52`); falha aqui só
 * esconde os atalhos das listas extras, e as dívidas seguem acessíveis.
 */
import { useEffect, useState } from 'react'

import { listarEscopos } from '../../services/api'
import { TITULOS_POR_ESCOPO } from '../../telas/TelaFichas'
import Botao from '../Botao'

export default function AtalhosDasFichas({
  casoId,
  aoAbrir,
}: {
  casoId: string
  aoAbrir: (escopo: string) => void
}) {
  const [abertos, setAbertos] = useState<string[]>([])

  useEffect(() => {
    let ativo = true
    listarEscopos(casoId)
      .then((dados) => {
        if (ativo) setAbertos(dados.escopos.filter((e) => e.aberto).map((e) => e.escopo))
      })
      .catch(() => undefined)
    return () => {
      ativo = false
    }
  }, [casoId])

  const extras = abertos.filter((escopo) => escopo !== 'DIVIDA_ID' && TITULOS_POR_ESCOPO[escopo])

  return (
    <section className="cartao" aria-labelledby="titulo-das-fichas">
      <h2 id="titulo-das-fichas" className="m-0 font-serif text-[1.15rem] font-semibold">
        Dívidas e despesas cadastradas
      </h2>
      <p className="nota m-0">Adicione, remova ou abra cada ficha.</p>
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        <Botao variante="secundario" className="sm:!w-auto" onClick={() => aoAbrir('DIVIDA_ID')}>
          Ver e editar minhas dívidas
        </Botao>
        {extras.map((escopo) => (
          <Botao
            key={escopo}
            variante="secundario"
            className="sm:!w-auto"
            onClick={() => aoAbrir(escopo)}
          >
            Ver e editar: {TITULOS_POR_ESCOPO[escopo].tituloPlural.toLowerCase()}
          </Botao>
        ))}
      </div>
    </section>
  )
}
