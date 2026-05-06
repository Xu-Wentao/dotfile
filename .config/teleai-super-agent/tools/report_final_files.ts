/// <reference path="../env.d.ts" />
import { tool } from "@opencode-ai/plugin"
import DESCRIPTION from "./report_final_files.txt"
import fs from "node:fs/promises"
import path from "node:path"

type FinalFileStatus =
  | "ok"
  | "path_not_absolute"
  | "not_found"
  | "not_a_file"
  | "stat_error"

type FinalFileReportItem = {
  inputPath: string
  resolvedPath: string
  absolute: boolean
  normalizedFromRelative: boolean
  exists: boolean
  kind: "file" | "directory" | "missing" | "unknown"
  sizeBytes: number | null
  displayable: boolean
  reason: FinalFileStatus
}

export default tool({
  description: DESCRIPTION,
  args: {
    files: tool
      .schema
      .array(tool.schema.string())
      .describe("最终交付文件的绝对路径列表"),
  },
  async execute(args) {
    const { files } = args as { files: string[] }
    if (!files || files.length === 0) throw new Error("至少需要提供一个文件路径")

    const items: FinalFileReportItem[] = []
    for (const filePath of files) {
      const normalizedFromRelative = !path.isAbsolute(filePath)
      const resolvedPath = normalizedFromRelative ? path.resolve(filePath) : filePath

      try {
        const stat = await fs.stat(resolvedPath)
        const isFile = stat.isFile()
        items.push({
          inputPath: filePath,
          resolvedPath,
          absolute: true,
          normalizedFromRelative,
          exists: true,
          kind: isFile ? "file" : "directory",
          sizeBytes: isFile ? stat.size : null,
          displayable: isFile,
          reason: isFile ? "ok" : "not_a_file",
        })
      } catch (error: any) {
        const reason: FinalFileStatus = error?.code === "ENOENT"
          ? (normalizedFromRelative ? "path_not_absolute" : "not_found")
          : "stat_error"
        items.push({
          inputPath: filePath,
          resolvedPath,
          absolute: true,
          normalizedFromRelative,
          exists: false,
          kind: "missing",
          sizeBytes: null,
          displayable: false,
          reason,
        })
      }
    }

    return JSON.stringify(
      {
        items,
        summary: {
          total: items.length,
          displayable: items.filter((item) => item.displayable).length,
          invalid: items.filter((item) => !item.displayable).length,
        },
      },
      null,
      2,
    )
  },
})
