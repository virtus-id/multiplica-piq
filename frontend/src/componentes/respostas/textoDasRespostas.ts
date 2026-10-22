/**
 * Como uma resposta vira texto na tela "Minhas respostas" — `T-422`.
 *
 * Só apresentação: o servidor manda o valor cru (`0.08`, `2276.76`) e aqui ele
 * vira o que o aluno digitou ("8%", "R$ 2.276,76"). Nada é recalculado nem
 * inventado.
 */
import { formatarDecimalDoServidor, formatarTaxaDoServidor } from '../../mascaras'
import type { ParteDasRespostas, RespostaDada } from '../../tipos'

/**
 * `T-335`: só o que é número decimal; um rótulo ou um código passa intacto.
 */
export function exibir(valor: string, tipo: RespostaDada['tipo']): string {
  if (!/^\d+(\.\d+)?$/.test(valor)) return valor
  if (tipo === 'TAXA') return `${formatarTaxaDoServidor(valor)}%`
  if (tipo === 'MOEDA') return `R$ ${formatarDecimalDoServidor(valor)}`
  return valor
}

/**
 * O que o aluno respondeu, numa linha — `AC-100`.
 *
 * **"Não sei" é resposta, e aparece como tal** (`RF-11`): uma resposta antiga
 * continua legível. A vírgula que junta os valores é decisão desta camada.
 */
export function textoDaResposta(resposta: RespostaDada): string {
  if (resposta.respondida_como_nao_sei) return 'Você respondeu: não sei.'
  if (resposta.valores.length === 0) return 'Respondida.'
  return resposta.valores.map((valor) => exibir(valor, resposta.tipo)).join(', ')
}

/**
 * "N respostas de M perguntas" — a contagem de uma parte (`T-297`): numa ficha
 * repetível cada pergunta vale uma vez por item. O total inclui condicionais
 * que talvez nunca abram, por isso a frase não promete proporção.
 */
export function contagemDaParte(parte: ParteDasRespostas): string {
  const dadas = parte.respondidas.length
  const plural = dadas === 1 ? 'resposta' : 'respostas'
  return `${dadas} ${plural} de ${parte.total_de_perguntas} perguntas`
}

/** Um grupo de respostas: soltas (`item_id` nulo) ou de um item de ficha. */
export interface GrupoDeRespostas {
  itemId: string | null
  /** `null` para as soltas; "Dívida 1", "Dívida 2"… para as fichas. */
  titulo: string | null
  respostas: RespostaDada[]
}

/**
 * Junta as respostas de uma mesma ficha — `T-334`. O servidor entrega a
 * pergunta 1 de todas as dívidas, depois a 2…; aqui as soltas vão primeiro e
 * cada `item_id` vira um grupo, SEM reordenar as perguntas dentro dele. Os
 * dados de itens diferentes nunca se misturam.
 */
export function agruparPorItem(respondidas: readonly RespostaDada[]): GrupoDeRespostas[] {
  const soltas = respondidas.filter((r) => r.item_id === null)
  const porItem = new Map<string, RespostaDada[]>()
  for (const r of respondidas) {
    if (r.item_id !== null) porItem.set(r.item_id, [...(porItem.get(r.item_id) ?? []), r])
  }
  const grupos: GrupoDeRespostas[] = []
  if (soltas.length) grupos.push({ itemId: null, titulo: null, respostas: soltas })
  let n = 0
  for (const [itemId, respostas] of porItem) {
    n += 1
    grupos.push({
      itemId,
      titulo: `${itemId.startsWith('D') ? 'Dívida' : 'Item'} ${n}`,
      respostas,
    })
  }
  return grupos
}

/** A chave de uma resposta: a mesma pergunta rende uma linha por item. */
export function chaveDaResposta(resposta: RespostaDada): string {
  return `${resposta.ID}/${resposta.item_id ?? ''}`
}

/** Minúsculas e sem acento, para a busca achar "salario" em "Salário". */
export function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}
