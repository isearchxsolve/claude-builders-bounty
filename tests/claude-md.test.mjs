import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const testDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(testDirectory, "..");
const claudeMdPath = path.join(repositoryRoot, "CLAUDE.md");

async function loadClaudeMd() {
  return readFile(claudeMdPath, "utf8");
}

test("CLAUDE.md exists and declares the intended Next.js SQLite stack", async () => {
  const content = await loadClaudeMd();

  for (const requiredText of [
    "Next.js 15 App Router",
    "React 19",
    "TypeScript 5",
    "SQLite",
    "better-sqlite3",
    "Turso",
    "Node.js: 22 LTS",
    "pnpm 9+",
  ]) {
    assert.match(
      content,
      new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"),
      `Expected CLAUDE.md to document ${requiredText}`,
    );
  }
});

test("CLAUDE.md defines executable development and verification commands", async () => {
  const content = await loadClaudeMd();

  for (const command of [
    "pnpm install",
    "pnpm dev",
    "pnpm lint",
    "pnpm typecheck",
    "pnpm test",
    "pnpm build",
    "pnpm db:migrate",
    "pnpm db:status",
  ]) {
    assert.match(
      content,
      new RegExp(command.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")),
      `Expected CLAUDE.md to contain ${command}`,
    );
  }
});

test("CLAUDE.md defines App Router, server boundary, and component rules", async () => {
  const content = await loadClaudeMd();

  for (const requiredText of [
    "Server Components are the default",
    '"use client"',
    'import "server-only";',
    "Server Action",
    "Route Handlers",
    "revalidatePath",
    "Zod",
  ]) {
    assert.match(
      content,
      new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"),
      `Expected component boundary guidance for ${requiredText}`,
    );
  }
});

test("CLAUDE.md defines SQLite ownership and production safety rules", async () => {
  const content = await loadClaudeMd();

  for (const requiredText of [
    "src/server/db",
    "journal_mode = WAL",
    "foreign_keys = ON",
    "busy_timeout = 5000",
    "parameterized statements",
    "one writer",
    "transaction",
    "repositories own SQL",
  ]) {
    assert.match(
      content,
      new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"),
      `Expected database guidance for ${requiredText}`,
    );
  }
});

test("CLAUDE.md enforces immutable, checksummed SQL migrations", async () => {
  const content = await loadClaudeMd();

  for (const requiredText of [
    "db/migrations",
    "0001_create_users.sql",
    "strictly increasing",
    "immutable",
    "_migrations",
    "checksum",
    "SELECT *",
    "CURRENT_TIMESTAMP",
  ]) {
    assert.match(
      content,
      new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"),
      `Expected migration contract for ${requiredText}`,
    );
  }
});

test("CLAUDE.md explicitly rejects high-risk anti-patterns with reasons", async () => {
  const content = await loadClaudeMd();

  for (const requiredText of [
    "Do not use the Pages Router",
    "Do not put database calls in Client Components",
    "Do not modify an existing migration",
    "Do not fetch internal Route Handlers from Server Components",
    "Do not use `any`",
    "Do not make every component a Client Component",
    "Do not perform side effects during render",
  ]) {
    assert.match(
      content,
      new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"),
      `Expected explicit anti-pattern guidance for ${requiredText}`,
    );
  }
});

test("CLAUDE.md contains a complete greenfield folder contract", async () => {
  const content = await loadClaudeMd();

  for (const requiredPath of [
    "app/",
    "components/",
    "src/server/actions/",
    "src/server/auth/",
    "src/server/db/",
    "db/migrations/",
    "scripts/migrate.ts",
    "tests/",
    ".env.example",
  ]) {
    assert.match(
      content,
      new RegExp(requiredPath.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")),
      `Expected folder structure to include ${requiredPath}`,
    );
  }
});
