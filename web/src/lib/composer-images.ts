export type ComposerImage = {
  id: string;
  media_type: string;
  data: string;
  previewUrl: string;
};

const MAX_BYTES_PER_IMAGE = 4 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
]);

function readOneComposerImage(file: File): Promise<ComposerImage | null> {
  const mt = (file.type || "").toLowerCase();
  if (!ALLOWED_IMAGE_TYPES.has(mt) || file.size > MAX_BYTES_PER_IMAGE) {
    return Promise.resolve(null);
  }
  return new Promise((resolve) => {
    const id = crypto.randomUUID();
    const previewUrl = URL.createObjectURL(file);
    const reader = new FileReader();
    reader.onload = () => {
      const r = String(reader.result || "");
      const m = r.match(/^data:[^;]+;base64,(.+)$/);
      if (!m?.[1]) {
        URL.revokeObjectURL(previewUrl);
        resolve(null);
        return;
      }
      resolve({ id, media_type: mt, data: m[1], previewUrl });
    };
    reader.onerror = () => {
      URL.revokeObjectURL(previewUrl);
      resolve(null);
    };
    reader.readAsDataURL(file);
  });
}

export async function readComposerImagesFromFiles(
  files: FileList | File[],
  maxImages: number,
): Promise<ComposerImage[]> {
  const slice = Array.from(files).slice(0, maxImages);
  const rows = await Promise.all(slice.map((file) => readOneComposerImage(file)));
  return rows.filter((row): row is ComposerImage => row != null);
}
