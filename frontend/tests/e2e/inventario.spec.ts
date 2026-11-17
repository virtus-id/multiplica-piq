/**
 * O alerta de inventário incompleto, no navegador — `RF-86`, `AC-133`,
 * `RF-78` (T-252).
 *
 * O alerta vive na casca: presente em Início, Pergunta e Fichas enquanto o
 * servidor devolver a pendência, e some quando ela deixa de existir — o
 * cliente não avalia regra nenhuma, só reconsulta `/inventario` a cada
 * navegação.
 */
import { expect, test } from '@playwright/test'

import { abrirTela, acaoPrincipal, interceptarBase } from './apoio/navegacao'

const CASO = 'CASO-INVENTARIO-E2E'
// `T-663` (`RF-559`, Rodada 18): sem `B5.00`, `SEM_DIVIDAS` substitui
// `DIVIDAS_FALTANDO` — nenhuma quantidade declarada, `ID_PARA_CORRIGIR`
// nulo (não há mais pergunta de quantidade a corrigir, só cadastrar ficha).
const MENSAGEM = 'Você ainda não cadastrou nenhuma dívida.'
const PENDENCIA = {
  tipo: 'INVENTARIO',
  codigo: 'SEM_DIVIDAS',
  ID: null,
  ID_PARA_CORRIGIR: null,
  item_id: null,
  escopo: 'DIVIDA_ID',
  enunciado: MENSAGEM,
  mensagem: MENSAGEM,
}

test.beforeEach(async ({ page }) => {
  await interceptarBase(page, CASO, { inventario: [PENDENCIA] })
  await page.route(`**/caso/${CASO}/pergunta`, async (rota) => {
    await rota.fulfill({
      json: {
        pergunta: {
          CASO_ID: CASO,
          ID: 'B3.01',
          bloco: 3,
          tipo: 'MOEDA',
          enunciado: 'Pergunta de teste',
          opcoes: [],
          escopo_repeticao: 'NENHUM',
          item_id: null,
          posicao: null,
          total_na_ficha: null,
          admite_nao_sei: false,
          valor_atual: null,
          respondida_como_nao_sei: false,
          valores_marcados: [],
          aviso: null,
        },
        avanco_permitido: false,
        total_pendencias: 1,
      },
    })
  })
  await page.route(`**/caso/${CASO}/fichas/DIVIDA_ID`, async (rota) => {
    await rota.fulfill({ json: { CASO_ID: CASO, escopo: 'DIVIDA_ID', fichas: [] } })
  })
})

for (const tela of ['inicio', 'pergunta', 'fichas']) {
  test(`AC-133: o alerta aparece em ${tela}`, async ({ page }) => {
    await abrirTela(page, CASO, tela)

    await expect(page.getByRole('alert').filter({ hasText: MENSAGEM })).toBeVisible()
  })
}

test('AC-133: igualadas as fichas, o alerta some na navegação seguinte', async ({ page }) => {
  await abrirTela(page, CASO, 'inicio')
  await expect(page.getByRole('alert').filter({ hasText: MENSAGEM })).toBeVisible()

  await page.route(`**/caso/${CASO}/inventario`, async (rota) => {
    await rota.fulfill({ json: { pendencias: [] } })
  })
  await page.getByRole('button', { name: 'Cadastrar as fichas' }).click()

  await expect(page.getByText(MENSAGEM)).toHaveCount(0)
})

test('T-301/T-663: sem nenhuma ficha de dívida, o Início abre a lista de fichas', async ({ page }) => {
  await interceptarBase(page, CASO, {
    inventario: [PENDENCIA],
    inicio: {
      proxima_etapa: {
        destino: 'inventario',
        ID_PERGUNTA: null,
        item_id: null,
        abrir_fichas: ['DIVIDA_ID'],
      },
    },
  })
  await abrirTela(page, CASO, 'inicio')

  await acaoPrincipal(page, 'Completar o inventário').click()

  await expect(page).toHaveURL(/#fichas/)
})
