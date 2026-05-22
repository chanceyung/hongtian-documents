import { Hono } from "hono";
import { bodyLimit } from "hono/body-limit";
import { fetchRequestHandler } from "@trpc/server/adapters/fetch";
import { appRouter } from "./router";
import { createContext } from "./context";
import { env } from "./lib/env";
import { serve } from "@hono/node-server";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";

const MIME: Record<string, string> = {
  ".html": "text/html", ".js": "application/javascript", ".css": "text/css",
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml", ".ico": "image/x-icon", ".json": "application/json",
  ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf",
  ".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  ".md": "text/markdown",
};

const app = new Hono();

app.use(bodyLimit({ maxSize: 50 * 1024 * 1024 }));

app.use("/api/trpc/*", async (c) => {
  return fetchRequestHandler({
    endpoint: "/api/trpc",
    req: c.req.raw,
    router: appRouter,
    createContext,
  });
});
app.all("/api/*", (c) => c.json({ error: "Not Found" }, 404));

if (env.isProduction) {
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const publicDir = path.join(__dirname, "public");

  const uploadDir = env.isDesktop
    ? path.join(dirname(process.env.DATABASE_PATH || "./data/hongtian.db"), "uploads")
    : "./uploads";

  app.use("/uploads/*", async (c) => {
    const rel = c.req.path.slice("/uploads/".length);
    if (!rel || rel.includes("..")) return c.notFound();
    const fp = path.join(uploadDir, rel);
    if (!fs.existsSync(fp)) return c.notFound();
    const ext = path.extname(fp);
    c.header("Content-Type", MIME[ext] || "application/octet-stream");
    return c.body(fs.readFileSync(fp));
  });

  app.use("/assets/*", async (c) => {
    const rel = c.req.path.slice(1);
    const fp = path.join(publicDir, rel);
    if (!fs.existsSync(fp)) return c.notFound();
    const ext = path.extname(fp);
    c.header("Content-Type", MIME[ext] || "application/octet-stream");
    return c.body(fs.readFileSync(fp));
  });

  app.use("/*", async (c) => {
    const rel = c.req.path.slice(1);
    if (!rel || rel.includes("..")) return c.notFound();
    const ext = path.extname(rel);
    if (!ext) return c.notFound();
    const fp = path.join(publicDir, rel);
    if (!fs.existsSync(fp)) return c.notFound();
    c.header("Content-Type", MIME[ext] || "application/octet-stream");
    return c.body(fs.readFileSync(fp));
  });

  app.notFound((c) => {
    const accept = c.req.header("accept") ?? "";
    if (!accept.includes("text/html")) {
      return c.json({ error: "Not Found" }, 404);
    }
    const indexPath = path.join(publicDir, "index.html");
    if (fs.existsSync(indexPath)) {
      return c.html(fs.readFileSync(indexPath, "utf-8"));
    }
    return c.text("Not Found", 404);
  });
}

const port = parseInt(process.env.PORT || "3000");
serve({ fetch: app.fetch, port }, () => {
  console.log(`Server running on http://localhost:${port}/`);
});
