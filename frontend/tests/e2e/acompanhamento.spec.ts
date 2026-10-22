/**
 * `T-420` (`RF-431`) — a tela do plano em elaboração e análise: três etapas,
 * prazo estimado e as duas ações sobre as respostas. Desktop (1440) e mobile (360).
 */
import { expect, test } from '@playwright/test'

import { abrirTela, inicioEmColeta, interceptarBase } from './apoio/navegacao'

const CASO = 'CASO-ACOMPANHAMENTO'

test.beforeEach(async ({ page }) => {
  await interceptarBase(page, CASO, {
    inicio: {
      ...inicioEmColeta(CASO),
      estado: 'AGUARDANDO_REVISAO',
      fase: 'revisao',
      mensagem: 'Seu plano está em conferência.',
      proxima_etapa: { destino: 'aguardando' as const, ID_PERGUNTA: null, item_id: null },
      pode_retomar_edicao: true,
      plano_liberado: false,
    },
  })
  await abrirTela(page, CASO, 'inicio')
})

test('mostra as três etapas, o prazo e a orientação de espera', async ({ page }) => {
  await expect(page.getByRole('heading', { name: 'Meu plano de quitação' })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Andamento do plano' }).getByRole('listitem')).toHaveCount(3)
  await expect(page.getByText('Etapa atual')).toBeVisible()
  await expect(page.getByText('Estamos preparando seu plano de quitação')).toBeVisible()
  await expect(page.getByText('Prazo estimado: até 2 dias úteis')).toBeVisible()
  await expect(page.getByText(/Pode fechar esta página com tranquilidade/)).toBeVisible()
  await expect(page.getByText(/já foi calculado|está pronto/i)).toHaveCount(0)
})

test('não rola para o lado e o conteúdo principal aparece logo', async ({ page }) => {
  const larguras = await page.evaluate(() => ({
    documento: document.documentElement.scrollWidth,
    janela: window.innerWidth,
  }))
  expect(larguras.documento).toBeLessThanOrEqual(larguras.janela)
  await expect(page.getByText('Estamos preparando seu plano de quitação')).toBeInViewport()
})

test('editar pede confirmação antes de retirar o plano da fila', async ({ page }) => {
  let retirou = false
  await page.route(`**/caso/${CASO}/retomar-edicao`, (rota) => {
    retirou = true
    return rota.fulfill({ json: { estado: 'COLETA_INICIAL' } })
  })

  await page.getByRole('button', { name: /Editar minhas respostas/ }).click()
  await expect(page.getByText('Alterar suas informações?')).toBeVisible()
  expect(retirou).toBe(false)

  await page.getByRole('button', { name: 'Continuar aguardando' }).click()
  await expect(page.getByRole('button', { name: /Ver minhas respostas/ })).toBeVisible()
  expect(retirou).toBe(false)
})
