/**
 * O acompanhamento do plano enquanto ele é elaborado e conferido — `T-420`
 * (`RF-431`).
 *
 * É a tela que o aluno vê depois de enviar as respostas e antes da liberação.
 * Elaboração e análise são UMA etapa só: o cálculo automático e a conferência
 * da equipe formam um processo de entrega, e separá-los dizia ao aluno que o
 * plano "já estava calculado" quando ainda não podia ser lido (`EC-25`).
 *
 * **O que esta tela nunca afirma:** que o plano está pronto, calculado ou
 * quase aprovado; que alguém calcula à mão; nem datas, contagens regressivas
 * ou porcentagens. O prazo é uma estimativa operacional, escrita como tal.
 *
 * Nenhuma regra mora aqui: se a edição existe (`pode_retomar_edicao`) é o
 * servidor que diz, e retirar o plano da fila só acontece DEPOIS da
 * confirmação (`RF-115`).
 */
import { useState } from 'react'

import { retomarEdicao } from '../services/api'
import Botao from './Botao'
import Icone, { type NomeDoIcone } from './Icone'

type SituacaoDaEtapa = 'concluida' | 'atual' | 'pendente'

const ETAPAS: readonly {
  rotulo: string
  descricao: string
  situacao: SituacaoDaEtapa
  icone: NomeDoIcone
}[] = [
  {
    rotulo: 'Informações enviadas',
    descricao: 'Suas informações foram recebidas com sucesso.',
    situacao: 'concluida',
    icone: 'concluido',
  },
  {
    rotulo: 'Elaboração e análise do plano',
    descricao: 'Seu plano será calculado e analisado por um especialista antes da liberação.',
    situacao: 'atual',
    icone: 'conferencia',
  },
  {
    rotulo: 'Plano liberado',
    descricao: 'Você poderá acessar seu plano de quitação quando estiver pronto.',
    situacao: 'pendente',
    icone: 'prazo',
  },
]

const CLASSE_DO_MARCO: Readonly<Record<SituacaoDaEtapa, string>> = {
  concluida: 'bg-accent text-surface border-accent',
  atual: 'bg-accent-soft text-accent border-accent',
  pendente: 'bg-surface text-muted border-line',
}

/**
 * A linha do tempo, com exatamente três etapas. No computador é a coluna
 * lateral, com a descrição de cada uma; no celular vira uma faixa compacta
 * (só os rótulos), para não empurrar a informação principal para baixo.
 */
export function AndamentoDoPlano() {
  return (
    <nav aria-label="Andamento do plano">
      <ol className="m-0 grid list-none grid-cols-3 gap-2 p-0 lg:grid-cols-1 lg:gap-0">
        {ETAPAS.map((etapa, indice) => (
          <li
            key={etapa.rotulo}
            aria-current={etapa.situacao === 'atual' ? 'step' : undefined}
            className="relative flex flex-col items-center gap-1 text-center lg:flex-row lg:items-start lg:gap-3 lg:pb-6 lg:text-left"
          >
            {/* O fio que liga as etapas, só na vertical. */}
            {indice < ETAPAS.length - 1 && (
              <span
                aria-hidden="true"
                className={`absolute left-[17px] top-9 hidden h-[calc(100%-2.25rem)] w-0.5 lg:block ${
                  etapa.situacao === 'concluida' ? 'bg-accent' : 'bg-line'
                }`}
              />
            )}
            <span
              className={`grid h-9 w-9 flex-none place-items-center rounded-full border-2 ${CLASSE_DO_MARCO[etapa.situacao]}`}
            >
              <Icone nome={etapa.icone} />
            </span>
            <span className="flex min-w-0 flex-col gap-0.5">
              <strong className="text-[0.82rem] leading-tight lg:text-base">{etapa.rotulo}</strong>
              {etapa.situacao === 'atual' && (
                <span className="chip chip-ok self-center !px-2 !py-0 !text-[11px] lg:self-start">
                  Etapa atual
                </span>
              )}
              <span className="nota m-0 hidden lg:block">{etapa.descricao}</span>
            </span>
          </li>
        ))}
      </ol>
    </nav>
  )
}

interface AcompanhamentoDoPlanoProps {
  casoId: string
  /** `pode_retomar_edicao`, do servidor: sem ele não há "Editar minhas respostas". */
  podeEditar: boolean
  aoVerRespostas: () => void
  /** O plano saiu da conferência: a tela leva às respostas para corrigir. */
  aoEditarRespostas: () => void
}

export default function AcompanhamentoDoPlano({
  casoId,
  podeEditar,
  aoVerRespostas,
  aoEditarRespostas,
}: AcompanhamentoDoPlanoProps) {
  const [confirmando, setConfirmando] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  async function editar() {
    setEnviando(true)
    setErro(null)
    try {
      await retomarEdicao(casoId)
      setConfirmando(false)
      aoEditarRespostas()
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : 'Não foi possível retirar o plano agora.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <>
      <section className="cartao-destaque" aria-labelledby="titulo-preparando">
        <div className="flex items-start gap-3">
          <span className="selo">
            <Icone nome="conferencia" />
          </span>
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <span className="eyebrow">ELABORAÇÃO E ANÁLISE</span>
            <h2 id="titulo-preparando" className="grande m-0">
              Estamos preparando seu plano de quitação
            </h2>
          </div>
        </div>
        <p className="m-0">
          Nossa equipe irá analisar suas informações e conferir os cálculos para garantir que seu
          plano seja elaborado com cuidado antes da liberação.
        </p>
      </section>

      <section className="cartao" aria-label="Prazo e aviso">
        <div className="flex items-start gap-3">
          <span className="selo">
            <Icone nome="prazo" />
          </span>
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <strong>Prazo estimado: até 2 dias úteis</strong>
            <p className="m-0">Avisaremos por e-mail assim que seu plano estiver liberado.</p>
          </div>
        </div>
        <p className="nota m-0">
          Você não precisa fazer nada agora. Pode fechar esta página com tranquilidade.
        </p>
      </section>

      <section className="cartao" aria-labelledby="titulo-respostas">
        <h3 id="titulo-respostas" className="m-0 font-serif text-[1.15rem] font-semibold">
          Quer revisar suas informações?
        </h3>
        <p className="nota m-0">Você pode consultar ou corrigir as respostas que enviou.</p>

        {!confirmando && (
          <div className="flex flex-col gap-2 sm:flex-row">
            <Botao onClick={aoVerRespostas}>
              <Icone nome="ver" /> Ver minhas respostas
            </Botao>
            {podeEditar && (
              <Botao variante="secundario" onClick={() => setConfirmando(true)}>
                <Icone nome="editar" /> Editar minhas respostas
              </Botao>
            )}
          </div>
        )}

        {confirmando && (
          <div role="alertdialog" aria-labelledby="titulo-alterar" className="flex flex-col gap-2">
            <strong id="titulo-alterar">Alterar suas informações?</strong>
            <p className="m-0">
              Seu plano sai da conferência. Quando você enviar de novo, ele volta para a fila e
              passa por uma nova conferência, o que poderá alterar o prazo de liberação.
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Botao onClick={() => setConfirmando(false)} disabled={enviando}>
                Continuar aguardando
              </Botao>
              <Botao variante="secundario" onClick={() => void editar()} disabled={enviando}>
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
    </>
  )
}
