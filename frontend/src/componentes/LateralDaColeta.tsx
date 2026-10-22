/**
 * A lateral das telas de coleta (pergunta, fichas, formulário) — `T-421`.
 *
 * Em cima, o andamento de sempre, com as três etapas; embaixo, as cinco partes
 * do questionário como progresso secundário (`RF-100`). Quem diz em que parte o
 * aluno está é o servidor; o cliente só desenha.
 */
import type { ParteDaTrilha } from '../tipos'
import { AndamentoDoPlano } from './AcompanhamentoDoPlano'
import TrilhaDaColeta from './TrilhaDaColeta'

export default function LateralDaColeta({ trilha }: { trilha?: readonly ParteDaTrilha[] | null }) {
  return (
    <div className="flex flex-col gap-4">
      <AndamentoDoPlano fase="coleta" />
      {trilha && <TrilhaDaColeta trilha={trilha} />}
    </div>
  )
}
