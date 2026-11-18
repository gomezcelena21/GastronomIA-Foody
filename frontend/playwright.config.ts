import { defineConfig, devices } from '@playwright/test'

// E2E de interfaz: no necesita backend ni base de datos.
// Las llamadas a la API se simulan con page.route() en cada prueba.
export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5173',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    // Client ID ficticio: el script de Google se simula en las pruebas, pero la app
    // necesita uno configurado para dibujar el botón de inicio de sesión.
    env: { VITE_GOOGLE_CLIENT_ID: 'e2e-client-id.apps.googleusercontent.com' },
  },
})
