/** Local 1200 × 630 share artwork; uploaded images never leave the browser. */
export async function buildBrandArtwork(
  title: string,
  description: string,
  cover?: string,
): Promise<Blob> {
  await document.fonts.ready;
  if (/[\u0b80-\u0bff]/.test(title + description))
    await document.fonts.load(
      '400 25px "Noto Sans Tamil"',
      title + description,
    );
  const canvas = document.createElement("canvas");
  canvas.width = 1200;
  canvas.height = 630;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("This browser cannot create an image.");
  const gradient = ctx.createLinearGradient(0, 0, 1200, 630);
  gradient.addColorStop(0, "#fff8ed");
  gradient.addColorStop(0.5, "#ffe3c4");
  gradient.addColorStop(1, "#ffbb7d");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 1200, 630);
  if (cover) {
    const img = new Image();
    img.src = cover;
    await img.decode();
    const scale = Math.max(1200 / img.width, 630 / img.height);
    ctx.globalAlpha = 0.14;
    ctx.drawImage(
      img,
      (1200 - img.width * scale) / 2,
      (630 - img.height * scale) / 2,
      img.width * scale,
      img.height * scale,
    );
    ctx.globalAlpha = 1;
  }
  for (const radius of [145, 185, 225]) {
    ctx.beginPath();
    ctx.arc(1030, 290, radius, 0, Math.PI * 2);
    ctx.strokeStyle = "#c2763538";
    ctx.lineWidth = 2;
    ctx.stroke();
  }
  ctx.fillStyle = "#ffffffa8";
  ctx.beginPath();
  ctx.roundRect(925, 200, 165, 180, 30);
  ctx.fill();
  ctx.strokeStyle = "#a34b17";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(955, 245);
  ctx.quadraticCurveTo(980, 235, 1007, 254);
  ctx.quadraticCurveTo(1030, 235, 1060, 245);
  ctx.lineTo(1060, 324);
  ctx.quadraticCurveTo(1030, 315, 1007, 334);
  ctx.quadraticCurveTo(980, 315, 955, 324);
  ctx.closePath();
  ctx.moveTo(1007, 254);
  ctx.lineTo(1007, 334);
  ctx.stroke();
  ctx.fillStyle = "#8b4119";
  ctx.font = '700 22px "Plus Jakarta Sans", "Noto Sans Tamil", sans-serif';
  ctx.fillText("SASHAINFINITY  /  KEEP DISCOVERING", 65, 80);
  const lines = (text: string, maxWidth: number, maxLines: number) => {
    const result: string[] = [];
    let line = "";
    for (const word of text
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, 600)
      .split(" ")) {
      const candidate = (line + " " + word).trim();
      if (ctx.measureText(candidate).width <= maxWidth) {
        line = candidate;
        continue;
      }
      if (line) result.push(line);
      line = word;
      while (ctx.measureText(line).width > maxWidth) {
        let cut = line.length - 1;
        while (cut > 1 && ctx.measureText(line.slice(0, cut)).width > maxWidth)
          cut--;
        result.push(line.slice(0, cut));
        line = line.slice(cut);
      }
    }
    if (line) result.push(line);
    if (result.length > maxLines) {
      result.length = maxLines;
      while (ctx.measureText(result[maxLines - 1] + "…").width > maxWidth)
        result[maxLines - 1] = result[maxLines - 1].slice(0, -1);
      result[maxLines - 1] += "…";
    }
    return result;
  };
  ctx.fillStyle = "#492910";
  ctx.font = '800 55px "Plus Jakarta Sans", "Noto Sans Tamil", sans-serif';
  lines(title, 775, 3).forEach((line, i) =>
    ctx.fillText(line, 65, 185 + i * 70),
  );
  ctx.fillStyle = "#775338";
  ctx.font = '400 25px "Plus Jakarta Sans", "Noto Sans Tamil", sans-serif';
  lines(
    description || "A little curiosity. A world of possibility.",
    780,
    2,
  ).forEach((line, i) => ctx.fillText(line, 65, 430 + i * 36));
  ctx.strokeStyle = "#b8763433";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(65, 540);
  ctx.lineTo(1135, 540);
  ctx.stroke();
  ctx.fillStyle = "#8b4119";
  ctx.font = '600 20px "Plus Jakarta Sans", "Noto Sans Tamil", sans-serif';
  ctx.fillText("Learn with purpose. Share your progress.", 65, 585);
  return new Promise((resolve, reject) =>
    canvas.toBlob(
      (blob) =>
        blob ? resolve(blob) : reject(new Error("Image export failed.")),
      "image/png",
    ),
  );
}
export async function readBannerFile(file: File): Promise<string> {
  if (
    !["image/png", "image/jpeg", "image/webp"].includes(file.type) ||
    file.size > 5 * 1024 * 1024
  )
    throw new Error("Choose a PNG, JPEG or WebP image under 5 MB.");
  const url = URL.createObjectURL(file);
  try {
    const image = new Image();
    image.src = url;
    await image.decode();
    if (image.width * image.height > 20_000_000)
      throw new Error("Use an image smaller than 20 megapixels.");
    return url;
  } catch (error) {
    URL.revokeObjectURL(url);
    throw error;
  }
}
export function downloadArtwork(blob: Blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "sashainfinity-share.png";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
