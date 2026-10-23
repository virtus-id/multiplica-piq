/**
 * Os atalhos para as listas de fichas, dentro da seção a que cada uma
 * pertence — `T-425`, reorganizado em `T-426`.
 *
 * É o que a tela de progresso oferecia e "Minhas respostas" não: adicionar,
 * remover ou abrir cada ficha (`RF-53`, `AC-04`). Antes eram quatro botões
 * soltos acima da página; agora cada botão fica no cabeçalho da seção cujas
 * perguntas ele cria — dívidas na parte 5, despesas e rendas na parte 3 —,
 * com a mesma redação ("Gerenciar …"). Quais listas estão abertas quem diz é
 * o servidor (`GET /caso/{id}/escopos`, `RF-52`); falha aqui só esconde os
 * atalhos, e as dívidas seguem acessíveis.
 */
import { useEffect, useState } from 'react'

import { listarEscopos } from '../../services/api'
import { TITULOS_POR_ESCOPO } from '../../telas/TelaFichas'
import Botao from '../Botao'
import Icone from '../Icone'

/** A parte do questionário em que cada lista de fichas nasce, e a ordem dos botões. */
const ESCOPOS_DA_PARTE: Readonly<Record<number, readonly string[]>> = {
  3: ['ITEM_DESPESA', 'DESPESA_NAO_MENSAL_ID', 'RENDA_ADICIONAL_ID', 'RECURSO_EXTRAORDINARIO_ID'],
  5: ['DIVIDA_ID'],
}

/** As listas abertas do caso. Sem `ativo`, não pergunta nada ao servidor. */
export function useEscoposAbertos(casoId: string, ativo: boolean): string[] {
  const [abertos, setAbertos] = useState<string[]>([])

  useEffect(() => {
    if (!ativo) return
    let vivo = true
    listarEscopos(casoId)
      .then((dados) => {
        if (vivo) setAbertos(dados.escopos.filter((e) => e.aberto).map((e) => e.escopo))
      })
      .catch(() => undefined)
    return () => {
      vivo = false
    }
  }, [casoId, ativo])

  return abertos
}

export default function AtalhosDaSecao({
  bloco,
  abertos,
  aoAbrir,
}: {
  bloco: number
  abertos: readonly string[]
  aoAbrir: (escopo: string) => void
}) {
  // As dívidas têm botão sempre (é o CRUD de `RF-53`); as demais, só se abertas.
  const escopos = (ESCOPOS_DA_PARTE[bloco] ?? []).filter(
    (escopo) => (escopo === 'DIVIDA_ID' || abertos.includes(escopo)) && TITULOS_POR_ESCOPO[escopo],
  )
  if (escopos.length === 0) return null

  return (
    <div role="group" aria-label="Adicionar, remover ou abrir fichas" className="flex flex-wrap gap-2">
      {escopos.map((escopo) => (
        <Botao
          key={escopo}
          variante="secundario"
          className="!min-h-0 !w-auto !px-3 !py-1.5 !text-sm"
          onClick={() => aoAbrir(escopo)}
        >
          <Icone nome="editar" /> Gerenciar {TITULOS_POR_ESCOPO[escopo].tituloPlural.toLowerCase()}
        </Botao>
      ))}
    </div>
  )
}
