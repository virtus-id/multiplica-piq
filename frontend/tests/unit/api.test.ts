/**
 * O cliente mostra a recusa do servidor — `T-337`.
 *
 * O `HTTPException` do FastAPI manda `{"detail": "..."}`, e não `erro`: sem
 * lê-lo, o `409` da conferência chegava à tela como "HTTP 409".
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ErroHttp, ajustarOrdem, retomarEdicao } from '../../src/services/api'

afterEach(() => {
  vi.restoreAllMocks()
})

function responder(status: number, corpo: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => corpo }),
  )
}

describe('pedir — mensagem da recusa', () => {
  it('lê o `detail` do HTTPException (409 da conferência)', async () => {
    responder(409, { detail: 'O aluno retirou este plano para editar.' })
    await expect(retomarEdicao('C1')).rejects.toMatchObject({
      status: 409,
      detalhe: 'O aluno retirou este plano para editar.',
    })
  })

  it('`erro` continua ganhando de `detail`', async () => {
    responder(409, { erro: 'Seu plano não está em conferência.', detail: 'outra coisa' })
    await expect(retomarEdicao('C1')).rejects.toBeInstanceOf(ErroHttp)
    await expect(retomarEdicao('C1')).rejects.toMatchObject({
      detalhe: 'Seu plano não está em conferência.',
    })
  })

  it('sem corpo legível, fica o status', async () => {
    responder(500, null)
    await expect(retomarEdicao('C1')).rejects.toMatchObject({ detalhe: 'HTTP 500' })
  })
})

describe('ajustarOrdem — RF-546 (T-599)', () => {
  it('POST JSON com a ordem e o motivo na rota do caso', async () => {
    const resultado = { SNAPSHOT_ID: 'S2', versao: 2, ordem_vigente: ['D3', 'D1'], ajustada: true }
    const espiao = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => resultado })
    vi.stubGlobal('fetch', espiao)

    await expect(ajustarOrdem('C1', ['D3', 'D1'], 'Negativada primeiro')).resolves.toEqual(resultado)

    const [url, init] = espiao.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/revisao/caso/C1/ordem')
    expect(init.method).toBe('POST')
    expect(init.headers).toMatchObject({ 'Content-Type': 'application/json' })
    expect(JSON.parse(init.body as string)).toEqual({ ordem: ['D3', 'D1'], motivo: 'Negativada primeiro' })
  })

  it('a recusa chega com o `detail` do servidor', async () => {
    responder(409, { detail: 'Esta já é a ordem vigente. Nada a recalcular.' })
    await expect(ajustarOrdem('C1', [], '')).rejects.toMatchObject({
      status: 409,
      detalhe: 'Esta já é a ordem vigente. Nada a recalcular.',
    })
  })
})
