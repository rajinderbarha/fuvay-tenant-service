import { z } from "zod";

/**
 * Contracts for /v1/public/legal/* (app/engines/legal_documents/public_router.py).
 *
 * Public and unauthenticated by design — these are read before anyone has an
 * account, from the signup footer as well as the profile screen.
 */

export const legalDocumentSchema = z.object({
  id: z.string(),
  doc_type: z.string(),
  audience: z.string(),
  locale: z.string(),
  version: z.string(),
  title: z.string(),
  summary: z.string().nullable(),
  body: z.string(),
  body_format: z.string(),
  effective_at: z.string().nullable(),
  published_at: z.string().nullable(),
});

export const legalDocumentIndexEntrySchema = z.object({
  doc_type: z.string(),
  title: z.string(),
  version: z.string(),
  audience: z.string(),
  locale: z.string(),
  effective_at: z.string().nullable(),
  path: z.string(),
});

export const legalDocumentIndexSchema = z.object({
  documents: z.array(legalDocumentIndexEntrySchema),
  total: z.number(),
});

export type LegalDocument = z.infer<typeof legalDocumentSchema>;
export type LegalDocumentIndexEntry = z.infer<typeof legalDocumentIndexEntrySchema>;
