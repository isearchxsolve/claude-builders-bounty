# CLAUDE.md — Next.js 15 + SQLite SaaS

## Mission

Build a secure, boring, maintainable SaaS using Next.js App Router and SQLite.
Prefer explicit code over abstractions, local ownership over hidden magic, and
small vertical slices over broad rewrites.

This document is the project contract. Follow it unless the user explicitly
requests an exception.

## Stack and versions

- Node.js: 22 LTS
- Package manager: pnpm 9+
- Framework: Next.js 15 App Router
- UI: React 19, TypeScript 5 with `strict: true`
- Styling: Tailwind CSS
- Validation: Zod
- Database: SQLite
- Default SQLite driver: `better-sqlite3`
- Optional hosted SQLite: Turso/libSQL, implemented only behind the database
  adapter boundary described below
- Tests: Node test runner or Vitest; Playwright only for critical browser flows

Use pnpm. Do not introduce npm, yarn, Bun, a second lockfile, or a second ORM.
One package manager and one dependency graph makes CI and production reproducible.

## Commands

Run these before presenting work as complete:

