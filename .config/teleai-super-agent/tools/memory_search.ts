/// <reference path="../env.d.ts" />
import { tool } from "@opencode-ai/plugin"
import DESCRIPTION from "./memory_search.txt"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"

const MEMORY_ROOT =
  process.env.TELEAI_MEMORY_ROOT ||
  path.join(process.env.HOME || os.homedir(), ".local", "share", "teleai-super-agent", "memory")
const MEMORY_DIR = path.join(MEMORY_ROOT, "daily-log")

const DATE_FILE_REGEX = /^\d{4}-\d{2}-\d{2}\.md$/
const REGEX_META_CHARS = /[\\^$.*+?()[\]{}|]/

function isDailyFile(name: string): boolean {
  return DATE_FILE_REGEX.test(name)
}

async function* listDailyFiles(): AsyncGenerator<string> {
  try {
    const names = await fs.readdir(MEMORY_DIR)
    for (const name of names) {
      if (!name.endsWith(".md")) continue
      if (!isDailyFile(name)) continue
      yield path.join(MEMORY_DIR, name)
    }
  } catch (e: any) {
    if (e?.code !== "ENOENT") throw e
  }
}

function shouldUseRegex(query: string): boolean {
  const trimmed = query.trim()
  return trimmed.startsWith("/") || REGEX_META_CHARS.test(trimmed)
}

function compileRegex(query: string): RegExp {
  const trimmed = query.trim()

  // Support `/pattern/flags` and bare `pattern` forms.
  const slashMatch = trimmed.match(/^\/([\s\S]*)\/([gimsuy]*)$/)
  if (slashMatch) {
    const [, pattern, flags] = slashMatch
    const normalizedFlags = flags.replace(/g/g, "")
    return new RegExp(pattern, normalizedFlags.includes("i") ? normalizedFlags : `${normalizedFlags}i`)
  }

  return new RegExp(trimmed, "i")
}

function findMatches(content: string, query: string): Array<{ start: number; end: number; line: number; snippet: string }> {
  const lines = content.split(/\r?\n/)
  const trimmed = query.trim()
  const q = trimmed.toLowerCase()
  const regex = shouldUseRegex(trimmed) ? compileRegex(trimmed) : null
  const results: Array<{ start: number; end: number; line: number; snippet: string }> = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const matched = !trimmed
      ? true
      : regex
        ? regex.test(line)
        : line.toLowerCase().includes(q)

    if (matched) {
      const snippet = line.trim().slice(0, 200)
      if (snippet) results.push({ start: i + 1, end: i + 1, line: i + 1, snippet })
    }
  }

  return results
}

export default tool({
  description: DESCRIPTION,
  args: {
    query: tool.schema.string().describe("搜索关键词、短语，或用于泛化搜索的正则表达式"),
    max_results: tool.schema
      .number()
      .optional()
      .default(15)
      .describe("返回的最大片段数"),
  },
  async execute(args) {
    const { query, max_results = 15 } = args as { query: string; max_results?: number }
    if (!query?.trim()) throw new Error("query 必填")

    try {
      if (shouldUseRegex(query)) compileRegex(query)
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`无效的正则表达式: ${error.message}`)
      }
      throw error
    }

    const collected: Array<{ file: string; line: number; snippet: string }> = []
    // 严格仅遍历按日期命名的每日日志文件（daily-log/YYYY-MM-DD.md）
    for await (const filePath of listDailyFiles()) {
      const content = await fs.readFile(filePath, "utf8").catch(() => "")
      const matches = findMatches(content, query.trim())
      const name = path.basename(filePath)
      for (const m of matches) {
        collected.push({ file: name, line: m.line, snippet: m.snippet })
        if (collected.length >= max_results) break
      }
      if (collected.length >= max_results) break
    }

    if (collected.length === 0) return `未找到与「${query}」相关的记忆片段。`
    return collected
      .slice(0, max_results)
      .map((r) => `[${r.file}:${r.line}] ${r.snippet}`)
      .join("\n")
  },
})
