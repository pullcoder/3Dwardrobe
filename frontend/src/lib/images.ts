export const MAX_FILE_BYTES = 10 * 1024 * 1024;
export const MAX_PIXELS = 20_000_000;
export const IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

export async function checkImage(file: File): Promise<void> {
  if (!IMAGE_TYPES.includes(file.type))
    throw new Error("JPEG, PNG, WebP 사진을 선택해 주세요.");
  if (!file.size || file.size > MAX_FILE_BYTES)
    throw new Error("사진은 한 장당 10 MiB 이하여야 합니다.");
  const url = URL.createObjectURL(file);
  try {
    const image = new Image();
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve();
      image.onerror = () =>
        reject(
          new Error("사진을 읽을 수 없습니다. 다른 사진을 선택해 주세요."),
        );
      image.src = url;
    });
    if (image.naturalWidth * image.naturalHeight > MAX_PIXELS)
      throw new Error("사진 해상도는 2천만 화소 이하여야 합니다.");
  } finally {
    URL.revokeObjectURL(url);
  }
}
