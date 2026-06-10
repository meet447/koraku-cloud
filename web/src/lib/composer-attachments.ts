export type ComposerAttachment = {
  id: string;
  filename: string;
  media_type: string;
  data: string;
};

const MAX_BYTES_PER_ATTACHMENT = 8 * 1024 * 1024;
const ALLOWED_ATTACHMENT_TYPES = new Set([
  "application/pdf",
  "text/plain",
  "text/markdown",
  "text/csv",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);

const EXT_TO_MIME: Record<string, string> = {
  ".pdf": "application/pdf",
  ".txt": "text/plain",
  ".md": "text/markdown",
  ".markdown": "text/markdown",
  ".csv": "text/csv",
  ".docx":
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
};

function resolveAttachmentMediaType(file: File): string | null {
  const mt = (file.type || "").toLowerCase().split(";")[0];
  if (ALLOWED_ATTACHMENT_TYPES.has(mt)) return mt;
  const name = (file.name || "").toLowerCase();
  const dot = name.lastIndexOf(".");
  if (dot < 0) return null;
  return EXT_TO_MIME[name.slice(dot)] ?? null;
}

function readOneComposerAttachment(file: File): Promise<ComposerAttachment | null> {
  const media_type = resolveAttachmentMediaType(file);
  if (!media_type || file.size > MAX_BYTES_PER_ATTACHMENT) {
    return Promise.resolve(null);
  }
  return new Promise((resolve) => {
    const id = crypto.randomUUID();
    const reader = new FileReader();
    reader.onload = () => {
      const r = String(reader.result || "");
      const m = r.match(/^data:[^;]+;base64,(.+)$/);
      if (!m?.[1]) {
        resolve(null);
        return;
      }
      resolve({
        id,
        filename: file.name || "attachment",
        media_type,
        data: m[1],
      });
    };
    reader.onerror = () => resolve(null);
    reader.readAsDataURL(file);
  });
}

export async function readComposerAttachmentsFromFiles(
  files: FileList | File[],
  maxAttachments: number,
): Promise<ComposerAttachment[]> {
  const slice = Array.from(files).slice(0, maxAttachments);
  const rows = await Promise.all(slice.map((file) => readOneComposerAttachment(file)));
  return rows.filter((row): row is ComposerAttachment => row != null);
}

export function isComposerAttachmentFile(file: File): boolean {
  return resolveAttachmentMediaType(file) != null;
}
