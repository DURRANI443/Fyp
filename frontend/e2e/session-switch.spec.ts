import { expect, test } from '@playwright/test';
import type { Page, Response, TestInfo } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';

async function attachNetwork(testInfo: TestInfo, name: string, report: unknown) {
  await mkdir(testInfo.outputDir, { recursive: true });
  const path = testInfo.outputPath(name);
  await writeFile(path, JSON.stringify(report, null, 2), 'utf8');
  await testInfo.attach(name, { path, contentType: 'application/json' });
}

async function enterWorkspace(page: Page, role: 'Customer' | 'Support') {
  await page.getByRole('button', { name: new RegExp(`^${role} `) }).click();
  await page.getByRole('button', { name: 'Enter workspace' }).click();
  await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible();
}

async function signOut(page: Page) {
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Enter workspace' })).toBeVisible();
}

async function resolveTicket(page: Page) {
  await page.getByRole('button', { name: 'Resolve conversation', exact: true }).click();
  await page.getByLabel('Resolution summary').fill('Confirmed the reply and finished this session-switch regression workflow.');
  await page.getByRole('button', { name: 'Mark as resolved' }).click();
  await expect(page.getByRole('button', { name: 'Mark as resolved' })).toHaveCount(0);
}

async function createHandoff(page: Page, question: string) {
  await page.getByRole('button', { name: 'Get support', exact: true }).click();
  await page.getByRole('textbox', { name: 'Message', exact: true }).fill(question);
  const sent = page.waitForResponse(response => /\/api\/conversations\/[^/]+\/messages$/.test(new URL(response.url()).pathname));
  await page.getByRole('button', { name: 'Send message' }).click();
  const conversation = await (await sent).json();
  await expect(page.locator('.citations')).toBeVisible();
  await page.getByRole('button', { name: 'Talk to a person' }).click();
  await expect(page.getByText(/automatic replies are paused/)).toBeVisible();
  return conversation.id as string;
}

function apiFailure(response: Response) {
  return new URL(response.url()).pathname.startsWith('/api/') && response.status() >= 400;
}

test('same-page customer to staff switch stops customer polling and preserves the staff reply', async ({ page }, testInfo) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await enterWorkspace(page, 'Customer');
  const question = 'What is your return policy?';
  const conversationId = await createHandoff(page, question);
  await signOut(page);
  await enterWorkspace(page, 'Support');

  const failures: string[] = [];
  const customerRequests: string[] = [];
  const started = Date.now();
  const network: { method: string; path: string; status: number }[] = [];
  page.on('response', response => {
    const path = new URL(response.url()).pathname;
    if (path.startsWith('/api/')) network.push({ method: response.request().method(), path, status: response.status() });
  });
  page.on('response', response => { if (apiFailure(response)) failures.push(`${response.status()} ${new URL(response.url()).pathname}`); });
  page.on('request', request => { if (new URL(request.url()).pathname === `/api/conversations/${conversationId}`) customerRequests.push(request.url()); });

  await page.locator('.ticket-card').filter({ hasText: question }).click();
  await page.getByRole('button', { name: 'Assign to me' }).click();
  const reply = 'Your return request will be reviewed by the returns team. This same-page reply is saved.';
  await page.getByLabel('Reply to Alex Morgan').fill(reply);
  await page.getByRole('button', { name: 'Send reply' }).click();
  await expect(page.locator('.message-bubble').filter({ hasText: reply })).toBeVisible();

  // Observe more than two customer (4s) and staff (5s) polling intervals.
  await page.waitForTimeout(11000);
  expect(customerRequests).toEqual([]);
  expect(failures).toEqual([]);
  await attachNetwork(testInfo, 'same-page-after-switch-network.json', {
    observation_ms: Date.now() - started, customerRequests, failures, network,
  });

  await resolveTicket(page);
  await signOut(page);
  await enterWorkspace(page, 'Customer');
  await page.getByRole('button', { name: 'Get support', exact: true }).click();
  await page.locator('.conversation-item').filter({ hasText: question }).click();
  await expect(page.locator('.message-bubble').filter({ hasText: reply })).toBeVisible();
});

test('another tab changing the shared account clears the old customer workspace and stops polling', async ({ page, context }, testInfo) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await enterWorkspace(page, 'Customer');
  const question = 'What is your shipping policy?';
  const conversationId = await createHandoff(page, question);

  // Tabs in the same context share the real HTTP-only session cookie.
  const switchingTab = await context.newPage();
  await switchingTab.goto('/', { waitUntil: 'domcontentloaded' });
  await expect(switchingTab.getByRole('button', { name: 'Get support', exact: true })).toBeVisible();
  await page.waitForResponse(response => new URL(response.url()).pathname === `/api/conversations/${conversationId}` && response.status() === 200);
  await signOut(switchingTab);
  await enterWorkspace(switchingTab, 'Support');

  const failures: string[] = [];
  const customerRequests: string[] = [];
  const started = Date.now();
  const network: { tab: string; method: string; path: string; status: number }[] = [];
  for (const [tab, name] of [[page, 'old-customer'], [switchingTab, 'new-staff']] as const) {
    tab.on('response', response => {
      const path = new URL(response.url()).pathname;
      if (path.startsWith('/api/')) network.push({ tab: name, method: response.request().method(), path, status: response.status() });
      if (apiFailure(response)) failures.push(`${name}: ${response.status()} ${path}`);
    });
  }
  page.on('request', request => { if (new URL(request.url()).pathname === `/api/conversations/${conversationId}`) customerRequests.push(request.url()); });
  await switchingTab.locator('.ticket-card').filter({ hasText: question }).click();
  await switchingTab.getByRole('button', { name: 'Assign to me' }).click();
  const reply = 'A staff member can reply after an account switch in a shared browser.';
  await switchingTab.getByLabel('Reply to Alex Morgan').fill(reply);
  await switchingTab.getByRole('button', { name: 'Send reply' }).click();
  await expect(switchingTab.getByText(reply, { exact: true })).toBeVisible();

  // A session change must remove private stale UI before another polling cycle.
  await expect(page.getByRole('button', { name: 'Enter workspace' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Message', exact: true })).toHaveCount(0);
  await page.waitForTimeout(11000);
  expect(customerRequests).toEqual([]);
  expect(failures).toEqual([]);
  await attachNetwork(testInfo, 'shared-tab-after-switch-network.json', {
    observation_ms: Date.now() - started, customerRequests, failures, network,
  });
  await page.screenshot({ path: testInfo.outputPath('old-customer-tab-cleared.png'), fullPage: true });
  await switchingTab.screenshot({ path: testInfo.outputPath('new-staff-tab-replied.png'), fullPage: true });
  await resolveTicket(switchingTab);
  await switchingTab.close();
});
