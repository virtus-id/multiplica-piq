/**
 * Minhas respostas — rever e corrigir o que já foi dito (`RF-68`, `RF-69`,
 * `AC-100`, `AC-101`, `AC-102`) (T-160), em uma página só (`T-422`, `RF-433`).
 *
 * **Por que existe.** `RF-10` promete retomada sem redigitar, e o sistema
 * cumpria. Mas retomar não é **conferir**: o relato foi literal — *"nem
 * consigo ver o que foi respondido, e se eu esquecer"*. Para quem responde cem
 * perguntas sobre o próprio dinheiro, não poder reler o que disse é não poder
 * confiar no plano que sai dali.
 *
 * **Uma página, dois modos, o mesmo layout.** Todas as partes aparecem em
 * sequência, com um índice fixo no topo que leva a cada uma por âncora. No modo
 * `visualizar` (cálculo, conferência, plano liberado) as respostas só se leem;
 * no modo `editar` cada resposta vira o campo de sempre. O modo vem do
 * servidor (`editavel`, `RF-114`), nunca do cliente.
 *
 * **Esta tela não decide o que aparece.** As cinco partes vêm do servidor
 * (`GET /caso/{id}/respostas`), inclusive as vazias (`AC-101`).
 *
 * **Salvar não é um segundo caminho de escrita** (`RF-69`). O "Salvar
 * alterações" grava cada resposta mudada pela MESMA rota da coleta
 * (`POST /caso/{id}/resposta`), uma por vez, na ordem da página: a validação
 * (`EC-01`) segue soberana no servidor, e a que falhar mostra o erro na própria
 * linha sem derrubar as outras.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'

import Botao from '../componentes/Botao'
import Esqueleto from '../componentes/Esqueleto'
import AtalhosDasFichas from '../componentes/respostas/AtalhosDasFichas'
import BannerDeRespostas from '../componentes/respostas/BannerDeRespostas'
import LinhaDaResposta, { type Rascunho } from '../componentes/respostas/LinhaDaResposta'
import PaginaDeRespostas from '../componentes/respostas/PaginaDeRespostas'
import {
  agruparPorItem,
  chaveDaResposta,
  type GrupoDeRespostas,
} from '../componentes/respostas/textoDasRespostas'
import Tela from '../componentes/Tela'
import { gravarResposta, obterRespostasDoCaso } from '../services/api'
import type { Fase, RespostaDada, RespostasDoCaso } from '../tipos'

export { agruparPorItem, type GrupoDeRespostas }

interface TelaRespostasProps {
  casoId: string
  voltar: () => void
  /** A fase do caso, do Início: distingue "em análise" de "plano liberado". */
  fase?: Fase
  /** Segue a coleta — para responder o que uma alteração abriu. */
  continuar?: () => void
  /** Abre a lista de fichas de um escopo (dívidas, despesas...) — `T-425`. */
  verFichas?: (escopo: string) => void
}

export default function TelaRespostas({
  casoId,
  voltar,
  fase,
  continuar,
  verFichas,
}: TelaRespostasProps) {
  const [respostas, setRespostas] = useState<RespostasDoCaso | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [rascunhos, setRascunhos] = useState<Record<string, Rascunho>>({})
  const [erros, setErros] = useState<Record<string, string>>({})
  const [salvando, setSalvando] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)
  const [pendencias, setPendencias] = useState(0)
  const [versao, setVersao] = useState(0)

  const carregar = useCallback(async () => {
    setCarregando(true)
    setErro(null)
    try {
      setRespostas(await obterRespostasDoCaso(casoId))
    } catch {
      setErro('Não foi possível carregar as suas respostas.')
    } finally {
      setCarregando(false)
    }
  }, [casoId])

  useEffect(() => {
    void carregar()
  }, [carregar])

  // Todas as respostas, na ordem da página: a mãe vem antes da filha, e é
  // nessa ordem que o "Salvar alterações" grava.
  const todas = useMemo(
    () => (respostas?.partes ?? []).flatMap((parte) => parte.respondidas),
    [respostas],
  )
  const alteradas = useMemo(
    () => todas.filter((resposta) => rascunhos[chaveDaResposta(resposta)] !== undefined),
    [todas, rascunhos],
  )

  async function salvar() {
    setSalvando(true)
    setAviso(null)
    const novosErros: Record<string, string> = {}
    const restantes: Record<string, Rascunho> = { ...rascunhos }
    let ultimaPendencia: number | null = null
    let gravadas = 0
    for (const resposta of alteradas) {
      const chave = chaveDaResposta(resposta)
      const rascunho = rascunhos[chave]
      if (!rascunho) continue
      try {
        const confirmacao = await gravarResposta(casoId, {
          idPergunta: resposta.ID,
          valor: rascunho.naoSei ? undefined : rascunho.valor,
          itemId: resposta.item_id,
          naoSei: rascunho.naoSei,
        })
        delete restantes[chave]
        ultimaPendencia = confirmacao.total_pendencias
        gravadas += 1
      } catch (falha) {
        novosErros[chave] = falha instanceof Error ? falha.message : 'Não foi possível salvar.'
      }
    }
    setRascunhos(restantes)
    setErros(novosErros)
    if (ultimaPendencia !== null) setPendencias(ultimaPendencia)
    if (gravadas > 0) {
      try {
        setRespostas(await obterRespostasDoCaso(casoId))
        setVersao((atual) => atual + 1)
      } catch {
        setErro('As alterações foram salvas, mas não foi possível recarregar a lista.')
      }
    }
    const falhas = Object.keys(novosErros).length
    setAviso(
      falhas === 0
        ? 'Alterações salvas.'
        : `${gravadas} salva${gravadas === 1 ? '' : 's'}; ${falhas} com problema (veja nas linhas marcadas).`,
    )
    setSalvando(false)
  }

  function descartar() {
    setRascunhos({})
    setErros({})
    setAviso(null)
    setVersao((atual) => atual + 1)
  }

  if (carregando && !respostas) {
    return (
      <Tela titulo="Minhas respostas" voltar={voltar} rotuloVoltar="‹ Voltar ao início">
        <Esqueleto forma="lista" anuncio="Carregando suas respostas" itens={4} />
      </Tela>
    )
  }

  if (!respostas || respostas.partes.length === 0) {
    return (
      <Tela titulo="Minhas respostas" voltar={voltar} rotuloVoltar="‹ Voltar ao início">
        <p role="alert" className="aviso-erro">
          {erro ?? 'Nada para mostrar agora.'}
        </p>
      </Tela>
    )
  }

  // `RF-114`: ausente ⇒ editável (servidor antigo não manda o campo).
  const modo = respostas.editavel !== false ? 'editar' : 'visualizar'

  function renderizarLinha(
    resposta: RespostaDada,
    contexto: { domId: string; destacada: boolean; larga: boolean },
  ) {
    const chave = chaveDaResposta(resposta)
    return (
      <LinhaDaResposta
        casoId={casoId}
        modo={modo}
        resposta={resposta}
        domId={contexto.domId}
        destacada={contexto.destacada}
        larga={contexto.larga}
        rascunho={rascunhos[chave]}
        erro={erros[chave]}
        aoAlterar={(rascunho) => setRascunhos((atual) => ({ ...atual, [chave]: rascunho }))}
      />
    )
  }

  return (
    <Tela
      titulo="Minhas respostas"
      voltar={voltar}
      rotuloVoltar="‹ Voltar ao início"
      largura="ampla"
      acoes={
        modo === 'editar' ? (
          <>
            <Botao onClick={() => void salvar()} disabled={salvando || alteradas.length === 0}>
              {salvando
                ? 'Salvando…'
                : alteradas.length > 0
                  ? `Salvar alterações (${alteradas.length})`
                  : 'Salvar alterações'}
            </Botao>
            {alteradas.length > 0 && (
              <Botao variante="discreto" onClick={descartar} disabled={salvando}>
                Descartar alterações
              </Botao>
            )}
            <Botao variante="discreto" onClick={voltar}>
              Voltar ao início
            </Botao>
          </>
        ) : (
          <Botao onClick={voltar}>Voltar ao início</Botao>
        )
      }
    >
      <p className="lead m-0">
        Aqui estão todas as informações que você enviou para a elaboração do seu plano de
        quitação.
      </p>

      {aviso && (
        <div role="status" className="aviso-ok flex-col">
          <strong>{aviso}</strong>
          {pendencias > 0 && continuar && (
            <>
              <span>
                {pendencias === 1
                  ? 'Ainda falta 1 pergunta para concluir.'
                  : `Ainda faltam ${pendencias} perguntas para concluir.`}
              </span>
              <Botao variante="secundario" className="sm:!w-auto" onClick={continuar}>
                Continuar respondendo
              </Botao>
            </>
          )}
        </div>
      )}
      {erro && (
        <p role="alert" className="aviso-erro">
          {erro}
        </p>
      )}

      {modo === 'editar' && verFichas && <AtalhosDasFichas casoId={casoId} aoAbrir={verFichas} />}

      <PaginaDeRespostas
        modo={modo}
        partes={respostas.partes}
        versao={versao}
        renderLinha={renderizarLinha}
        banner={
          <BannerDeRespostas
            casoId={casoId}
            modo={modo}
            planoLiberado={fase === 'plano'}
            podeEditar={respostas.pode_retomar_edicao === true}
            aoRetirar={() => void carregar()}
          />
        }
      />
    </Tela>
  )
}
