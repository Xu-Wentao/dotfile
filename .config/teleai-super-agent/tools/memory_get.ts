/// <reference path="../env.d.ts" />
import { tool } from "@opencode-ai/plugin"
import DESCRIPTION from "./memory_get.txt"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"

const MEMORY_ROOT =
  process.env.TELEAI_MEMORY_ROOT ||
  path.join(process.env.HOME || os.homedir(), ".local", "share", "teleai-super-agent", "memory")
const DAILY_LOG_DIR = path.join(MEMORY_ROOT, "daily-log")

function resolvePath(file: string): string {
  const name = path.basename(file)
  if (name === "MEMORY.md" || name === "memory.md") return path.join(MEMORY_ROOT, "MEMORY.md")
  if (name === "USER.md" || name === "user.md") return path.join(MEMORY_ROOT, "USER.md")
  return path.join(DAILY_LOG_DIR, name)
}

export default tool({
  description: DESCRIPTION,
  args: {
    file: tool.schema.string().describe("文件名，如 USER.md、MEMORY.md、2026-03-09.md"),
  },
  async execute(args) {
    const { file } = args as { file: string }
    if (!file?.trim()) throw new Error("file 必填")

    const targetPath = resolvePath(file.trim())
    const content = await fs.readFile(targetPath, "utf8").catch((e: any) => {
      if (e?.code === "ENOENT") throw new Error(`文件不存在: ${file}`)
      throw e
    })
    return content
  },
})
