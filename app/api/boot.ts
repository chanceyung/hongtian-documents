import { Hono } from "hono";
import { bodyLimit } from "hono/body-limit";
import { fetchRequestHandler } from "@trpc/server/adapters/fetch";
import { appRouter } from "./router";
import { createContext } from "./context";
import { env as envConfig } from "./lib/env";
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
  ".wasm": "application/wasm",
};

const app = new Hono();

app.use(bodyLimit({ maxSize: 100 * 1024 * 1024 }));

/** 动态获取 Python 后端端口，支持运行时变化 */
function getPythonPort(): number {
  return parseInt(process.env.PYTHON_BACKEND_PORT || "8000");
}

async function proxyToPython(c: any): Promise<Response> {
  const pythonPort = getPythonPort();
  const target = `http://127.0.0.1:${pythonPort}${c.req.path}`;
  const method = c.req.method;
  const headers: Record<string, string> = {};
  c.req.raw.headers.forEach((v: string, k: string) => {
    if (k.toLowerCase() !== "host" && k.toLowerCase() !== "connection") {
      headers[k] = v;
    }
  });

  let body: BodyInit | null = null;
  if (method !== "GET" && method !== "HEAD") {
    body = await c.req.raw.arrayBuffer();
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60_000);
  try {
    const resp = await fetch(target, { method, headers, body, signal: controller.signal });
    clearTimeout(timeout);

    const contentType = resp.headers.get("content-type") || "";
    if (contentType.includes("text/event-stream")) {
      return new Response(resp.body, {
        status: resp.status,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
      });
    }
    const respHeaders = new Headers();
    resp.headers.forEach((v: string, k: string) => {
      if (k.toLowerCase() !== "transfer-encoding") respHeaders.set(k, v);
    });
    return new Response(resp.body, { status: resp.status, headers: respHeaders });
  } finally {
    clearTimeout(timeout);
  }
}

app.all("/api/magazine/*", async (c) => {
  try {
    return await proxyToPython(c);
  } catch (err: any) {
    const reason = err?.name === "AbortError" ? "timeout" : String(err);
    console.error("[Proxy /api/magazine]", reason);
    return c.json({ error: "Python backend unavailable", detail: reason }, 503);
  }
});

/**
 * 供 Python 后端回调查询用户 API Key 设置。
 * Python 后端通过 NODE_SERVER_PORT 环境变量找到本服务。
 */
app.get("/api/internal/settings", async (c) => {
  try {
    const { getDb } = await import("./queries/connection");
    const { userSettings } = await import("@db/schema");
    const { eq } = await import("drizzle-orm");
    const db = await getDb();
    const [row] = await db.select().from(userSettings)
      .where(eq(userSettings.userId, envConfig.desktopUserId));
    return c.json({
      apiKey: row?.zhipuApiKey || "",
      model: row?.zhipuModel || "glm-4-flash",
    });
  } catch (err: any) {
    return c.json({ apiKey: "", model: "glm-4-flash", error: err.message }, 500);
  }
});

app.all("/api/api-keys/*", async (c) => {
  try {
    return await proxyToPython(c);
  } catch (err: any) {
    const reason = err?.name === "AbortError" ? "timeout" : String(err);
    console.error("[Proxy /api/api-keys]", reason);
    return c.json({ error: "Python backend unavailable", detail: reason }, 503);
  }
});

app.use("/api/trpc/*", async (c) => {
  return fetchRequestHandler({
    endpoint: "/api/trpc",
    req: c.req.raw,
    router: appRouter,
    createContext,
  });
});

app.all("/api/*", (c) => {
  if (c.req.path.startsWith("/api/magazine") || c.req.path.startsWith("/api/api-keys") || c.req.path.startsWith("/api/trpc")) {
    return c.notFound();
  }
  return c.json({ error: "Not Found" }, 404);
});

if (envConfig.isProduction) {
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const publicDir = path.join(__dirname, "public");

  // 数据目录：桌面模式用 DATABASE_PATH 的父目录，Web 模式用 ./uploads
  const uploadDir = envConfig.isDesktop
    ? path.join(dirname(process.env.DATABASE_PATH || "./data/hongtian.db"), "uploads")
    : "./uploads";

  // Python 后端输出目录（桌面模式下与 uploadDir 同级）
  const outputDir = envConfig.isDesktop
    ? path.join(dirname(process.env.DATABASE_PATH || "./data/hongtian.db"), "output")
    : "./data/output";

  app.use("/uploads/*", async (c) => {
    const rel = c.req.path.slice("/uploads/".length);
    if (!rel || rel.includes("..")) return c.notFound();
    const fp = path.join(uploadDir, rel);
    if (!fs.existsSync(fp)) return c.notFound();
    const ext = path.extname(fp);
    c.header("Content-Type", MIME[ext] || "application/octet-stream");
    return c.body(fs.readFileSync(fp));
  });

  // 代理 Python 后端的输出文件下载
  app.use("/output/*", async (c) => {
    const rel = c.req.path.slice("/output/".length);
    if (!rel || rel.includes("..")) return c.notFound();
    const fp = path.join(outputDir, rel);
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
