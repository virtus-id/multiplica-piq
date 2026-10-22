/**
 * O que o aluno já preencheu numa ficha curta, à vista na lista (`T-410`):
 * o valor em dinheiro e as escolhas (ex.: Fixo ou Variável). Só exibição —
 * o servidor manda `campos` com o `valor_atual` de cada pergunta, e nenhuma
 * regra mora aqui.
 */
import { moeda } from '../moeda'
import type { Pergunta } from '../tipos'

const EM_BRANCO = '—'

function textoDoCampo(campo: Pergunta): string {
  if (campo.respondida_como_nao_sei) return 'Não sei'
  const valor = campo.valor_atual
  if (valor === null || valor === '' || Array.isArray(valor)) return EM_BRANCO
  if (campo.tipo === 'MOEDA') return moeda(valor)
  return campo.opcoes.find((opcao) => opcao.valor_interno === valor)?.rotulo ?? valor
}

export default function ResumoDaFicha({ campos }: { campos: Pergunta[] }) {
  if (campos.length === 0) return null
  return (
    <div
      data-testid="resumo-da-ficha"
      className="order-last flex w-full items-center justify-end gap-2 sm:order-none sm:w-auto sm:shrink-0"
    >
      {campos.map((campo) => {
        const texto = textoDoCampo(campo)
        return campo.tipo === 'MOEDA' ? (
          <span key={campo.ID} className="font-bold tabular-nums" title={campo.enunciado}>
            {texto}
          </span>
        ) : (
          <span key={campo.ID} className="chip chip-mudo" title={campo.enunciado}>
            {texto}
          </span>
        )
      })}
    </div>
  )
}
