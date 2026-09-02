import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";
import { ENV } from "../../config/environment";
import { getInMemoryAccessToken } from "../session/tokenVault";

function safeName(value: string): string {
  return value.replace(/[^A-Za-z0-9-]/g, "-");
}

/** Download the authenticated, immutable provider warranty evidence and open
 * the device share/save sheet. The access token is sent as a header and is
 * never placed in the URL or persisted in the document. */
export async function downloadWarrantyCertificate(
  downloadPath: string,
  certificateNumber: string,
): Promise<void> {
  const token = getInMemoryAccessToken();
  if (!token) throw new Error("Please sign in again to download this certificate.");
  if (!FileSystem.cacheDirectory) throw new Error("Document storage is unavailable on this device.");

  const url = `${ENV.apiBaseUrl.replace(/\/$/, "")}/${downloadPath.replace(/^\//, "")}`;
  const target = `${FileSystem.cacheDirectory}${safeName(certificateNumber)}.html`;
  const result = await FileSystem.downloadAsync(url, target, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (result.status < 200 || result.status >= 300) {
    await FileSystem.deleteAsync(target, { idempotent: true });
    throw new Error(result.status === 410
      ? "The warranty certificate download period has ended."
      : "Could not download the warranty certificate.");
  }
  if (!(await Sharing.isAvailableAsync())) {
    throw new Error("Saving or sharing files is not available on this device.");
  }
  await Sharing.shareAsync(result.uri, {
    mimeType: "text/html",
    dialogTitle: `Warranty ${certificateNumber}`,
  });
}
