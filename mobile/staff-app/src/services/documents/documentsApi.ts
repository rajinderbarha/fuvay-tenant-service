import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { DocumentsDetailDTO, DocumentVersionDTO } from "./types";

export function getDocuments(signal?: AbortSignal): Promise<ApiResult<DocumentsDetailDTO>> {
  return authenticatedRequest<DocumentsDetailDTO>(`/v1/staff/me/documents`, { method: "GET", signal });
}

export function submitDocument(input: {
  docType: string; mediaAssetId: string; documentNumber?: string; issueDate?: string; expiryDate?: string;
}): Promise<ApiResult<DocumentVersionDTO>> {
  return authenticatedRequest<DocumentVersionDTO>(`/v1/staff/me/documents`, {
    method: "POST",
    body: {
      doc_type: input.docType, media_asset_id: input.mediaAssetId,
      document_number: input.documentNumber ?? null, issue_date: input.issueDate ?? null, expiry_date: input.expiryDate ?? null,
    },
  });
}

export function getDocumentHistory(docType: string, signal?: AbortSignal): Promise<ApiResult<{ versions: DocumentVersionDTO[] }>> {
  return authenticatedRequest<{ versions: DocumentVersionDTO[] }>(`/v1/staff/me/documents/${encodeURIComponent(docType)}/history`, { method: "GET", signal });
}
