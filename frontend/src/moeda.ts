/**
 * Exibição de uma string decimal do servidor — sinal incluso. Fica fora dos
 * componentes porque a fotografia do mês e a lista de fichas mostram dinheiro
 * do mesmo jeito: nenhuma conta aqui, só a formatação (`RF-13`).
 */
import { formatarDecimalDoServidor } from './mascaras'

export const NAO_INFORMADO = 'não informado'

export function moeda(valor: string | null): string {
  if (valor === null) return NAO_INFORMADO
  const negativo = valor.startsWith('-')
  const texto = formatarDecimalDoServidor(negativo ? valor.slice(1) : valor) || '0,00'
  return `${negativo ? '−' : ''}R$ ${texto}`
}
