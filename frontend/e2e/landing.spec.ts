import { test, expect } from '@playwright/test'

test.describe('Landing y páginas legales', () => {
  test('la portada muestra marca, cobertura y fuentes con atribución', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByRole('heading', { level: 1 })).toContainText('gastronomía')
    await expect(page.getByText('27.064').first()).toBeVisible()
    await expect(page.getByText('CABA + GBA').first()).toBeVisible()
    await expect(page.getByText(/© OpenStreetMap contributors/)).toBeVisible()
    await expect(page.getByText(/CC-BY-2.5-AR/)).toBeVisible()
    await expect(page.getByText(/CDLA-Permissive-2.0/)).toBeVisible()
  })

  test('la portada enlaza a privacidad y términos', async ({ page }) => {
    await page.goto('/')
    const privacidad = page.getByRole('link', { name: /política de privacidad/i }).first()
    const terminos = page.getByRole('link', { name: /términos y condiciones/i }).first()
    await expect(privacidad).toHaveAttribute('href', '/privacidad')
    await expect(terminos).toHaveAttribute('href', '/terminos')
  })

  test('la política de privacidad es una página propia', async ({ page }) => {
    await page.goto('/privacidad')
    await expect(page.getByRole('heading', { level: 1, name: 'Política de privacidad' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '2. Qué datos podemos tratar' })).toBeVisible()
    await expect(page.locator('a[href^="mailto:"]').first()).toBeVisible()
    await expect(page).toHaveTitle(/privacidad/i)
  })

  test('los términos y condiciones son una página propia', async ({ page }) => {
    await page.goto('/terminos')
    await expect(page.getByRole('heading', { level: 1, name: 'Términos y condiciones' })).toBeVisible()
    await expect(page.getByText(/Seguridad alimentaria/)).toBeVisible()
    await expect(page.getByRole('heading', { name: '11. Ley aplicable' })).toBeVisible()
    await expect(page).toHaveTitle(/términos/i)
  })
})
