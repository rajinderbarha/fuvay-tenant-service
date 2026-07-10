import { Page } from '@playwright/test';
import { loginViaUi } from './auth';
import { TENANT_OWNER, TENANT_READONLY } from './api';

export async function loginAsTenantOwner(page: Page) {
  await loginViaUi(page, TENANT_OWNER.email, TENANT_OWNER.password);
}

export async function loginAsTenantReadOnly(page: Page) {
  await loginViaUi(page, TENANT_READONLY.email, TENANT_READONLY.password);
}
