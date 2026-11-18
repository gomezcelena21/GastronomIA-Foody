import { test, expect, type Page } from '@playwright/test'

// Simula la API para que las pruebas de interfaz no dependan de PostgreSQL.
async function apiBasica(page: Page) {
  await page.route('https://accounts.google.com/**', route => route.abort())
  await page.route('**/api/provinces', route => route.fulfill({
    json: { provinces: [{ name: 'Buenos Aires', count: 10 }] },
  }))
}

async function entrarComoInvitado(page: Page) {
  await page.goto('/chat')
  await page.getByRole('button', { name: 'Continuar sin registrarme' }).click({ timeout: 20_000 })
  await expect(page.locator('.shell')).toBeVisible()
}

test.describe('Acceso y chat', () => {
  test('el login muestra Google y el acceso sin registro', async ({ page }) => {
    await apiBasica(page)
    await page.goto('/chat')
    await expect(page.getByRole('heading', { name: /Hola, soy/ })).toBeVisible({ timeout: 20_000 })
    await expect(page.getByRole('button', { name: 'Continuar sin registrarme' })).toBeVisible({ timeout: 20_000 })
    await expect(page.locator('.gwrap')).toBeAttached()
  })

  test('el invitado entra y Foody responde con tarjetas reales', async ({ page }) => {
    await apiBasica(page)
    await page.route('**/api/chat', async route => {
      if (route.request().method() !== 'POST') return route.continue()
      await route.fulfill({
        json: {
          response: 'Te recomiendo «La Prueba», en Palermo.',
          session_id: 's1',
          validada: true,
          id_conversacion: 1,
          restaurants: [{
            restaurant_id: 1, name: 'La Prueba', neighborhood: 'Palermo', city: 'CABA',
            cuisine_type: ['pizzeria'], source_name: 'OpenStreetMap',
            features: { has_gluten_free_options: true },
          }],
        },
      })
    })

    await entrarComoInvitado(page)
    await page.getByPlaceholder('Escribí tu mensaje…').fill('pizzería sin TACC en Palermo')
    await page.getByPlaceholder('Escribí tu mensaje…').press('Enter')

    await expect(page.getByText(/Te recomiendo «La Prueba»/)).toBeVisible()
    await expect(page.locator('.card').filter({ hasText: 'La Prueba' })).toBeVisible()
    await expect(page.locator('.card').filter({ hasText: 'La Prueba' }).getByText('Sin TACC')).toBeVisible()
  })
})

test.describe('Explorar', () => {
  test('muestra resultados, filtros y mapa', async ({ page }) => {
    await apiBasica(page)
    await page.route('**/api/restaurants?**', route => route.fulfill({
      json: {
        total: 1,
        results: [{
          restaurant_id: 7, name: 'Mapa Feliz', neighborhood: 'Belgrano', city: 'CABA',
          latitude: -34.56, longitude: -58.45, cuisine_type: ['cafe'],
          features: { has_vegan_options: true }, source_name: 'BA Data',
        }],
      },
    }))

    await entrarComoInvitado(page)
    await page.getByRole('button', { name: /Explorar/ }).click()

    await expect(page.locator('.li').filter({ hasText: 'Mapa Feliz' })).toBeVisible()
    await expect(page.locator('iframe[title="mapa"]')).toBeVisible()
    await expect(page.getByText('1 lugar').first()).toBeVisible()
  })
})

test.describe('Comercios', () => {
  test('una cuenta con comercio llega al panel y puede cargar sus datos', async ({ page }) => {
    await page.route('**/api/provinces', route => route.fulfill({
      json: { provinces: [{ name: 'Buenos Aires', count: 10 }] },
    }))
    // GSI simulado: dibuja un botón y devuelve un credential falso.
    await page.route('https://accounts.google.com/**', route => route.fulfill({
      contentType: 'application/javascript',
      body: `
        window.google = { accounts: { id: {
          initialize: function (o) { window.__googleCallback = o.callback },
          renderButton: function (el) {
            var b = document.createElement('button')
            b.type = 'button'
            b.textContent = 'Continuar con Google'
            b.onclick = function () { window.__googleCallback({ credential: 'credential-de-prueba-123456' }) }
            el.appendChild(b)
          }
        } } };
      `,
    }))
    await page.route('**/api/auth/google', route => route.fulfill({
      json: {
        token: 'token.de.prueba',
        usuario: { id_usuario: 42, nombre: 'Ana', email: 'ana@example.com', comercio: true, admin: false },
      },
    }))
    await page.route('**/api/comercio/mio', route => route.fulfill({
      json: { comercio: null },
    }))

    await page.goto('/chat')
    // El GSI real dibuja un solo botón; el simulador puede dibujar dos por el
    // doble montaje de React StrictMode, así que se usa el primero.
    await page.getByRole('button', { name: 'Continuar con Google' }).first().click({ timeout: 20_000 })

    // Al iniciar sesión se abre el chat directo (ya no se pregunta si es usuario o comercio).
    await expect(page.locator('.shell')).toBeVisible()
    await expect(page.getByText(/Cómo querés usar GastronomIA/)).toHaveCount(0)
    // El comercio se maneja desde Perfil → Mi comercio. La cuenta ya tiene uno asociado: "Ir a mi comercio".
    await page.getByRole('button', { name: 'Perfil' }).click()
    await page.getByRole('button', { name: /mi comercio/i }).click()

    await expect(page.getByRole('heading', { name: 'Mi comercio' })).toBeVisible()
    await expect(page.getByText('Datos del comercio')).toBeVisible()
    await expect(page.locator('.ex-grid input[type="text"]').first()).toBeVisible()
  })
})

test.describe('Sesión recordada', () => {
  // Token de prueba con la misma forma que el real: el primer tramo es un JSON en base64 con el vencimiento (exp).
  const token = (segundos: number) =>
    Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + segundos })).toString('base64url') + '.firma'
  const guardarSesion = async (page: Page, segundos: number) => {
    // addInitScript corre en cada carga de página: la sesión se siembra una sola vez por
    // pestaña, así no reaparece después de cerrarla.
    await page.addInitScript(([t, u]) => {
      if (sessionStorage.getItem('e2e_sesion_sembrada')) return
      sessionStorage.setItem('e2e_sesion_sembrada', '1')
      localStorage.setItem('foody_token', t)
      localStorage.setItem('foody_user', u)
    }, [token(segundos), JSON.stringify({ id_usuario: 42, nombre: 'Ana', email: 'ana@example.com', comercio: false, admin: false })])
  }

  test('quien ya inició sesión entra directo al chat, sin login ni elegir usuario o comercio', async ({ page }) => {
    await apiBasica(page)
    await page.route('**/api/auth/me', route => route.fulfill({ json: { email: 'ana@example.com', nombre: 'Ana', consultas_restantes: 10 } }))
    await guardarSesion(page, 3600)
    await page.goto('/chat')
    await expect(page.locator('.shell')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByRole('button', { name: 'Continuar sin registrarme' })).toHaveCount(0)
    await expect(page.getByText(/Cómo querés usar GastronomIA/)).toHaveCount(0)
  })

  test('si la sesión venció, se muestra el inicio de sesión', async ({ page }) => {
    await apiBasica(page)
    await guardarSesion(page, -60)
    await page.goto('/chat')
    await expect(page.getByRole('button', { name: 'Continuar sin registrarme' })).toBeVisible({ timeout: 20_000 })
  })

  test('si el servidor rechaza el token (401), se vuelve al inicio de sesión', async ({ page }) => {
    await apiBasica(page)
    await page.route('**/api/auth/me', route => route.fulfill({ status: 401, json: { detail: 'Tu sesión no es válida o venció.' } }))
    await guardarSesion(page, 3600)
    await page.goto('/chat')
    await expect(page.getByRole('button', { name: 'Continuar sin registrarme' })).toBeVisible({ timeout: 20_000 })
  })

  test('cerrar sesión borra la sesión guardada', async ({ page }) => {
    await apiBasica(page)
    await page.route('**/api/auth/me', route => route.fulfill({ json: { email: 'ana@example.com', nombre: 'Ana', consultas_restantes: 10 } }))
    await guardarSesion(page, 3600)
    await page.goto('/perfil')
    await page.getByRole('button', { name: 'Cerrar sesión' }).click()
    await page.waitForURL('**/')
    expect(await page.evaluate(() => localStorage.getItem('foody_token'))).toBeNull()
  })
})
