import { test, expect, Page } from '@playwright/test';

/**
 * A dead session must never render page content.
 *
 * Both portals put the shell OUTSIDE the guard and page content inside it, so
 * the sidebar painting is expected and fine. What must never appear is the
 * gated content region -- `.admin-content` / `.provider-content`, the elements
 * that hold {children}.
 *
 * The admin case is aimed at the exact regression: /admin/dashboard is declared
 * `requiredPermission: ""`, and the old gate read "" as "allow". Combined with a
 * failed /auth/me collapsing to `permissions = []`, that rendered the dashboard
 * to an expired token. /admin/tenants (a permissioned route) is the control.
 *
 * Both apps refresh on 401, so a realistic dead session invalidates BOTH the
 * access and the refresh token -- otherwise the client silently re-auths and
 * nothing is being tested.
 */

const APP = (process.env.E2E_APP || 'admin') as 'admin' | 'tenant';

const CFG = APP === 'admin'
  ? {
      creds: { email: 'admin@serviceos.in', password: 'Password123!' },
      keys: ['serviceos_admin_token', 'serviceos_admin_refresh'],
      content: '.admin-content',
      paths: ['/admin/dashboard', '/admin/tenants'],
    }
  : {
      creds: { email: 'provider@serviceos.in', password: 'Password123!' },
      keys: ['serviceos_tenant_token', 'serviceos_tenant_refresh'],
      content: '.provider-content',
      paths: ['/dashboard'],
    };

const PROBE = '__session_leak_probe';

/**
 * Records every non-empty text state of the gated content region.
 *
 * A single assertion after the redirect would miss a flash, which is half the
 * bug -- the tenant portal rendered real data and THEN redirected. So this
 * samples on every DOM mutation plus a 10ms interval, and writes findings to
 * sessionStorage, which clearSession() does not clear and which therefore
 * survives the redirect to /login.
 */
async function installLeakProbe(page: Page) {
  await page.addInitScript(({ sel, key }) => {
    const push = (t: string) => {
      try {
        const arr = JSON.parse(sessionStorage.getItem(key) || '[]');
        arr.push(t);
        sessionStorage.setItem(key, JSON.stringify(arr));
      } catch { /* storage unavailable: nothing to record into */ }
    };
    const sample = () => {
      const el = document.querySelector(sel);
      if (!el) return;
      // Breadcrumbs render inside the content box but are shell chrome derived
      // from the URL, not gated page data, and they sit outside the guard by
      // design. Excluded, or the probe reports the path the user typed as a
      // leak. textContent rather than innerText so visually-hidden text counts
      // too -- a leak that is merely off-screen is still a leak.
      const clone = el.cloneNode(true) as HTMLElement;
      clone.querySelectorAll('nav[aria-label="Breadcrumb"]').forEach((n) => n.remove());
      const text = (clone.textContent || '').trim();
      if (text.length > 0) push(text.slice(0, 300));
    };
    const start = () => {
      new MutationObserver(sample).observe(document.documentElement, {
        childList: true, subtree: true, characterData: true,
      });
      sample();
      setInterval(sample, 10);
    };
    if (document.documentElement) start();
    else addEventListener('DOMContentLoaded', start);
  }, { sel: CFG.content, key: PROBE });
}

async function login(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('serviceos_disable_tour_e2e', 'true');
    localStorage.setItem('serviceos-tenant-tour-done', 'true');
  });
  await page.goto('/login');
  await page.locator('input[type="email"]').fill(CFG.creds.email);
  await page.locator('input[type="password"]').fill(CFG.creds.password);
  await page.locator('button[type="submit"]').click();
  await expect(page).not.toHaveURL(/\/login/, { timeout: 120_000 });
}

/**
 * A guard that redirects before the document finishes loading ABORTS the
 * navigation, and Playwright surfaces that as net::ERR_ABORTED. That is the
 * gate doing its job as early as possible -- the tenant portal short-circuits
 * without even asking the server when no token is present -- so it is a pass
 * condition, not a failure. Any other navigation error still propagates.
 */
async function gotoAllowingRedirect(page: Page, path: string) {
  try {
    await page.goto(path);
  } catch (e: any) {
    if (!String(e?.message ?? e).includes('ERR_ABORTED')) throw e;
  }
}

async function readProbe(page: Page): Promise<string[]> {
  return page.evaluate((k) => JSON.parse(sessionStorage.getItem(k) || '[]'), PROBE);
}

test.describe(`[${APP}] a dead session renders no content`, () => {

  // Next dev compiles a route on its first request; on this machine that can
  // exceed the config's 60s default and fail a test for reasons unrelated to
  // sessions.
  test.describe.configure({ timeout: 180_000 });

  test('positive control: a LIVE session does render content', async ({ page }) => {
    // Without this, "nothing rendered" below proves nothing -- it could just
    // mean the probe or the selector is wrong.
    await login(page);
    await installLeakProbe(page);
    await page.evaluate((k) => sessionStorage.removeItem(k), PROBE);

    await page.goto(CFG.paths[0]);
    await expect(page.locator(CFG.content)).not.toBeEmpty({ timeout: 120_000 });

    const seen = await readProbe(page);
    expect(seen.length, 'probe must observe content when the session is valid').toBeGreaterThan(0);
  });

  for (const path of CFG.paths) {
    test(`expired token: ${path} never paints`, async ({ page }) => {
      await login(page);
      await installLeakProbe(page);

      await page.evaluate(({ keys, k }) => {
        sessionStorage.removeItem(k);
        // Present but not accepted -- an expired token is still a string, which
        // is exactly what the old tenant check was fooled by.
        localStorage.setItem(keys[0], 'expired.invalid.token');
        localStorage.setItem(keys[1], 'expired.invalid.refresh');
      }, { keys: CFG.keys, k: PROBE });

      await gotoAllowingRedirect(page, path);
      await page.waitForURL(/\/login/, { timeout: 120_000 });

      const leaked = await readProbe(page);
      expect(leaked, `content painted before the redirect: ${JSON.stringify(leaked).slice(0, 500)}`).toEqual([]);
    });
  }

  // ---------------------------------------------------------------------
  // The other half of the contract. A guard that withholds content is only
  // half-right if it also throws away good sessions: the first version of this
  // fix treated ANY failed /auth/me as "signed out", so a network blip, a 500,
  // or a request aborted by clicking a link logged out a valid user. Caught by
  // the browser, not by review -- me() rejected with "Failed to fetch" and the
  // guard cleared the session.
  // ---------------------------------------------------------------------

  for (const [label, failure] of [
    ['a network failure', (route: any) => route.abort('failed')],
    ['a server error',    (route: any) => route.fulfill({
      status: 500, contentType: 'application/json',
      body: JSON.stringify({ error_code: 'SERVER_ERROR', detail: 'boom' }),
    })],
  ] as const) {
    test(`${label} must NOT sign you out`, async ({ page }) => {
      await login(page);
      await page.route('**/v1/auth/me', failure as any);

      await gotoAllowingRedirect(page, CFG.paths[0]);
      await page.waitForTimeout(8000); // outlast the guard's retries

      expect(page.url(), 'a session that was never refused must not be ended').not.toMatch(/\/login/);
      const token = await page.evaluate((k) => localStorage.getItem(k), CFG.keys[0]);
      expect(token, 'the token must survive a failure that says nothing about it').toBeTruthy();

      // Unsure is not the same as allowed: content stays withheld, with a way back.
      await expect(page.getByRole('button', { name: /try again/i })).toBeVisible({ timeout: 20_000 });
    });
  }

  test(`after logout: ${CFG.paths[0]} never paints`, async ({ page }) => {
    // The user's other case: sign out, then hit a protected URL directly
    // (typed, bookmarked, or the browser Back button).
    await login(page);
    await installLeakProbe(page);
    await page.evaluate(({ keys, k }) => {
      sessionStorage.removeItem(k);
      keys.forEach((key: string) => localStorage.removeItem(key));
    }, { keys: CFG.keys, k: PROBE });

    await gotoAllowingRedirect(page, CFG.paths[0]);
    await page.waitForURL(/\/login/, { timeout: 120_000 });

    const leaked = await readProbe(page);
    expect(leaked, `content painted while signed out: ${JSON.stringify(leaked).slice(0, 500)}`).toEqual([]);
  });
});
