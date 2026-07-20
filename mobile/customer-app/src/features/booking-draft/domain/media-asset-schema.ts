import { z } from "zod";

/**
 * Mirrors app/engines/media/models.py#MediaAsset.to_dict() — the Phase 0A
 * media engine, the only upload path this sprint uses (see
 * CUSTOMER-L5-06-contract-matrix.md; the legacy signed-URL flow at
 * app/engines/media/router.py is deliberately not used).
 */
export const MEDIA_ASSET_STATUSES = ["active", "replaced", "deleted", "quarantined", "archived"] as const;

export const mediaAssetSchema = z.object({
  id: z.string().min(1),
  owner_type: z.string().min(1),
  owner_id: z.string().min(1),
  tenant_id: z.string().nullable(),
  customer_id: z.string().nullable(),
  uploaded_by_user_id: z.string().min(1),
  media_context: z.string().min(1),
  file_name_original: z.string(),
  mime_type: z.string().min(1),
  file_extension: z.string(),
  file_size_bytes: z.number().int().nonnegative(),
  storage_driver: z.string().min(1),
  is_public: z.boolean(),
  access_level: z.string().min(1),
  status: z.string().min(1),
  width: z.number().int().nullable(),
  height: z.number().int().nullable(),
  preview_url: z.string().min(1),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
});

export type ValidatedMediaAsset = z.infer<typeof mediaAssetSchema>;

/**
 * `POST /v1/media/upload` nests the asset one level deeper than every other
 * media endpoint: `{"success": true, "data": <asset>}` instead of the asset
 * directly — a real, verified backend quirk (`new_router.py#upload_media`),
 * not a client bug. This unwraps it; `get`/`list`/`replace`/`delete`
 * responses do not go through this function.
 */
export function parseUploadResponse(payload: unknown): ValidatedMediaAsset | null {
  const envelope = z.object({ success: z.boolean(), data: z.unknown() }).safeParse(payload);
  if (!envelope.success) return null;
  return parseMediaAsset(envelope.data.data);
}

export function parseMediaAsset(payload: unknown): ValidatedMediaAsset | null {
  const result = mediaAssetSchema.safeParse(payload);
  return result.success ? result.data : null;
}

const mediaAssetListSchema = z.object({
  items: z.array(z.unknown()),
  total: z.number().int().nonnegative(),
  page: z.number().int().positive(),
  page_size: z.number().int().positive(),
});

export interface MediaAssetListResult {
  items: ValidatedMediaAsset[];
  total: number;
  droppedCount: number;
}

export function parseMediaAssetList(payload: unknown): MediaAssetListResult | null {
  const envelope = mediaAssetListSchema.safeParse(payload);
  if (!envelope.success) return null;

  const items: ValidatedMediaAsset[] = [];
  let droppedCount = 0;
  for (const raw of envelope.data.items) {
    const parsed = parseMediaAsset(raw);
    if (parsed) items.push(parsed);
    else droppedCount += 1;
  }
  return { items, total: envelope.data.total, droppedCount };
}

const replaceResponseSchema = z.object({ replaced_id: z.string().min(1), new_asset: z.unknown() });
export function parseReplaceResponse(payload: unknown): { replacedId: string; newAsset: ValidatedMediaAsset } | null {
  const envelope = replaceResponseSchema.safeParse(payload);
  if (!envelope.success) return null;
  const newAsset = parseMediaAsset(envelope.data.new_asset);
  if (!newAsset) return null;
  return { replacedId: envelope.data.replaced_id, newAsset };
}

const deleteResponseSchema = z.object({ id: z.string().min(1), deleted: z.boolean() });
export function parseDeleteResponse(payload: unknown): { id: string; deleted: boolean } | null {
  const result = deleteResponseSchema.safeParse(payload);
  return result.success ? result.data : null;
}
