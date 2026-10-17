/**
 * Fila de conferência — tela `equipe-fila` do protótipo (`RF-50`, `RF-59`,
 * `AC-28`, `AC-87`).
 *
 * **Os dois sinais aparecem SEPARADOS**, e isso não é escolha de layout:
 * `entra_por_politica` (a política do piloto, 100% revisado) e
 * `e_metodologico` (o campo `REVISAO_HUMANA_OBRIGATORIA` que o motor
 * levantou) são fatos diferentes. Um teste estático do servidor falha se
 * forem combinados num booleano só — combiná-los aqui, no visual, teria o
 * mesmo efeito prático de esconder a distinção do revisor.
 *
 * **900px, não 560px** (`AC-87`): a coluna de leitura do aluno existe para
 * uma pergunta por vez; o revisor compara linhas de uma tabela. É a única
 * diferença de layout entre as duas áreas, e vem da prop `largura`.
 *
 * Acesso é por papel: sem sessão dá `401`, conta não-revisora dá `403`.
 * Quem decide isso é o servidor, a cada requisição.
 */
import { useCallback, useEffect, useState } from 'react'

import Botao from '../componentes/Botao'
import Esqueleto from '../componentes/Esqueleto'
import TabelaDeCasos, { type Ordem } from '../componentes/TabelaDeCasos'
import Tela from '../componentes/Tela'
import { ErroHttp, obterCasosParaRevisao } from '../services/api'
import type {
  AbaDeCasos,
  CampoDeOrdem,
  ParametrosDeCasos,
  RespostaDeCasos,
} from '../tipos'

const ABAS: { aba: AbaDeCasos; rotulo: string }[] = [
  { aba: 'pendentes', rotulo: 'Pendentes' },
  { aba: 'entregues', rotulo: 'Entregues' },
  { aba: 'devolvidos', rotulo: 'Devolvidos' },
  { aba: 'todos', rotulo: 'Todos' },
]

const CHAVE_DA_BUSCA = 'piq.fila.busca'
const CONSULTA_INICIAL: ParametrosDeCasos = { aba: 'pendentes', pagina: 1, por_pagina: 25 }

/** O termo de busca guardado ao recarregar (`RF-504`); storage indisponível não derruba a tela. */
function lerConsulta(): ParametrosDeCasos {
  try {
    const q = sessionStorage.getItem(CHAVE_DA_BUSCA)
    if (q) return { ...CONSULTA_INICIAL, q }
  } catch {
    /* sem storage: começa limpo */
  }
  return CONSULTA_INICIAL
}

/** Pendentes: o mais antigo primeiro; nas demais abas, o mais recente (`RF-505`). */
function ordemPadrao(aba: AbaDeCasos): Ordem {
  return { campo: 'chegou_em', direcao: aba === 'pendentes' ? 'asc' : 'desc' }
}

const CLASSE_CAMPO = 'rounded-piq border-2 border-line bg-surface px-2 py-0.5 text-sm text-ink'
const CLASSE_PAGINACAO = '!min-h-0 !w-auto !px-3 !py-0.5 !text-sm'

/**
 * `401`/`403` não são falhas: são a guarda de papel funcionando. Mostrar
 * "HTTP 403" a uma pessoa é despejar o código de status na cara dela —
 * o texto abaixo diz o que de fato aconteceu, sem inventar promessa de
 * acesso que o servidor não vai conceder.
 */
function mensagemDoErro(falha: unknown): string {
  if (falha instanceof ErroHttp) {
    if (falha.status === 403) return 'Esta tela é da equipe de conferência. Sua conta não tem esse acesso.'
    if (falha.status === 401) return 'Sua sessão expirou. Entre novamente.'
    return falha.detalhe
  }
  return 'Não foi possível carregar a fila.'
}

interface TelaRevisaoProps {
  voltar?: () => void
  /**
   * Abre a conferência de um caso — `AC-29`.
   *
   * **Sem isto a tela de conferência é inalcançável.** Ela existe desde
   * `T-150`, e as rotas que a alimentam desde `T-70`/`T-72`, mas a fila não
   * tinha como abri-la: o revisor via a lista e não podia agir sobre ela, o
   * que deixava `RF-23` (todo plano passa pela conferência) sem caminho na
   * interface.
   */
  abrirCaso?: (casoId: string) => void
  /**
   * Abre o "Painel de usuários" — `T-186` (`T-331`).
   *
   * Sem isto o painel só era alcançável digitando `#equipe-painel` na mão:
   * nenhuma tela linkava para lá. A fila é a raiz da navegação do revisor
   * (não recebe `voltar` — ver a nota em `App.tsx`), então é dela que a
   * segunda área da equipe precisa ficar a um clique.
   */
  abrirPainel?: () => void
  /**
   * Encerra a sessão — `T-188`.
   *
   * Mesma nota de `TelaInicio`: sem isto não havia caminho de sair pela
   * interface para NINGUÉM, revisor incluído. Esta é a raiz da navegação
   * dele (sem `voltar`), então é aqui que "sair" mora.
   */
  aoSair: () => void
}

export default function TelaRevisao({
  voltar,
  abrirCaso,
  abrirPainel,
  aoSair,
}: TelaRevisaoProps) {
  const [filtros, setFiltros] = useState<ParametrosDeCasos>(lerConsulta)
  const [busca, setBusca] = useState(filtros.q ?? '')
  const [dados, setDados] = useState<RespostaDeCasos | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  const aba = filtros.aba ?? 'pendentes'
  const ordem: Ordem =
    filtros.ordenar && filtros.direcao
      ? { campo: filtros.ordenar, direcao: filtros.direcao }
      : ordemPadrao(aba)

  const carregar = useCallback(async () => {
    setCarregando(true)
    setErro(null)
    try {
      const padrao = ordemPadrao(filtros.aba ?? 'pendentes')
      setDados(
        await obterCasosParaRevisao({
          ...filtros,
          ordenar: filtros.ordenar ?? padrao.campo,
          direcao: filtros.direcao ?? padrao.direcao,
        }),
      )
    } catch (falha) {
      setErro(mensagemDoErro(falha))
    } finally {
      setCarregando(false)
    }
  }, [filtros])

  useEffect(() => {
    void carregar()
  }, [carregar])

  useEffect(() => {
    try {
      if (filtros.q) sessionStorage.setItem(CHAVE_DA_BUSCA, filtros.q)
      else sessionStorage.removeItem(CHAVE_DA_BUSCA)
    } catch {
      /* sem storage: a busca só não sobrevive ao recarregar */
    }
  }, [filtros.q])

  // Busca com atraso: uma consulta por pausa na digitação, não por tecla.
  useEffect(() => {
    const t = setTimeout(() => {
      setFiltros((f) => (busca === (f.q ?? '') ? f : { ...f, q: busca || undefined, pagina: 1 }))
    }, 300)
    return () => clearTimeout(t)
  }, [busca])

  /** Mudar filtro volta à página 1. */
  const mudar = (parcial: Partial<ParametrosDeCasos>) =>
    setFiltros((f) => ({ ...f, ...parcial, pagina: parcial.pagina ?? 1 }))

  const ordenarPor = (campo: CampoDeOrdem) =>
    mudar({
      ordenar: campo,
      direcao: ordem.campo === campo && ordem.direcao === 'asc' ? 'desc' : 'asc',
    })

  const total = dados?.total ?? 0
  const porPagina = dados?.por_pagina ?? filtros.por_pagina ?? 25
  const pagina = dados?.pagina ?? filtros.pagina ?? 1
  const de = total === 0 ? 0 : (pagina - 1) * porPagina + 1
  const ate = Math.min(pagina * porPagina, total)
  const itens = dados?.itens ?? []

  return (
    <Tela
      titulo="Planos aguardando conferência"
      voltar={voltar}
      largura="equipe"
      onde={dados ? `${dados.contagens.pendentes} na fila` : undefined}
      aoSair={aoSair}
      acoes={
        <>
          {/* A fila é lida em turnos: recarregar é a ação principal do
              revisor, e sem ela a única forma de ver o que entrou é
              recarregar a página. */}
          <Botao variante="secundario" onClick={() => void carregar()} disabled={carregando}>
            {carregando ? 'Atualizando…' : 'Atualizar a fila'}
          </Botao>
          {abrirPainel && (
            <Botao variante="discreto" onClick={abrirPainel}>
              Ver painel de usuários
            </Botao>
          )}
        </>
      }
    >
      <p className="lead">
        Todo plano passa por aqui antes de chegar ao aluno. Recálculos também.
      </p>

      {/* Abas e busca na mesma linha; em tela estreita a busca desce. */}
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2" data-testid="abas-e-busca">
        <div role="group" aria-label="Situação dos planos" className="flex flex-wrap gap-2">
          {ABAS.map(({ aba: a, rotulo }) => (
            <button
              key={a}
              type="button"
              aria-pressed={a === aba}
              className={`chip !py-0.5 ${a === aba ? 'chip-ok' : 'chip-mudo'}`}
              onClick={() => mudar({ aba: a, ordenar: undefined, direcao: undefined })}
            >
              {rotulo}
              {dados && ` (${dados.contagens[a]})`}
            </button>
          ))}
        </div>

        <form role="search" className="relative w-full sm:w-72" onSubmit={(e) => e.preventDefault()}>
          <input
            type="text"
            aria-label="Buscar por nome ou e-mail"
            placeholder="Buscar por nome ou e-mail"
            className={`${CLASSE_CAMPO} w-full pr-7`}
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
          {busca && (
            <button
              type="button"
              aria-label="Limpar busca"
              className="absolute inset-y-0 right-0 px-2 text-muted"
              onClick={() => setBusca('')}
            >
              <span aria-hidden="true">×</span>
            </button>
          )}
        </form>
      </div>

      {/*
        **Só na PRIMEIRA carga** (T-164): `carregando` também fica `true` na
        reconsulta, com a tabela já na tela. O botão já diz "Atualizando…".
      */}
      {carregando && !dados && <Esqueleto forma="lista" anuncio="Carregando a fila" itens={4} />}

      {erro && (
        <p role="alert" className="aviso-erro">
          {erro}
        </p>
      )}

      {dados && !erro && itens.length === 0 && !carregando && (
        <div role="status" className="nota">
          <p>Nenhum plano encontrado.</p>
        </div>
      )}

      {itens.length > 0 && (
        <TabelaDeCasos itens={itens} ordem={ordem} aoOrdenar={ordenarPor} abrirCaso={abrirCaso} />
      )}

      {dados && total > 0 && (
        <nav aria-label="Páginas" className="flex flex-wrap items-center gap-2 text-sm">
          <span role="status">
            Mostrando {de}–{ate} de {total}
          </span>
          <Botao variante="discreto" className={CLASSE_PAGINACAO} disabled={pagina <= 1} onClick={() => mudar({ pagina: pagina - 1 })}>
            Anterior
          </Botao>
          <Botao variante="discreto" className={CLASSE_PAGINACAO} disabled={ate >= total} onClick={() => mudar({ pagina: pagina + 1 })}>
            Próxima
          </Botao>
          <label className="flex items-center gap-2">
            Por página
            <select
              className={CLASSE_CAMPO}
              value={porPagina}
              onChange={(e) => mudar({ por_pagina: Number(e.target.value) as 25 | 50 })}
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </label>
        </nav>
      )}
    </Tela>
  )
}
