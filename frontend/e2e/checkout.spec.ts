import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

async function login(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Enter workspace' }).click();
  await expect(page.getByRole('heading', { name: 'The essentials' })).toBeVisible();
}

test('purchase persists, supports order questions, and cancellation refunds demo stock', async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await login(page);
  const products = await (await page.request.get('/api/products')).json();
  for (const row of products) {
    const photo = await page.request.get(row.image_url);
    expect(photo.status()).toBe(200);
    expect(photo.headers()['content-type']).toContain('image/jpeg');
  }
  const product = products.find((row: { name: string }) => row.name === 'Everyday Cotton Tee');
  const card = page.locator('.product-card').filter({ has: page.getByRole('heading', { name: product.name, exact: true }) });
  await card.getByLabel(`Size for ${product.name}`).selectOption('M');
  await card.getByRole('button', { name: `Add ${product.name} to cart` }).click();
  await page.getByRole('button', { name: 'Cart (1)', exact: true }).click();
  await page.getByLabel(`Quantity for ${product.name} M`).selectOption('2');
  await page.getByRole('button', { name: 'Review order', exact: true }).click();
  await expect(page.locator('.checkout-summary')).toContainText('Confirmed total');
  const completed = page.waitForResponse(response => response.url().endsWith('/api/checkout') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Confirm & simulate payment · $48.00', exact: true }).click();
  const receipt = await (await completed).json();
  expect(receipt.status).toBe('approved');
  await expect(page.getByRole('heading', { name: receipt.order.number, exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('checkout-receipt.png'), fullPage: true });
  await page.getByRole('button', { name: 'View my orders', exact: true }).click();
  await page.locator('.order-list-card').filter({ hasText: receipt.order.number }).click();
  await expect(page.locator('.order-detail')).toContainText('M');
  await page.reload();
  await page.getByRole('button', { name: 'My orders', exact: true }).click();
  await page.locator('.order-list-card').filter({ hasText: receipt.order.number }).click();
  await page.getByRole('button', { name: 'Get order help', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Message', exact: true })).toHaveValue(new RegExp(receipt.order.number));
  await page.getByRole('textbox', { name: 'Message', exact: true }).fill(`Where is my order ${receipt.order.number}?`);
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  await expect(page.locator('.message-bubble').filter({ hasText: receipt.order.number }).last()).toBeVisible();
  await expect(page.locator('.message-bubble').last()).toContainText(/processing|preparing/i);
  await page.getByRole('button', { name: 'My orders', exact: true }).click();
  await page.locator('.order-list-card').filter({ hasText: receipt.order.number }).click();
  await page.getByRole('button', { name: 'Cancel order', exact: true }).click();
  await page.getByRole('button', { name: 'Review request', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm cancellation', exact: true }).click();
  await expect(page.locator('.order-detail')).toContainText('Refunded');
  const after = await (await page.request.get('/api/products')).json();
  expect(after.find((row: { id: string }) => row.id === product.id).stock).toBe(product.stock);
  expect(errors).toEqual([]);
});

test('mobile decline keeps the cart and a fresh approval creates one order', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  const before = await (await page.request.get('/api/orders')).json();
  await page.getByRole('button', { name: 'Add Stainless Steel Water Bottle to cart', exact: true }).click();
  await page.getByRole('button', { name: 'Cart (1)', exact: true }).click();
  await page.getByLabel('Demo card outcome').selectOption('declined');
  await page.getByRole('button', { name: 'Review order', exact: true }).click();
  await page.getByRole('button', { name: /Confirm & simulate payment/ }).click();
  await expect(page.getByText('Simulated payment declined.', { exact: true })).toBeVisible();
  expect((await (await page.request.get('/api/orders')).json()).length).toBe(before.length);
  await expect(page.getByRole('button', { name: 'Cart (1)', exact: true })).toBeVisible();
  await page.getByLabel('Demo card outcome').selectOption('approved');
  await page.getByRole('button', { name: 'Review order', exact: true }).click();
  await page.getByRole('button', { name: /Confirm & simulate payment/ }).click();
  await expect(page.getByRole('heading', { name: 'Your demo order is in.', exact: true })).toBeVisible();
  expect((await (await page.request.get('/api/orders')).json()).length).toBe(before.length + 1);
  await expect(page.getByRole('button', { name: 'Cart (0)', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('checkout-mobile.png'), fullPage: true });
});
