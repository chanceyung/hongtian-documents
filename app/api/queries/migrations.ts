import type { Database } from "sql.js";

const CREATE_USERS = `
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL DEFAULT '桌面用户',
  email TEXT,
  avatar TEXT,
  role TEXT NOT NULL DEFAULT 'admin',
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);`;

const CREATE_CONVERSATIONS = `
CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  title TEXT NOT NULL DEFAULT '新对话',
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);`;

const CREATE_MESSAGES = `
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversations(id),
  role TEXT NOT NULL CHECK(role IN ('user','assistant')),
  content TEXT NOT NULL,
  attachments TEXT,
  created_at INTEGER NOT NULL DEFAULT (unixepoch())
);`;

const CREATE_TASKS = `
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversations(id),
  user_id TEXT NOT NULL REFERENCES users(id),
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','running','completed','failed')),
  output_format TEXT NOT NULL DEFAULT 'pdf' CHECK(output_format IN ('pdf','pptx')),
  output_file TEXT,
  progress INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  completed_at INTEGER
);`;

const CREATE_AGENT_STATES = `
CREATE TABLE IF NOT EXISTS agent_states (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES tasks(id),
  agent_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','running','completed','error')),
  progress INTEGER NOT NULL DEFAULT 0,
  logs TEXT,
  started_at INTEGER,
  completed_at INTEGER
);`;

const CREATE_USER_SETTINGS = `
CREATE TABLE IF NOT EXISTS user_settings (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL UNIQUE REFERENCES users(id),
  zhipu_api_key TEXT,
  zhipu_model TEXT DEFAULT 'glm-4-flash',
  default_format TEXT DEFAULT 'pdf' CHECK(default_format IS NULL OR default_format IN ('pdf','pptx')),
  default_template TEXT DEFAULT 'modern_tech',
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);`;

const CREATE_DESKTOP_USER = `
INSERT OR IGNORE INTO users (id, name, role)
VALUES ('desktop-user', '桌面用户', 'admin');`;

export function runMigrations(db: Database): void {
  db.run(CREATE_USERS);
  db.run(CREATE_CONVERSATIONS);
  db.run(CREATE_MESSAGES);
  db.run(CREATE_TASKS);
  db.run(CREATE_AGENT_STATES);
  db.run(CREATE_USER_SETTINGS);
  db.run(CREATE_DESKTOP_USER);
}
