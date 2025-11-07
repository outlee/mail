import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should redirect to login when not authenticated', async ({ page }) => {
    await expect(page).toHaveURL('/login')
  })

  test('should display login form', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('input[placeholder="Email"]')).toBeVisible()
    await expect(page.locator('input[placeholder="Password"]')).toBeVisible()
    await expect(page.locator('button:has-text("Login")')).toBeVisible()
  })

  test('should show error on invalid credentials', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[placeholder="Email"]', 'invalid@example.com')
    await page.fill('input[placeholder="Password"]', 'wrongpassword')
    await page.click('button:has-text("Login")')

    await expect(page.locator('text=Login Error')).toBeVisible()
    await expect(page.locator('text=Login failed')).toBeVisible()
  })

  test('should require email field', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[placeholder="Password"]', 'password123')
    await page.click('button:has-text("Login")')

    await expect(page.locator('text=Please input your email')).toBeVisible()
  })

  test('should require password field', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[placeholder="Email"]', 'test@example.com')
    await page.click('button:has-text("Login")')

    await expect(page.locator('text=Please input your password')).toBeVisible()
  })

  test('should validate email format', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[placeholder="Email"]', 'invalidemail')
    await page.fill('input[placeholder="Password"]', 'password123')
    await page.click('button:has-text("Login")')

    await expect(page.locator('text=Please input a valid email')).toBeVisible()
  })

  test('should successfully login with valid credentials', async ({ page }) => {
    await page.goto('/login')

    await page.fill('input[placeholder="Email"]', 'test@example.com')
    await page.fill('input[placeholder="Password"]', 'testpassword123')

    await page.click('button:has-text("Login")')

    await page.waitForURL('/dashboard', { timeout: 10000 })
    await expect(page).toHaveURL('/dashboard')

    // Session storage is cleared on browser close, so we check page content instead
    await expect(page.locator('text=Dashboard')).toBeVisible()
  })

  test('should persist session after reload', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[placeholder="Email"]', 'test@example.com')
    await page.fill('input[placeholder="Password"]', 'testpassword123')
    await page.click('button:has-text("Login")')

    await page.waitForURL('/dashboard', { timeout: 10000 })

    // Store session data
    const sessionData = await page.evaluate(() => ({
      accessToken: sessionStorage.getItem('access_token'),
      refreshToken: sessionStorage.getItem('refresh_token'),
    }))

    expect(sessionData.accessToken).toBeTruthy()
    expect(sessionData.refreshToken).toBeTruthy()

    // Reload and verify still on dashboard
    await page.reload()
    await expect(page).toHaveURL('/dashboard')
  })
})

test.describe('Protected Routes', () => {
  test('should show user info on dashboard', async ({ page }) => {
    await page.goto('/login')

    await page.fill('input[placeholder="Email"]', 'test@example.com')
    await page.fill('input[placeholder="Password"]', 'testpassword123')
    await page.click('button:has-text("Login")')

    await page.waitForURL('/dashboard', { timeout: 10000 })

    await expect(page.locator('text=User')).toBeVisible()
    await expect(page.locator('text=Role')).toBeVisible()
    await expect(page.locator('text=Email')).toBeVisible()
  })

  test('should display logout button on dashboard', async ({ page }) => {
    await page.goto('/login')

    await page.fill('input[placeholder="Email"]', 'test@example.com')
    await page.fill('input[placeholder="Password"]', 'testpassword123')
    await page.click('button:has-text("Login")')

    await page.waitForURL('/dashboard', { timeout: 10000 })

    const logoutButton = page.locator('button:has-text("Logout")')
    await expect(logoutButton).toBeVisible()
  })

  test('should logout successfully', async ({ page }) => {
    await page.goto('/login')

    await page.fill('input[placeholder="Email"]', 'test@example.com')
    await page.fill('input[placeholder="Password"]', 'testpassword123')
    await page.click('button:has-text("Login")')

    await page.waitForURL('/dashboard', { timeout: 10000 })

    // Click logout
    await page.click('button:has-text("Logout")')

    // Should redirect to login
    await page.waitForURL('/login', { timeout: 10000 })
    await expect(page).toHaveURL('/login')
  })
})
