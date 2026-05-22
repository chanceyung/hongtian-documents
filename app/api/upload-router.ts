import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { writeFile, mkdir } from "fs/promises";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { env } from "./lib/env";

function getUploadDir(): string {
  if (env.isDesktop) {
    const dbPath = process.env.DATABASE_PATH || "./data/hongtian.db";
    return join(dirname(dbPath), "uploads");
  }
  return "./uploads";
}

export const uploadRouter = createRouter({
  upload: publicQuery.input(z.object({
    fileName: z.string(),
    fileType: z.string(),
    fileData: z.string(),
  })).mutation(async ({ input }) => {
    const uploadDir = getUploadDir();
    await mkdir(uploadDir, { recursive: true });

    const timestamp = Date.now();
    const safeName = input.fileName.replace(/[^a-zA-Z0-9._-]/g, "_");
    const fileName = `${timestamp}_${safeName}`;
    const filePath = join(uploadDir, fileName);

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
