import fs from "node:fs"
import path from "node:path"
type WatermarkMode = "explicit" | "hidden" | "both"

type WatermarkRuntime = {
  addWatermark: (inputPath: string, outputPath: string, mode: WatermarkMode) => Promise<void>
}

const PLUGIN_DIR = __dirname
const RUNTIME_MODULE_PATH = path.join(PLUGIN_DIR, "watermark-runtime", "index.cjs")
const RUNTIME_IMAGE_FONT_PATH = path.join(PLUGIN_DIR, "watermark-runtime", "wqy-microhei.ttc")
const BUNDLED_PDF_FONT_PATH = path.join(PLUGIN_DIR, "watermark-runtime", "NotoSerifSC-VF.ttf")
const RUNTIME_PDF_FONT_PATH = fs.existsSync(BUNDLED_PDF_FONT_PATH)
  ? BUNDLED_PDF_FONT_PATH
  : fs.existsSync("C:\\Windows\\Fonts\\NotoSerifSC-VF.ttf")
    ? "C:\\Windows\\Fonts\\NotoSerifSC-VF.ttf"
    : path.join(PLUGIN_DIR, "watermark-runtime", "NotoSansSC-VF.ttf")

const USER_HOME = process.env.USERPROFILE || process.env.HOME || ""
const TELEAI_DATA_ROOT = path.join(USER_HOME, ".local", "share", "teleai-super-agent")
const OPENCODE_BASE_DIR = path.join(TELEAI_DATA_ROOT, "opencode")
const LEGACY_OPENCODE_BASE_DIR = path.join(USER_HOME, ".config", "opencode")
const LOG_DIR = path.join(OPENCODE_BASE_DIR, "logs")
const TMP_DIR = path.join(OPENCODE_BASE_DIR, "tmp")
const LOG_FILE = path.join(LOG_DIR, "watermark-plugin.log")

const USER_AGENT_CONFIG_PATH = path.join(TELEAI_DATA_ROOT, "user-agent-config.json")
const LEGACY_USER_AGENT_CONFIG_PATH = path.join(OPENCODE_BASE_DIR, "user-agent-config.json")
const VERY_LEGACY_USER_AGENT_CONFIG_PATH = path.join(LEGACY_OPENCODE_BASE_DIR, "user-agent-config.json")

const WRITE_LIKE_TOOLS = new Set(["write", "edit", "multiedit", "bash", "powershell"])

const SUPPORTED_EXTS = new Set([
  ".txt",
  ".md",
  ".markdown",
  ".mdown",
  ".mkd",
  ".mkdown",
  ".pdf",
  ".docx",
  ".pptx",
  ".xlsx",
  ".jpg",
  ".jpeg",
  ".png",
])

const SKIP_EXTS = new Set([
  ".mp4", ".avi", ".mov", ".mkv",
  ".mp3", ".wav", ".aac", ".flac",
  ".py", ".js", ".go", ".sh", ".json", ".xml", ".html",
  ".doc", ".ppt", ".xls", ".csv",
])

const RECENT_PROCESSED = new Map<string, number>()
const DEDUP_MS = 5000
let runtimeModule: WatermarkRuntime | null = null
const FILE_READY_TIMEOUT_MS = 15000
const FILE_READY_POLL_MS = 400
const RUNTIME_TIMEOUT_MS = 30000
const PPTX_START_DELAY_MS = 8000
const RECENT_FALLBACK_WINDOW_MS = 8000
const RECENT_FALLBACK_MAX_DEPTH = 1
const RECENT_FALLBACK_MAX_FILES = 3
const RECENT_FALLBACK_BURST_MS = 2500
type ShellCommandIntent = "read" | "write" | "unknown"

const POWERSHELL_WRITE_PATTERNS = [
  /\bset-content\b/i,
  /\badd-content\b/i,
  /\bout-file\b/i,
  /\bnew-item\b/i,
  /\bcopy-item\b/i,
  /\bmove-item\b/i,
  /\brename-item\b/i,
  /\bexport-[a-z0-9_-]+\b/i,
  /\bset-itemproperty\b/i,
  /\bclear-content\b/i,
  /\bremove-item\b/i,
  /\bni\b/i,
  /\bsc\b/i,
  /\bac\b/i,
  /\boc\b/i,
  /\bto_excel\b/i,
  /\bto_csv\b/i,
  /\bworkbook\.save\b/i,
  /\bwb\.save\b/i,
  /\bsaveas\b/i,
  /\bsave\(/i,
  /\b>\b/,
  /\b>>\b/,
]

const POWERSHELL_READ_PATTERNS = [
  /\bget-content\b/i,
  /\bimport-excel\b/i,
  /\bselect-string\b/i,
  /\bget-item\b/i,
  /\bget-childitem\b/i,
  /\bdir\b/i,
  /\bls\b/i,
  /\btype\b/i,
  /\bcat\b/i,
  /\bread_excel\b/i,
  /\bload_workbook\b/i,
  /\bread_csv\b/i,
  /\bread_text\b/i,
  /\bread_bytes\b/i,
  /\bopen\s*\(/i,
]

const BASH_WRITE_PATTERNS = [
  /\bcp\b/,
  /\bmv\b/,
  /\btouch\b/,
  /\btee\b/,
  /\binstall\b/,
  /\bmkdir\b/,
  /\bcat\s+.+>/i,
  /\becho\s+.+>/i,
  /\bprintf\s+.+>/i,
  /\bpython\b.*\b(save|write|export|dump)\b/i,
  /\bnode\b.*\b(save|write|export)\b/i,
  /\bto_excel\b/i,
  /\bto_csv\b/i,
  /\bworkbook\.save\b/i,
  /\bwb\.save\b/i,
  /\bsaveas\b/i,
  /\bsave\(/i,
  /\b>\b/,
  /\b>>\b/,
]

const BASH_READ_PATTERNS = [
  /\bcat\b/,
  /\bhead\b/,
  /\btail\b/,
  /\bless\b/,
  /\bmore\b/,
  /\bgrep\b/,
  /\bsed\b/,
  /\bawk\b/,
  /\bpython\b.*\b(read|load|parse|inspect|extract)\b/i,
  /\bnode\b.*\b(read|load|parse|inspect|extract)\b/i,
  /\bread_excel\b/i,
  /\bload_workbook\b/i,
]

function ensureDirs() {
  fs.mkdirSync(LOG_DIR, { recursive: true })
  fs.mkdirSync(TMP_DIR, { recursive: true })
}

function log(message: string) {
  ensureDirs()
  fs.appendFileSync(LOG_FILE, `${new Date().toISOString()} ${message}\n`, "utf-8")
}

function normalizeFilePath(filePath: string): string {
  return path.normalize(String(filePath).trim().replace(/^[\"']|[\"']$/g, ""))
}

function getBaseDirs(input: any, output: any): string[] {
  const candidates = [
    input?.args?.cwd,
    output?.metadata?.cwd,
    process.cwd(),
    USER_HOME ? path.join(USER_HOME, "Desktop") : "",
  ].filter(Boolean)

  return [...new Set(candidates.map((p: string) => normalizeFilePath(p)).filter((p) => fs.existsSync(p)))]
}

function getPreferredWorkingDir(input: any, output: any): string | undefined {
  const candidates = [
    input?.args?.cwd,
    output?.metadata?.cwd,
    process.cwd(),
  ].filter(Boolean)

  for (const candidate of candidates) {
    const normalized = normalizeFilePath(candidate)
    try {
      if (fs.existsSync(normalized) && fs.statSync(normalized).isDirectory()) {
        return normalized
      }
    } catch {}
  }

  return undefined
}

function getFileExt(filePath: string): string {
  return path.extname(filePath).toLowerCase()
}

function isExcludedWatermarkFile(filePath: string): boolean {
  const baseName = path.basename(filePath).toUpperCase()
  if (baseName === 'SKILL.MD') return true

  const segments = normalizeFilePath(filePath).split(/[\\/]+/)
  return segments.includes(".temp") || segments.includes(".watermark_tmp")
}

function isSupportedFile(filePath: string): boolean {
  if (isExcludedWatermarkFile(filePath)) return false
  const ext = getFileExt(filePath)
  if (SKIP_EXTS.has(ext)) return false
  return SUPPORTED_EXTS.has(ext)
}

function existsAndIsFile(filePath: string): boolean {
  try {
    return fs.existsSync(filePath) && fs.statSync(filePath).isFile()
  } catch {
    return false
  }
}

function shouldSkipByDedup(filePath: string): boolean {
  const now = Date.now()
  const last = RECENT_PROCESSED.get(filePath)
  if (last && now - last < DEDUP_MS) {
    return true
  }
  RECENT_PROCESSED.set(filePath, now)
  return false
}

function getExplicitExemptFromUserAgentConfig(): boolean | undefined {
  try {
    const configPathCandidates = [
      USER_AGENT_CONFIG_PATH,
      LEGACY_USER_AGENT_CONFIG_PATH,
      VERY_LEGACY_USER_AGENT_CONFIG_PATH,
    ]

    const resolvedPath = configPathCandidates.find((p) => fs.existsSync(p))
    if (!resolvedPath) {
      log(`[CONFIG] user-agent-config not found in candidates: ${configPathCandidates.join(", ")}`)
      return undefined
    }

    const raw = fs.readFileSync(resolvedPath, "utf-8")
    const parsed = JSON.parse(raw)
    const value = parsed?.features?.watermark?.aiWatermarkEnabled

    if (typeof value === "boolean") {
      log(`[CONFIG] aiWatermarkEnabled found in user-agent-config (${resolvedPath}): ${value}`)
      return !value
    }

    log(`[CONFIG] aiWatermarkEnabled missing or invalid in user-agent-config (${resolvedPath})`)
    return undefined
  } catch (error: any) {
    log(`[CONFIG] failed to read user-agent-config: ${error?.message || String(error)}`)
    return undefined
  }
}

function getExplicitExempt(input: any, output: any): boolean {
  const configValue = getExplicitExemptFromUserAgentConfig()
  if (typeof configValue === "boolean") {
    return configValue
  }

  const raw =
    input?.args?.explicitExempt ??
    input?.args?.explicit_exempt ??
    output?.metadata?.explicitExempt ??
    process.env.AIGC_EXPLICIT_EXEMPT ??
    "false"

  const fallback = String(raw).toLowerCase() === "true"
  log(`[CONFIG] fallback explicitExempt used: ${fallback}`)
  return fallback
}

function getStructuredFilePaths(input: any, output: any): string[] {
  const candidates = [
    input?.args?.filePath,
    input?.args?.path,
    output?.metadata?.filepath,
    output?.metadata?.filePath,
  ].filter(Boolean)

  return [...new Set(candidates.map((p: string) => normalizeFilePath(p)))]
}

function resolveCandidatePath(rawPath: string, baseDirs: string[]): string[] {
  const normalized = normalizeFilePath(rawPath)
  if (!normalized) return []

  if (path.isAbsolute(normalized)) {
    return [normalized]
  }

  const resolved = baseDirs.map((baseDir) => normalizeFilePath(path.join(baseDir, normalized)))
  return [...new Set(resolved)]
}

function extractPathsFromText(text: string, baseDirs: string[]): string[] {
  if (!text) return []

  const results = new Set<string>()
  const extPattern = "txt|md|markdown|mdown|mkd|mkdown|pdf|docx|pptx|xlsx|jpg|jpeg|png"

  const windowsPathRegex = new RegExp(
    `[A-Za-z]:\\\\(?:[^\\\\/:*?\\\"<>|\\r\\n]+\\\\)*[^\\\\/:*?\\\"<>|\\r\\n]+\\.(${extPattern})`,
    "gi"
  )

  const unixAbsPathRegex = new RegExp(
    `/(?:[^/\\s"'<>|]+/)*[^/\\s"'<>|]+\\.(${extPattern})`,
    "gi"
  )

  const relativePathRegex = new RegExp(
    `(?:\\./|\\.\\./)(?:[^/\\s"'<>|]+/)*[^/\\s"'<>|]+\\.(${extPattern})`,
    "gi"
  )

  const quotedPathRegex = new RegExp(
    `["']([^"']+\\.(${extPattern}))["']`,
    "gi"
  )

  const bareFilenameRegex = new RegExp(
    `(?:^|[\\s=:(])([^\\\\/:"'<>|\\r\\n]+\\.(${extPattern}))(?=$|[\\s),;])`,
    "gi"
  )

  let match: RegExpExecArray | null

  while ((match = windowsPathRegex.exec(text)) !== null) {
    results.add(normalizeFilePath(match[0]))
  }

  while ((match = unixAbsPathRegex.exec(text)) !== null) {
    results.add(normalizeFilePath(match[0]))
  }

  while ((match = relativePathRegex.exec(text)) !== null) {
    results.add(normalizeFilePath(match[0]))
  }

  while ((match = quotedPathRegex.exec(text)) !== null) {
    for (const candidate of resolveCandidatePath(match[1], baseDirs)) {
      results.add(candidate)
    }
  }

  while ((match = bareFilenameRegex.exec(text)) !== null) {
    for (const candidate of resolveCandidatePath(match[1], baseDirs)) {
      results.add(candidate)
    }
  }

  return [...results]
}

function getCommandToolFilePaths(input: any, output: any): string[] {
  const command = String(input?.args?.command || "")
  const stdout = String(output?.metadata?.output || output?.output || "")
  const baseDirs = getBaseDirs(input, output)

  const paths = [
    ...extractPathsFromText(command, baseDirs),
    ...extractPathsFromText(stdout, baseDirs),
  ]

  return [...new Set(paths)].filter((p) => existsAndIsFile(p) && isSupportedFile(p))
}

function matchesAnyPattern(text: string, patterns: RegExp[]): boolean {
  return patterns.some((pattern) => pattern.test(text))
}

function classifyShellCommandIntent(tool: string, input: any, output: any): ShellCommandIntent {
  const command = String(input?.args?.command || "")
  const stdout = String(output?.metadata?.output || output?.output || "")
  const combined = `${command}\n${stdout}`

  if (!combined.trim()) {
    return "unknown"
  }

  if (tool === "powershell") {
    const isWrite = matchesAnyPattern(combined, POWERSHELL_WRITE_PATTERNS)
    const isRead = matchesAnyPattern(combined, POWERSHELL_READ_PATTERNS)

    // Prefer write classification for hybrid "read then save" spreadsheet/document scripts.
    if (isWrite && !isRead) return "write"
    if (isRead && !isWrite) return "read"
    if (isWrite) return "write"
    return "unknown"
  }

  if (tool === "bash") {
    const isWrite = matchesAnyPattern(combined, BASH_WRITE_PATTERNS)
    const isRead = matchesAnyPattern(combined, BASH_READ_PATTERNS)

    // Prefer write classification for hybrid "read then save" spreadsheet/document scripts.
    if (isWrite && !isRead) return "write"
    if (isRead && !isWrite) return "read"
    if (isWrite) return "write"
  }

  return "unknown"
}

function findRecentlyModifiedSupportedFiles(baseDirs: string[], withinMs = 15000, maxDepth = 2): string[] {
  const now = Date.now()
  const recent: string[] = []

  function walk(dir: string, depth: number) {
    try {
      const entries = fs.readdirSync(dir, { withFileTypes: true })
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name)
        if (entry.isDirectory()) {
          if (depth < maxDepth) {
            walk(fullPath, depth + 1)
          }
          continue
        }
        if (!entry.isFile()) continue
        if (!isSupportedFile(fullPath)) continue
        const stat = fs.statSync(fullPath)
        if (now - stat.mtimeMs <= withinMs) {
          recent.push(fullPath)
        }
      }
    } catch {}
  }

  for (const baseDir of baseDirs) {
    walk(baseDir, 0)
  }

  return [...new Set(recent)]
}

function sortPathsByMtimeDesc(paths: string[]): string[] {
  return [...new Set(paths)].sort((a, b) => {
    try {
      return fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs
    } catch {
      return 0
    }
  })
}

function getFileStem(filePath: string): string {
  return path.parse(filePath).name.toLowerCase()
}

function uniqueExistingSupportedPaths(paths: string[]): string[] {
  return [...new Set(paths.map((p) => normalizeFilePath(p)))]
    .filter((p) => existsAndIsFile(p) && isSupportedFile(p))
}

function getBurstRecentFallbackPaths(input: any, output: any): string[] {
  const cwd = getPreferredWorkingDir(input, output)
  if (!cwd) return []

  const recent = sortPathsByMtimeDesc(
    findRecentlyModifiedSupportedFiles([cwd], RECENT_FALLBACK_WINDOW_MS, RECENT_FALLBACK_MAX_DEPTH)
  )
  if (!recent.length) return []

  const newest = recent[0]
  let newestMtime = 0
  try {
    newestMtime = fs.statSync(newest).mtimeMs
  } catch {
    return [newest]
  }

  const burst = recent.filter((candidate) => {
    try {
      return newestMtime - fs.statSync(candidate).mtimeMs <= RECENT_FALLBACK_BURST_MS
    } catch {
      return false
    }
  })

  if (burst.length > 1 && burst.length <= RECENT_FALLBACK_MAX_FILES) {
    return burst
  }

  const sameStemRecent = recent.filter((candidate) => getFileStem(candidate) === getFileStem(newest))
  if (sameStemRecent.length > 1 && sameStemRecent.length <= RECENT_FALLBACK_MAX_FILES) {
    return sameStemRecent
  }

  if (burst.length > RECENT_FALLBACK_MAX_FILES) {
    const sameStemBurst = burst.filter((candidate) => getFileStem(candidate) === getFileStem(newest))
    if (sameStemBurst.length > 0 && sameStemBurst.length <= RECENT_FALLBACK_MAX_FILES) {
      return sameStemBurst
    }
  }

  return [newest]
}

function getWatermarkMode(explicitExempt: boolean): WatermarkMode {
  return explicitExempt ? "hidden" : "both"
}

function getStartDelayMs(filePath: string): number {
  const ext = getFileExt(filePath)
  if (ext === ".pptx") {
    return PPTX_START_DELAY_MS
  }
  return 0
}

function createTempOutputPath(inputFile: string): string {
  const parsed = path.parse(inputFile)
  const tmpRootDir = path.join(parsed.dir, ".watermark_tmp")
  const taskDirName = `${parsed.name}_${Date.now()}_${process.pid}_${Math.random().toString(16).slice(2, 8)}`
  const taskDir = path.join(tmpRootDir, taskDirName)
  fs.mkdirSync(taskDir, { recursive: true })
  return path.join(taskDir, `${parsed.name}_watermarked${parsed.ext}`)
}

function cleanupTempArtifacts(tempOutputPath: string) {
  try {
    if (fs.existsSync(tempOutputPath)) {
      fs.unlinkSync(tempOutputPath)
    }
  } catch {}

  try {
    const taskDir = path.dirname(tempOutputPath)
    if (fs.existsSync(taskDir) && fs.readdirSync(taskDir).length === 0) {
      fs.rmdirSync(taskDir)
    }
  } catch {}

  try {
    const taskDir = path.dirname(tempOutputPath)
    const tmpRootDir = path.dirname(taskDir)
    if (path.basename(tmpRootDir) === ".watermark_tmp" && fs.existsSync(tmpRootDir) && fs.readdirSync(tmpRootDir).length === 0) {
      fs.rmdirSync(tmpRootDir)
    }
  } catch {}
}

function getRuntime(): WatermarkRuntime {
  if (!runtimeModule) {
    runtimeModule = require(RUNTIME_MODULE_PATH) as WatermarkRuntime
  }
  return runtimeModule
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function waitForFileReady(filePath: string, timeoutMs = FILE_READY_TIMEOUT_MS): Promise<void> {
  const start = Date.now()
  let lastSize = -1
  let lastMtime = -1
  let stableCount = 0

  while (Date.now() - start < timeoutMs) {
    try {
      if (!fs.existsSync(filePath)) {
        await sleep(FILE_READY_POLL_MS)
        continue
      }

      const stat = fs.statSync(filePath)
      const currentSize = stat.size
      const currentMtime = stat.mtimeMs

      // Treat the file as ready only after both size and mtime stop changing across polls.
      if (currentSize > 0 && currentSize === lastSize && currentMtime === lastMtime) {
        stableCount += 1
      } else {
        stableCount = 0
        lastSize = currentSize
        lastMtime = currentMtime
      }

      if (stableCount >= 2) {
        return
      }
    } catch {}

    await sleep(FILE_READY_POLL_MS)
  }

  throw new Error(`file not ready within timeout: ${filePath}`)
}

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number, label: string): Promise<T> {
  let timer: NodeJS.Timeout | undefined
  try {
    return await Promise.race([
      promise,
      new Promise<T>((_, reject) => {
        timer = setTimeout(() => reject(new Error(`${label} timed out after ${timeoutMs}ms`)), timeoutMs)
      }),
    ])
  } finally {
    if (timer) {
      clearTimeout(timer)
    }
  }
}

function startWatermarkTask(filePath: string, explicitExempt: boolean) {
  const delayMs = getStartDelayMs(filePath)
  const runner = () => {
    void addWatermark(filePath, explicitExempt).catch((error: any) => {
      log(`[AFTER] async watermark task error: ${filePath} | ${error?.stack || error?.message || String(error)}`)
    })
  }

  if (delayMs > 0) {
    log(`[AFTER] watermark task scheduled with delay=${delayMs}ms: ${filePath}`)
    setTimeout(runner, delayMs)
    return
  }

  runner()
}

function startWatermarkTasks(filePaths: string[], explicitExempt: boolean, reason: string) {
  const uniquePaths = sortPathsByMtimeDesc(uniqueExistingSupportedPaths(filePaths))
  if (!uniquePaths.length) {
    return
  }

  log(`[AFTER] ${reason}: ${uniquePaths.join(", ")}`)
  for (const filePath of uniquePaths) {
    startWatermarkTask(filePath, explicitExempt)
  }
}

async function addWatermark(filePath: string, explicitExempt: boolean) {
  const normalized = normalizeFilePath(filePath)

  if (!isSupportedFile(normalized)) {
    log(`[AFTER] skip unsupported file: ${normalized}`)
    return
  }

  if (!existsAndIsFile(normalized)) {
    log(`[AFTER] file not found or not file: ${normalized}`)
    return
  }

  if (shouldSkipByDedup(normalized)) {
    log(`[AFTER] skip duplicate watermark in short window: ${normalized}`)
    return
  }

  if (!fs.existsSync(RUNTIME_MODULE_PATH)) {
    log(`[AFTER] watermark runtime not found: ${RUNTIME_MODULE_PATH}`)
    return
  }

  const watermarkMode = getWatermarkMode(explicitExempt)
  const tempOutputPath = createTempOutputPath(normalized)
  const backupPath = `${normalized}.bak`

  log(`[AFTER] watermark runtime path: ${RUNTIME_MODULE_PATH}`)
  log(`[AFTER] watermark start: ${normalized}, explicitExempt=${explicitExempt}, watermarkMode=${watermarkMode}`)

  try {
    log(`[AFTER] waitForFileReady begin: ${normalized}`)
    await waitForFileReady(normalized)
    log(`[AFTER] waitForFileReady done: ${normalized}`)

    if (fs.existsSync(RUNTIME_IMAGE_FONT_PATH)) {
      process.env.TELEWAX_FONT_PATH = process.env.TELEWAX_FONT_PATH || RUNTIME_IMAGE_FONT_PATH
    }
    if (fs.existsSync(RUNTIME_PDF_FONT_PATH)) {
      process.env.TELEWAX_PDF_FONT_PATH = process.env.TELEWAX_PDF_FONT_PATH || RUNTIME_PDF_FONT_PATH
    }
    log(`[AFTER] getRuntime begin: ${normalized}`)
    const runtime = getRuntime()
    log(`[AFTER] getRuntime done: ${normalized}`)

    if (path.basename(normalized).toUpperCase() === "SKILL.MD") {
      log(`[AFTER] skip watermark for skill file: ${normalized}`)
      return
    }

    log(`[AFTER] runtime.addWatermark begin: ${normalized}`)
    await withTimeout(runtime.addWatermark(normalized, tempOutputPath, watermarkMode), RUNTIME_TIMEOUT_MS, `watermark runtime for ${normalized}`)
    log(`[AFTER] runtime.addWatermark done: ${normalized}`)

    if (!fs.existsSync(tempOutputPath)) {
      throw new Error(`runtime output not found: ${tempOutputPath}`)
    }

    log(`[AFTER] replace original begin: ${normalized}`)
    fs.copyFileSync(normalized, backupPath)
    fs.renameSync(tempOutputPath, normalized)
    if (fs.existsSync(backupPath)) {
      fs.unlinkSync(backupPath)
    }
    cleanupTempArtifacts(tempOutputPath)
    log(`[AFTER] replace original done: ${normalized}`)
    log(`[AFTER] watermark done: ${normalized}`)
  } catch (error: any) {
    try {
      if (fs.existsSync(backupPath)) {
        fs.renameSync(backupPath, normalized)
      }
    } catch {}
    cleanupTempArtifacts(tempOutputPath)
    log(`[AFTER] watermark error: ${normalized} | ${error?.stack || error?.message || String(error)}`)
  }
}

export default async function () {
  ensureDirs()

  log("plugin loaded")
  log(`plugin dir: ${PLUGIN_DIR}`)
  log(`process.cwd: ${process.cwd()}`)
  log(`process.execPath: ${process.execPath}`)
  log(`watermark runtime expected at: ${RUNTIME_MODULE_PATH}`)
  log(`user-agent-config expected at: ${USER_AGENT_CONFIG_PATH}`)

  return {
    "tool.execute.after": async (input: any, output: any) => {
      try {
        const tool = String(input?.tool || "").toLowerCase()

        if (!WRITE_LIKE_TOOLS.has(tool)) {
          return
        }

        log(`[AFTER] tool.execute.after triggered, tool=${tool}`)

        const explicitExempt = getExplicitExempt(input, output)
        log(`[AFTER] final explicitExempt = ${explicitExempt}`)

        const structuredPaths = uniqueExistingSupportedPaths(getStructuredFilePaths(input, output))
        if (structuredPaths.length > 0) {
          startWatermarkTasks(structuredPaths, explicitExempt, `structured file(s) detected: tool=${tool}`)
          return
        }

        if (tool === "bash" || tool === "powershell") {
          const shellIntent = classifyShellCommandIntent(tool, input, output)
          log(`[AFTER] ${tool} intent classified as: ${shellIntent}`)

          if (shellIntent === "read") {
            log(`[AFTER] ${tool} treated as read-only, skip watermark`)
            return
          }

          const commandToolPaths = uniqueExistingSupportedPaths(getCommandToolFilePaths(input, output))
          if (commandToolPaths.length > 0 && shellIntent === "write") {
            startWatermarkTasks(commandToolPaths, explicitExempt, `${tool} file(s) detected from command/output`)
            return
          }

          const burstFallbackPaths = getBurstRecentFallbackPaths(input, output)
          if (burstFallbackPaths.length > 0 && shellIntent === "write") {
            startWatermarkTasks(
              burstFallbackPaths,
              explicitExempt,
              `${tool} recent fallback file(s) detected in cwd burst window`
            )
            return
          }

          log(`[AFTER] ${tool} detected but no writable file path found`)
          return
        }

        const recentPaths = getBurstRecentFallbackPaths(input, output)
        if (recentPaths.length > 0) {
          startWatermarkTasks(recentPaths, explicitExempt, `recent fallback file(s) detected: tool=${tool}`)
        }
      } catch (e: any) {
        log(`[AFTER] hook error: ${e?.stack || e?.message || String(e)}`)
      }
    },
  }
}


