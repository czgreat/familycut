async function fetchImageBlob(url: string): Promise<Blob> {
  const response = await fetch(url, { credentials: "same-origin" });
  if (!response.ok) {
    throw new Error(`图片加载失败：${response.status}`);
  }
  return response.blob();
}

function toImageFile(blob: Blob, fileName: string): File {
  const type = blob.type || "image/png";
  return new File([blob], fileName, { type });
}

export async function shareImageFile(input: {
  title: string;
  text: string;
  url: string;
  fileName: string;
}): Promise<"shared" | "downloaded"> {
  const blob = await fetchImageBlob(input.url);
  const file = toImageFile(blob, input.fileName);

  if (navigator.canShare?.({ files: [file] }) && navigator.share) {
    await navigator.share({
      title: input.title,
      text: input.text,
      files: [file]
    });
    return "shared";
  }

  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = input.fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
  return "downloaded";
}

export async function downloadUrl(url: string, fileName: string): Promise<void> {
  const blob = await fetchImageBlob(url);
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}
