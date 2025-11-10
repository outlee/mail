import { test, expect } from '@playwright/test'

test.describe('Dashboard Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[placeholder="Email"]', 'test@example.com')
    await page.fill('input[placeholder="Password"]', 'testpassword123')
    await page.click('button:has-text("Login")')
    await page.waitForURL('/dashboard', { timeout: 10000 })
  })

  test('should display dashboard title', async ({ page }) => {
    await expect(page.locator('h1:has-text("Dashboard")')).toBeVisible()
  })

  test('should display user information card', async ({ page }) => {
    const userCard = page.locator('.ant-card').filter({ hasText: 'User Information' })
    await expect(userCard).toBeVisible()
    await expect(userCard.locator('text=User:')).toBeVisible()
    await expect(userCard.locator('text=Email:')).toBeVisible()
    await expect(userCard.locator('text=Role:')).toBeVisible()
  })

  test('should display system health card', async ({ page }) => {
    const healthCard = page.locator('.ant-card').filter({ hasText: 'System Health' })
    await expect(healthCard).toBeVisible()
  })

  test('should check system health status', async ({ page }) => {
    await page.click('button:has-text("Check Health")')
    
    await page.waitForTimeout(1000)
    
    const healthCard = page.locator('.ant-card').filter({ hasText: 'System Health' })
    const statusText = await healthCard.locator('text=/Status:.*/')
    await expect(statusText).toBeVisible()
  })

  test('should have functional logout button', async ({ page }) => {
    const logoutButton = page.locator('button:has-text("Logout")')
    await expect(logoutButton).toBeVisible()
    await expect(logoutButton).toBeEnabled()
  })

  test('should navigate back to login on logout', async ({ page }) => {
    await page.click('button:has-text("Logout")')
    await page.waitForURL('/login', { timeout: 10000 })
    await expect(page).toHaveURL('/login')
  })

  test('should clear session data on logout', async ({ page }) => {
    await page.click('button:has-text("Logout")')
    await page.waitForURL('/login', { timeout: 10000 })

    const sessionData = await page.evaluate(() => ({
      accessToken: sessionStorage.getItem('access_token'),
      refreshToken: sessionStorage.getItem('refresh_token'),
    }))

    expect(sessionData.accessToken).toBeNull()
    expect(sessionData.refreshToken).toBeNull()
  })

  test('should display alerts management card if available', async ({ page }) => {
    const alertsCard = page.locator('.ant-card').filter({ hasText: /Alert/ })
    const cardCount = await alertsCard.count()
    
    if (cardCount > 0) {
      await expect(alertsCard.first()).toBeVisible()
    }
  })

  test('should load dashboard quickly', async ({ page }) => {
    const startTime = Date.now()
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    const loadTime = Date.now() - startTime

    expect(loadTime).toBeLessThan(5000)
  })
})

test.describe('Dashboard Responsiveness', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[placeholder="Email"]', 'test@example.com')
    await page.fill('input[placeholder="Password"]', 'testpassword123')
    await page.click('button:has-text("Login")')
    await page.waitForURL('/dashboard', { timeout: 10000 })
  })

  test('should be responsive on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await expect(page.locator('h1:has-text("Dashboard")')).toBeVisible()
  })

  test('should be responsive on tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await expect(page.locator('h1:has-text("Dashboard")')).toBeVisible()
  })

  test('should be responsive on desktop viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await expect(page.locator('h1:has-text("Dashboard")')).toBeVisible()
  })
})

test.describe('Dashboard Role-Based Access', () => {
  test('should display content for maintainer role', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[placeholder="Email"]', 'maintainer@example.com')
    await page.fill('input[placeholder="Password"]', 'password123')
    await page.click('button:has-text("Login")')
    await page.waitForURL('/dashboard', { timeout: 10000 })

    const userCard = page.locator('.ant-card').filter({ hasText: 'User Information' })
    await expect(userCard.locator('text=/Role:.*maintainer/i')).toBeVisible()
  })

  test('should display content for operator role', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[placeholder="Email"]', 'test@example.com')
    await page.fill('input[placeholder="Password"]', 'testpassword123')
    await page.click('button:has-text("Login")')
    await page.waitForURL('/dashboard', { timeout: 10000 })

    const userCard = page.locator('.ant-card').filter({ hasText: 'User Information' })
    await expect(userCard.locator('text=/Role:.*operator/i')).toBeVisible()
  })
})
