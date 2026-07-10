import { Page } from '@playwright/test';
import { loginViaUi } from './auth';
import { SUPER_ADMIN } from './api';

export async function loginAsSuperAdmin(page: Page) {
  await loginViaUi(page, SUPER_ADMIN.email, SUPER_ADMIN.password);
}
