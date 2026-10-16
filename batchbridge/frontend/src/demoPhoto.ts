export async function createDemoPhoto(): Promise<File> {
  const canvas = document.createElement("canvas");
  canvas.width = 960;
  canvas.height = 620;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Unable to create the demo photo in this browser");
  context.fillStyle = "#e8e5da";
  context.fillRect(0, 0, 960, 620);
  context.fillStyle = "#123e30";
  context.fillRect(80, 60, 800, 500);
  context.fillStyle = "#f6eedc";
  context.font = "bold 30px sans-serif";
  context.fillText("SWEETCO · FICTIONAL DEMO PACKAGING", 120, 120);
  context.font = "bold 42px Georgia";
  context.fillText("Alpine Milk Chocolate", 120, 200);
  context.font = "26px sans-serif";
  context.fillText("100g    |    CHOC-100    |    LOT 38", 120, 250);
  context.fillText("Best before: 31 AUG 2027", 120, 295);
  context.fillStyle = "#fff";
  context.fillRect(120, 330, 540, 165);
  context.fillStyle = "#16241d";
  // Decorative stripes illustrate a scan. They do not encode a real retail barcode.
  for (let index = 0, x = 145; x < 630; index += 1) {
    const width = [3, 6, 2, 5, 3, 2, 7][index % 7];
    context.fillRect(x, 345, width, 95);
    x += width + 4;
  }
  context.font = "bold 28px monospace";
  context.fillText("DEMO-CHOC-38", 205, 480);
  context.fillStyle = "#f6eedc";
  context.font = "18px sans-serif";
  context.fillText("Simulated barcode lookup · no camera decoding", 120, 535);
  const blob = await new Promise<Blob>((resolve, reject) =>
    canvas.toBlob((value) => value ? resolve(value) : reject(new Error("Demo photo creation failed")), "image/png"),
  );
  return new File([blob], "demo-chocolate-lot-38.png", { type: "image/png" });
}
