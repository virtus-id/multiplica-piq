/**
 * A faixa de status de "Minhas respostas" — `T-422`.
 *
 * O MESMO componente nos dois modos, com as mesmas proporções: muda o texto
 * e a ação à direita. O estado vem do servidor (`editavel`,
 * `pode_retomar_edicao`) e da fase; esta faixa nunca diz que o plano já foi
 * calculado enquanto ele está em elaboração e análise.
 *
 * "Editar respostas" não grava nada: abre a confirmação, e só depois dela o
 * plano sai da conferência (`RF-115`) — a mesma regra e o mesmo texto de
 * antes.
 */
import { useState } from 'react'

import { retomarEdicao } from '../../services/api'
import Botao from '../Botao'
import Icone from '../Icone'

interface BannerDeRespostasProps {
  casoId: string
  modo: 'visualizar' | 'editar'
  /** O plano já foi liberado: as respostas ficam só para consulta. */
  planoLiberado: boolean
  /** `pode_retomar_edicao`, do servidor: sem ele não há "Editar respostas". */
  podeEditar: boolean
  /** O plano saiu da conferência: a tela relê e passa ao modo de edição. */
  aoRetirar: () => void
}

export default function BannerDeRespostas({
  casoId,
  modo,
  planoLiberado,
  podeEditar,
  aoRetirar,
}: BannerDeRespostasProps) {
  const [confirmando, setConfirmando] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  async function retirar() {
    setEnviando(true)
    setErro(null)
    try {
      await retomarEdicao(casoId)
      setConfirmando(false)
      aoRetirar()
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : 'Não foi possível retirar o plano agora.')
    } finally {
      setEnviando(false)
    }
  }

  const titulo =
    modo === 'editar'
      ? 'Revise suas informações'
      : planoLiberado
        ? 'Seu plano de quitação já foi liberado.'
        : 'Seu plano está em elaboração e análise.'
  const texto =
    modo === 'editar'
      ? 'Faça as correções necessárias e salve suas alterações ao finalizar.'
      : planoLiberado
        ? 'Estas são as informações usadas na elaboração do seu plano. Elas ficam só para consulta.'
        : 'Nossa equipe está analisando suas informações para preparar seu plano de quitação.'

  return (
    <section
      aria-label="Situação do plano"
      className="flex flex-col gap-3 rounded-piq border border-line bg-accent-soft px-4 py-3 lg:px-6"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <span className="selo">
            <Icone nome={modo === 'editar' ? 'editar' : 'conferencia'} />
          </span>
          <div className="flex min-w-0 flex-col gap-0.5">
            <strong>{titulo}</strong>
            <span className="nota m-0">{texto}</span>
          </div>
        </div>
        {modo === 'visualizar' && podeEditar && !confirmando && (
          <Botao
            variante="secundario"
            className="sm:!w-auto sm:flex-none"
            onClick={() => setConfirmando(true)}
          >
            <Icone nome="editar" /> Editar respostas
          </Botao>
        )}
      </div>

      {confirmando && (
        <div role="alertdialog" aria-labelledby="titulo-alterar-respostas" className="flex flex-col gap-2">
          <strong id="titulo-alterar-respostas">Alterar suas informações?</strong>
          <p className="m-0">
            Seu plano sai da conferência. Quando você enviar de novo, ele volta para a fila e passa
            por uma nova conferência, o que poderá alterar o prazo de liberação.
          </p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Botao className="sm:!w-auto" onClick={() => setConfirmando(false)} disabled={enviando}>
              Continuar aguardando
            </Botao>
            <Botao
              variante="secundario"
              className="sm:!w-auto"
              onClick={() => void retirar()}
              disabled={enviando}
            >
              Editar respostas
            </Botao>
          </div>
        </div>
      )}

      {erro && (
        <p role="alert" className="aviso-erro">
          {erro}
        </p>
      )}
    </section>
  )
}
