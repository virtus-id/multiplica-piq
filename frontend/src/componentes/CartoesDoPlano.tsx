/**
 * A ação que mexe no plano ainda em conferência — `RF-115`, `RF-120` (T-344).
 * "Pedir plano novo" depois da entrega saiu (`RF-409`, T-388).
 *
 * **Um lugar só.** O aluno chega pelo Início e também por "Minhas respostas":
 * as duas telas oferecem a mesma ação, com a mesma confirmação. Cada tela só
 * diz o que fazer DEPOIS (`aoRetirar`); a regra — quando a ação existe — é do
 * servidor (`pode_retomar_edicao`).
 *
 * **Confirmação em linha, nunca em um `window.confirm`.** O texto da
 * confirmação é parte do requisito (`AC-184`): o aluno precisa saber que o
 * plano será conferido de novo e que isso pode demorar na fila.
 */
import { useState } from 'react'

import { retomarEdicao } from '../services/api'
import Botao from './Botao'

/** Roda a ação, com o estado de "confirmando", "enviando" e o erro do servidor. */
function useAcaoConfirmada(executar: () => Promise<unknown>, depois: () => void, erroPadrao: string) {
  const [confirmando, setConfirmando] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  async function confirmar() {
    setEnviando(true)
    setErro(null)
    try {
      await executar()
      setConfirmando(false)
      depois()
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : erroPadrao)
    } finally {
      setEnviando(false)
    }
  }

  return { confirmando, setConfirmando, enviando, erro, confirmar }
}

interface CartaoRetirarProps {
  casoId: string
  /** O que o cartão diz sobre a conferência — varia por tela. */
  explicacao: string
  /** O caso voltou à coleta: a tela relê ou leva a "Minhas respostas". */
  aoRetirar: () => void
}

/** "Quero editar minhas respostas" — retira o plano da conferência (`RF-115`). */
export function CartaoRetirarDaConferencia({ casoId, explicacao, aoRetirar }: CartaoRetirarProps) {
  const acao = useAcaoConfirmada(
    () => retomarEdicao(casoId),
    aoRetirar,
    'Não foi possível retirar o plano agora.',
  )

  return (
    <section className="cartao" aria-label="Plano em conferência">
      <strong>Seu plano está em conferência.</strong>
      <p className="nota">{explicacao}</p>

      {!acao.confirmando && (
        <Botao variante="discreto" className="self-start" onClick={() => acao.setConfirmando(true)}>
          Quero editar minhas respostas
        </Botao>
      )}

      {acao.confirmando && (
        <div className="flex flex-col gap-2" role="group" aria-label="Confirmar a retirada">
          <p>
            <strong>
              Seu plano sai da conferência. Quando você enviar de novo, ele volta para a fila.
            </strong>
          </p>
          <div className="flex flex-wrap gap-2">
            <Botao onClick={() => void acao.confirmar()} disabled={acao.enviando}>
              Retirar o plano e editar
            </Botao>
            <Botao
              variante="discreto"
              onClick={() => acao.setConfirmando(false)}
              disabled={acao.enviando}
            >
              Cancelar
            </Botao>
          </div>
        </div>
      )}

      {acao.erro && (
        <p role="alert" className="aviso-erro">
          {acao.erro}
        </p>
      )}
    </section>
  )
}
