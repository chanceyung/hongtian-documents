import { drizzle } from "drizzle-orm/sql-js";
import * as schema from "@db/schema";
import * as relations from "@db/relations";
import { runMigrations } from "./migrations";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const fullSchema = { ...schema, ...relations };

let dbInstance: ReturnType<typeof drizzle<typeof fullSchema>> | null = null;
let sqlDb: import("sql.js").Database | null = null;

export async function getDb() {
  if (dbInstance) return dbInstance;

  const initSqlJs = (await import("sql.js")).default;

  // 查找 WASM 文件
  const __dirname = path.dirname(fileURLToPath(import.meta.url));
  const wasmPaths = [
    path.join(__dirname, "sql-wasm.wasm"),
    path.join(__dirname, "node_modules", "sql.js", "dist", "sql-wasm.wasm"),
  ];
  let wasmPath: string | undefined;
  for (const p of wasmPaths) {
    if (fs.existsSync(p)) { wasmPath = p; break; }
  }

  const SQL = await initSqlJs(wasmPath ? { locateFile: () => wasmPath! } : undefined);

  const dbPath = getDatabasePath();

  const dir = path.dirname(dbPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  if (fs.existsSync(dbPath)) {
    const buffer = fs.readFileSync(dbPath);
    sqlDb = new SQL.Database(buffer);
  } else {
    sqlDb = new SQL.Database();
    runMigrations(sqlDb);
    saveDatabase(dbPath);
  }

  dbInstance = drizzle(sqlDb, { schema: fullSchema });
  return dbInstance;
}

export function getSqlDb() {
  return sqlDb;
}

export function saveDatabase(dbPath?: string) {
  if (!sqlDb) return;
  const p = dbPath || getDatabasePath();
  const data = sqlDb.export();
  const buffer = Buffer.from(data);
  fs.writeFileSync(p, buffer);
}

function getDatabasePath(): string {
  return process.env.DATABASE_PATH || "./data/hongtian.db";
}
