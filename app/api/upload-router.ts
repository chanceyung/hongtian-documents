import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { writeFile } from "fs/promises";
import { mkdir } from "fs/promises";
import { join } from "path";

const UPLOAD_DIR = "./uploads";

export const uploadRouter = createRouter({
  upload: publicQuery.input(z.object({
    fileName: z.string(),
    fileType: z.string(),
    fileData: z.string(), // base64 encoded
  })).mutation(async ({ input }) => {
    await mkdir(UPLOAD_DIR, { recursive: true });

    const timestamp = Date.now();
    const safeName = input.fileName.replace(/[^a-zA-Z0-9._-]/g, "_");
    const fileName = `${timestamp}_${safeName}`;
    const filePath = join(UPLOAD_DIR, fileName);

    const buffer = Buffer.from(input.fileData, "base64");
    await writeFile(filePath, buffer);

    const fileSize = (buffer.length / 1024).toFixed(1);

    return {
      url: `/uploads/${fileName}`,
      fileName: input.fileName,
      fileSize: `${fileSize} KB`,
      fileType: input.fileType,
    };
  }),
});
