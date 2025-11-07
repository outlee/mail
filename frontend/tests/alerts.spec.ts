import { test, expect } from '@playwright/test'

test.describe('Alerts Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'admin@example.com')
    await page.fill('[data-testid="password-input"]', 'password')
    await page.click('[data-testid="login-button"]')
    
    // Wait for dashboard to load
    await page.waitForURL('/dashboard')
    await expect(page.locator('h1')).toContainText('Dashboard')
  })

  test('should navigate to alerts page', async ({ page }) => {
    // Click on alerts management card
    await page.click('text=View Alerts')
    
    // Should navigate to alerts page
    await page.waitForURL('/alerts')
    await expect(page.locator('h2')).toContainText('Alerts')
  })

  test('should navigate to alert policies page', async ({ page }) => {
    // Navigate to alerts first
    await page.click('text=View Alerts')
    await page.waitForURL('/alerts')
    
    // Click on Alert Policies tab
    await page.click('text=Alert Policies')
    
    // Should navigate to alert policies page
    await page.waitForURL('/alerts/policies')
    await expect(page.locator('h2')).toContainText('Alert Policies')
  })

  test('should display alert policies table', async ({ page }) => {
    // Navigate to alert policies
    await page.click('text=View Alerts')
    await page.waitForURL('/alerts')
    await page.click('text=Alert Policies')
    await page.waitForURL('/alerts/policies')
    
    // Should display policies table
    await expect(page.locator('table')).toBeVisible()
    await expect(page.locator('text=High MTBF Alert')).toBeVisible()
    await expect(page.locator('text=Low Availability Warning')).toBeVisible()
  })

  test('should create new alert policy', async ({ page }) => {
    // Navigate to alert policies
    await page.click('text=View Alerts')
    await page.waitForURL('/alerts')
    await page.click('text=Alert Policies')
    await page.waitForURL('/alerts/policies')
    
    // Click create policy button
    await page.click('text=Create Policy')
    
    // Should open drawer
    await expect(page.locator('.ant-drawer-title')).toContainText('Create Alert Policy')
    
    // Fill form fields
    await page.fill('[placeholder="Enter policy name"]', 'Test Alert Policy')
    await page.fill('[placeholder="Enter policy description"]', 'Test description')
    await page.selectOption('select[name="metric"]', 'mtbf')
    await page.selectOption('select[name="comparator"]', 'greater_than')
    await page.fill('input[type="number"]', '500')
    await page.selectOption('select[name="severity"]', 'high')
    
    // Add recipient
    await page.click('text=Add Recipient')
    await page.selectOption('select:has-text("Type")', 'email')
    await page.fill('input[placeholder="Enter email address"]', 'test@example.com')
    
    // Submit form
    await page.click('text=Create')
    
    // Should show success message and close drawer
    await expect(page.locator('.ant-message')).toContainText('created successfully')
    await expect(page.locator('.ant-drawer')).not.toBeVisible()
    
    // Should show new policy in table
    await expect(page.locator('text=Test Alert Policy')).toBeVisible()
  })

  test('should validate form fields', async ({ page }) => {
    // Navigate to alert policies
    await page.click('text=View Alerts')
    await page.waitForURL('/alerts')
    await page.click('text=Alert Policies')
    await page.waitForURL('/alerts/policies')
    
    // Click create policy button
    await page.click('text=Create Policy')
    
    // Try to submit empty form
    await page.click('text=Create')
    
    // Should show validation errors
    await expect(page.locator('text=Enter policy name')).toBeVisible()
    await expect(page.locator('text=Select a metric')).toBeVisible()
  })

  test('should display alerts list', async ({ page }) => {
    // Navigate to alerts
    await page.click('text=View Alerts')
    await page.waitForURL('/alerts')
    
    // Should display alerts table
    await expect(page.locator('table')).toBeVisible()
    await expect(page.locator('text=High MTBF Alert')).toBeVisible()
    await expect(page.locator('text=Low Availability Warning')).toBeVisible()
  })

  test('should filter alerts by status', async ({ page }) => {
    // Navigate to alerts
    await page.click('text=View Alerts')
    await page.waitForURL('/alerts')
    
    // Open filter panel
    await page.click('text=Filters')
    
    // Filter by status
    await page.click('select[placeholder*="Select status"]')
    await page.click('text=Active')
    
    // Should show filtered results
    await expect(page.locator('text=High MTBF Alert')).toBeVisible()
  })

  test('should acknowledge alert', async ({ page }) => {
    // Navigate to alerts
    await page.click('text=View Alerts')
    await page.waitForURL('/alerts')
    
    // Find active alert and acknowledge it
    const acknowledgeButton = page.locator('button:has-text("Acknowledge")').first()
    await expect(acknowledgeButton).toBeVisible()
    
    await acknowledgeButton.click()
    await page.click('text=OK') // Confirm acknowledgment
    
    // Should show success message
    await expect(page.locator('.ant-message')).toContainText('acknowledged successfully')
  })

  test('should view alert details', async ({ page }) => {
    // Navigate to alerts
    await page.click('text=View Alerts')
    await page.waitForURL('/alerts')
    
    // Click on view button for first alert
    await page.click('button:has-text("View")').first()
    
    // Should show detail modal
    await expect(page.locator('.ant-modal-title')).toContainText('Alert Details')
    await expect(page.locator('text=Policy')).toBeVisible()
    await expect(page.locator('text=Message')).toBeVisible()
    await expect(page.locator('text=History Timeline')).toBeVisible()
  })

  test('should respect role-based access', async ({ page }) => {
    // Login as operator (read-only user)
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'operator@example.com')
    await page.fill('[data-testid="password-input"]', 'password')
    await page.click('[data-testid="login-button"]')
    
    // Navigate to alert policies
    await page.click('text=View Alerts')
    await page.waitForURL('/alerts')
    await page.click('text=Alert Policies')
    
    // Should not show create button for operators
    await expect(page.locator('text=Create Policy')).not.toBeVisible()
    
    // Should not show edit/delete buttons
    await expect(page.locator('text=Edit')).not.toBeVisible()
    await expect(page.locator('text=Delete')).not.toBeVisible()
  })
})