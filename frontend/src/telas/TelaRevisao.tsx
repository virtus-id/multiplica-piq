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

/** Os códigos vão na consulta; o texto da tela é o rótulo. */
const STATUS: { codigo: string; rotulo: string }[] = [
  { codigo: 'AGUARDANDO_REVISAO', rotulo: 'Em revisão' },
  { codigo: 'PLANO_LIBERADO', rotulo: 'Entregue' },
  { codigo: 'REPROVADO_EM_REVISAO', rotulo: 'Devolvido ao aluno' },
  { codigo: 'ERRO_DE_CALCULO', rotulo: 'Erro no cálculo' },
]

const CHAVE_DOS_FILTROS = 'piq.fila.filtros'
const FILTROS_INICIAIS: ParametrosDeCasos = { aba: 'pendentes', pagina: 1, por_pagina: 25 }

/** Filtros guardados ao recarregar (`RF-504`); storage indisponível não derruba a tela. */
function lerFiltros(): ParametrosDeCasos {
  try {
    const guardado = sessionStorage.getItem(CHAVE_DOS_FILTROS)
    if (guardado) return { ...FILTROS_INICIAIS, ...(JSON.parse(guardado) as ParametrosDeCasos) }
  } catch {
    /* sem storage ou JSON inválido: começa limpo */
  }
  return FILTROS_INICIAIS
}

/** Pendentes: o mais antigo primeiro; nas demais abas, o mais recente (`RF-505`). */
function ordemPadrao(aba: AbaDeCasos): Ordem {
  return { campo: 'chegou_em', direcao: aba === 'pendentes' ? 'asc' : 'desc' }
}

const CLASSE_CAMPO = 'rounded-piq border-2 border-line bg-surface px-2 py-1 text-ink'

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
  const [filtros, setFiltros] = useState<ParametrosDeCasos>(lerFiltros)
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
      sessionStorage.setItem(CHAVE_DOS_FILTROS, JSON.stringify(filtros))
    } catch {
      /* sem storage: os filtros só não sobrevivem ao recarregar */
    }
  }, [filtros])

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

  const limpar = () => {
    setBusca('')
    setFiltros({ ...FILTROS_INICIAIS, aba, por_pagina: filtros.por_pagina })
  }

  // Chips dos filtros ativos (a aba, a ordem e a paginação não contam).
  const opcoes = dados?.opcoes
  const rotuloDe = (lista: { codigo: string; rotulo: string }[] | undefined, c: string) =>
    lista?.find((o) => o.codigo === c)?.rotulo ?? c
  const ativos: { chave: string; texto: string; remover: () => void }[] = []
  if (filtros.q) ativos.push({ chave: 'q', texto: `Busca: ${filtros.q}`, remover: () => { setBusca(''); mudar({ q: undefined }) } })
  for (const s of filtros.status ?? [])
    ativos.push({
      chave: `s-${s}`,
      texto: `Status: ${STATUS.find((x) => x.codigo === s)?.rotulo ?? s}`,
      remover: () => mudar({ status: (filtros.status ?? []).filter((x) => x !== s) }),
    })
  if (filtros.de) ativos.push({ chave: 'de', texto: `Chegou desde ${filtros.de}`, remover: () => mudar({ de: undefined }) })
  if (filtros.ate) ativos.push({ chave: 'ate', texto: `Chegou até ${filtros.ate}`, remover: () => mudar({ ate: undefined }) })
  if (filtros.tipo) ativos.push({ chave: 'tipo', texto: filtros.tipo === 'primeiro' ? 'Primeiro plano' : 'Recálculo', remover: () => mudar({ tipo: undefined }) })
  if (filtros.mes_negativo) ativos.push({ chave: 'mes', texto: filtros.mes_negativo === 'sim' ? 'Mês no negativo' : 'Mês fecha positivo', remover: () => mudar({ mes_negativo: undefined }) })
  if (filtros.metodo) ativos.push({ chave: 'metodo', texto: `Método: ${rotuloDe(opcoes?.metodos, filtros.metodo)}`, remover: () => mudar({ metodo: undefined }) })
  if (filtros.motivo) ativos.push({ chave: 'motivo', texto: `Motivo: ${rotuloDe(opcoes?.motivos, filtros.motivo)}`, remover: () => mudar({ motivo: undefined }) })
  if (filtros.revisor) ativos.push({ chave: 'revisor', texto: `Revisor: ${rotuloDe(opcoes?.revisores, filtros.revisor)}`, remover: () => mudar({ revisor: undefined }) })
  if (filtros.parado_horas) ativos.push({ chave: 'parado', texto: `Parado há mais de ${filtros.parado_horas} h`, remover: () => mudar({ parado_horas: undefined }) })

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

      <div role="group" aria-label="Situação dos planos" className="flex flex-wrap gap-2">
        {ABAS.map(({ aba: a, rotulo }) => (
          <button
            key={a}
            type="button"
            aria-pressed={a === aba}
            className={`chip ${a === aba ? 'chip-ok' : 'chip-mudo'}`}
            onClick={() => mudar({ aba: a, ordenar: undefined, direcao: undefined, status: undefined })}
          >
            {rotulo}
            {dados && ` (${dados.contagens[a]})`}
          </button>
        ))}
      </div>

      <form
        role="search"
        aria-label="Filtros"
        className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
        onSubmit={(e) => e.preventDefault()}
      >
        <label className="flex flex-col gap-1">
          Buscar por nome ou e-mail
          <input type="search" className={CLASSE_CAMPO} value={busca} onChange={(e) => setBusca(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1">
          Chegou a partir de
          <input type="date" className={CLASSE_CAMPO} value={filtros.de ?? ''} onChange={(e) => mudar({ de: e.target.value || undefined })} />
        </label>
        <label className="flex flex-col gap-1">
          Chegou até
          <input type="date" className={CLASSE_CAMPO} value={filtros.ate ?? ''} onChange={(e) => mudar({ ate: e.target.value || undefined })} />
        </label>
        <label className="flex flex-col gap-1">
          Tipo
          <select className={CLASSE_CAMPO} value={filtros.tipo ?? ''} onChange={(e) => mudar({ tipo: (e.target.value || undefined) as ParametrosDeCasos['tipo'] })}>
            <option value="">Todos</option>
            <option value="primeiro">Primeiro plano</option>
            <option value="recalculo">Recálculo</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          Mês no negativo
          <select className={CLASSE_CAMPO} value={filtros.mes_negativo ?? ''} onChange={(e) => mudar({ mes_negativo: (e.target.value || undefined) as ParametrosDeCasos['mes_negativo'] })}>
            <option value="">Todos</option>
            <option value="sim">Sim</option>
            <option value="nao">Não</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          Método
          <select className={CLASSE_CAMPO} value={filtros.metodo ?? ''} onChange={(e) => mudar({ metodo: e.target.value || undefined })}>
            <option value="">Todos</option>
            {opcoes?.metodos.map((o) => <option key={o.codigo} value={o.codigo}>{o.rotulo}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          Motivo da revisão
          <select className={CLASSE_CAMPO} value={filtros.motivo ?? ''} onChange={(e) => mudar({ motivo: e.target.value || undefined })}>
            <option value="">Todos</option>
            {opcoes?.motivos.map((o) => <option key={o.codigo} value={o.codigo}>{o.rotulo}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          Revisor
          <select className={CLASSE_CAMPO} value={filtros.revisor ?? ''} onChange={(e) => mudar({ revisor: e.target.value || undefined })}>
            <option value="">Todos</option>
            {opcoes?.revisores.map((o) => <option key={o.codigo} value={o.codigo}>{o.rotulo}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          Parado há mais de (horas)
          <input
            type="number"
            min={1}
            className={CLASSE_CAMPO}
            value={filtros.parado_horas ?? ''}
            onChange={(e) => mudar({ parado_horas: e.target.value ? Number(e.target.value) : undefined })}
          />
        </label>
        <fieldset className="m-0 flex flex-wrap items-center gap-x-4 gap-y-1 border-0 p-0 sm:col-span-2 lg:col-span-3">
          <legend className="mb-1 p-0">Status</legend>
          {STATUS.map(({ codigo, rotulo }) => (
            <label key={codigo} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={filtros.status?.includes(codigo) ?? false}
                onChange={(e) => {
                  const atual = filtros.status ?? []
                  const novo = e.target.checked ? [...atual, codigo] : atual.filter((x) => x !== codigo)
                  mudar({ status: novo.length ? novo : undefined })
                }}
              />
              {rotulo}
            </label>
          ))}
        </fieldset>
      </form>

      {ativos.length > 0 && (
        <div className="flex flex-wrap items-center gap-2" aria-label="Filtros ativos" role="group">
          {ativos.map((a) => (
            <button key={a.chave} type="button" className="chip chip-mudo" onClick={a.remover}>
              {a.texto}
              <span className="sr-only"> (tirar este filtro)</span>
              <span aria-hidden="true"> ×</span>
            </button>
          ))}
          <Botao variante="discreto" onClick={limpar}>
            Limpar filtros
          </Botao>
        </div>
      )}

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
          <Botao variante="secundario" onClick={limpar}>
            Limpar filtros
          </Botao>
        </div>
      )}

      {itens.length > 0 && (
        <TabelaDeCasos itens={itens} ordem={ordem} aoOrdenar={ordenarPor} abrirCaso={abrirCaso} />
      )}

      {dados && total > 0 && (
        <nav aria-label="Páginas" className="flex flex-wrap items-center gap-3">
          <span role="status">
            Mostrando {de}–{ate} de {total}
          </span>
          <Botao variante="discreto" disabled={pagina <= 1} onClick={() => mudar({ pagina: pagina - 1 })}>
            Anterior
          </Botao>
          <Botao variante="discreto" disabled={ate >= total} onClick={() => mudar({ pagina: pagina + 1 })}>
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
