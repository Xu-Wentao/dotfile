/// <reference path="../env.d.ts" />
import { tool } from "@opencode-ai/plugin"
import DESCRIPTION from "./image_read.txt"
import { execFileSync } from "child_process"
import fs from "fs"
import os from "os"
import path from "path"
import { postImageRead } from "./auth"

const MAX_IMAGE_BYTES = 5 * 1024 * 1024
const SUPPORTED_IMAGE_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".webp"])

function getLocalImagePathError(filePath: string): string | null {
  const ext = path.extname(filePath).toLowerCase()
  if (!ext) {
    return "输入文件缺少扩展名，请提供 png、jpg、jpeg 或 webp 图片。"
  }

  if (!SUPPORTED_IMAGE_EXTENSIONS.has(ext)) {
    if (ext === ".ppt" || ext === ".pptx") {
      return "当前工具只支持图片识别，不支持 PPT/PPTX 文件，请先将页面导出为图片后重试。"
    }
    return `当前工具只支持 png、jpg、jpeg 或 webp 图片，不支持 ${ext} 文件。`
  }

  return null
}

function formatImageReadError(status: number, statusText: string, responseText: string): string {
  const normalized = `${statusText}\n${responseText}`.toLowerCase()
  const isTooLarge =
    status === 413 ||
    normalized.includes("request entity too large") ||
    normalized.includes("oversizeimage") ||
    normalized.includes("input image") && normalized.includes("exceeds the limit")

  if (isTooLarge) {
    return "输入图像过大，请压缩后重试。"
  }

  return `NewApi error (${status}): ${statusText}\n${responseText}`
}

function fileToDataUrl(filePath: string): string {
  const abs = path.isAbsolute(filePath) ? filePath : path.resolve(process.cwd(), filePath)
  const pathError = getLocalImagePathError(abs)
  if (pathError) {
    throw new Error(pathError)
  }

  const preparedPath = prepareImageForUpload(abs)
  const buf = fs.readFileSync(preparedPath)
  const size = buf.byteLength
  const ext = path.extname(preparedPath).toLowerCase()

  const mime =
    ext === ".png"
      ? "image/png"
      : ext === ".jpg" || ext === ".jpeg"
        ? "image/jpeg"
        : "application/octet-stream"

  console.error("[image_read] upload file  =", preparedPath)
  console.error("[image_read] upload bytes =", size)

  return `data:${mime};base64,${buf.toString("base64")}`
}

function isHttpImageUrl(value: string): boolean {
  return /^https?:\/\//i.test(value)
}

function isDataImageUrl(value: string): boolean {
  return /^data:image\/[a-z0-9.+-]+;base64,/i.test(value)
}

function isFileImageUrl(value: string): boolean {
  return /^file:\/\//i.test(value)
}

function normalizeFileUrlToPath(value: string): string | null {
  try {
    const parsed = new URL(value)
    if (parsed.protocol !== "file:") return null

    let localPath = decodeURIComponent(parsed.pathname)
    if (process.platform === "win32" && /^\/[A-Za-z]:/.test(localPath)) {
      localPath = localPath.slice(1)
    }

    if (parsed.host) {
      if (process.platform === "win32") {
        return `\\\\${parsed.host}${localPath.replace(/\//g, "\\")}`
      }
      return `//${parsed.host}${localPath}`
    }

    return process.platform === "win32" ? localPath.replace(/\//g, "\\") : localPath
  } catch {
    return null
  }
}

function tryResolveLocalImagePath(value: string): string | null {
  if (!value) return null

  const trimmed = value.trim()
  if (!trimmed || isHttpImageUrl(trimmed) || isDataImageUrl(trimmed)) {
    return null
  }

  if (isFileImageUrl(trimmed)) {
    const normalizedFileUrlPath = normalizeFileUrlToPath(trimmed)
    if (!normalizedFileUrlPath) return null
    return fs.existsSync(normalizedFileUrlPath) ? normalizedFileUrlPath : null
  }

  const candidate = path.isAbsolute(trimmed) ? trimmed : path.resolve(process.cwd(), trimmed)
  return fs.existsSync(candidate) ? candidate : null
}

function resolveImageInput(imageUrl: string | undefined, filePath: string | undefined): string {
  if (filePath) {
    return fileToDataUrl(filePath)
  }

  if (!imageUrl) {
    throw new Error("image_url or file_path is required")
  }

  const localPath = tryResolveLocalImagePath(imageUrl)
  if (localPath) {
    console.error("[image_read] local image_url =", imageUrl)
    console.error("[image_read] resolved path   =", localPath)
    return fileToDataUrl(localPath)
  }

  if (isHttpImageUrl(imageUrl) || isDataImageUrl(imageUrl)) {
    return imageUrl
  }

  throw new Error("image_url must be an http/https URL, a data:image base64 URL, or a valid local image path")
}

function prepareImageForUpload(filePath: string): string {
  const pathError = getLocalImagePathError(filePath)
  if (pathError) {
    throw new Error(pathError)
  }

  const stat = fs.statSync(filePath)
  if (stat.size <= MAX_IMAGE_BYTES) {
    return filePath
  }

  if (process.platform !== "win32") {
    throw new Error(
      `Local image is ${stat.size} bytes, exceeds ${MAX_IMAGE_BYTES} bytes, and auto compression is currently only supported on Windows`
    )
  }

  return compressImageOnWindows(filePath, MAX_IMAGE_BYTES)
}

function compressImageOnWindows(filePath: string, maxBytes: number): string {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "image-read-"))
  const outputPath = path.join(tempDir, `${path.parse(filePath).name}-compressed.jpg`)
  const scriptPath = path.join(tempDir, "compress-image.ps1")
  const powershell = process.env.SystemRoot
    ? path.join(process.env.SystemRoot, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    : "powershell.exe"

  const script = `
param(
  [string]$InputPath,
  [string]$OutputPath,
  [int]$TargetBytes
)

Add-Type -AssemblyName System.Drawing

function Save-JpegCandidate {
  param(
    [System.Drawing.Image]$Source,
    [string]$Destination,
    [double]$Scale,
    [long]$Quality
  )

  $width = [Math]::Max([int][Math]::Round($Source.Width * $Scale), 1)
  $height = [Math]::Max([int][Math]::Round($Source.Height * $Scale), 1)
  $bitmap = New-Object System.Drawing.Bitmap $width, $height
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  try {
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $graphics.DrawImage($Source, 0, 0, $width, $height)

    $encoder = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
    if (-not $encoder) {
      throw 'JPEG encoder not found'
    }

    $encoderParams = New-Object System.Drawing.Imaging.EncoderParameters 1
    $encoderParams.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality), $Quality
    $bitmap.Save($Destination, $encoder, $encoderParams)
  } finally {
    $graphics.Dispose()
    $bitmap.Dispose()
  }
}

$qualities = @(90, 82, 74, 66, 58, 50, 42, 36, 30, 24, 18, 12)
$scales = @(1.0, 0.9, 0.82, 0.74, 0.66, 0.58, 0.5, 0.42, 0.34, 0.26)

$source = [System.Drawing.Image]::FromFile($InputPath)
try {
  foreach ($scale in $scales) {
    foreach ($quality in $qualities) {
      Save-JpegCandidate -Source $source -Destination $OutputPath -Scale $scale -Quality $quality
      $size = (Get-Item $OutputPath).Length
      if ($size -le $TargetBytes) {
        Write-Output $OutputPath
        exit 0
      }
    }
  }
} finally {
  $source.Dispose()
}

throw "Failed to compress image below $TargetBytes bytes"
`
  fs.writeFileSync(scriptPath, script, "utf8")

  try {
    execFileSync(
      powershell,
      [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        scriptPath,
        "-InputPath",
        filePath,
        "-OutputPath",
        outputPath,
        "-TargetBytes",
        String(maxBytes),
      ],
      { stdio: "pipe" }
    )
  } catch (error) {
    const message =
      error instanceof Error && "stderr" in error
        ? String((error as { stderr?: Buffer | string }).stderr ?? error.message)
        : String(error)
    throw new Error(`Failed to compress oversized image on Windows: ${message}`)
  }

  const compressedStat = fs.statSync(outputPath)
  console.error("[image_read] compressed from =", fs.statSync(filePath).size)
  console.error("[image_read] compressed to   =", compressedStat.size)
  if (compressedStat.size > maxBytes) {
    throw new Error(
      `Compressed image is still ${compressedStat.size} bytes, exceeds ${maxBytes} bytes`
    )
  }

  return outputPath
}

export default tool({
  description: DESCRIPTION,

  args: {
    prompt: tool.schema.string().describe("给模型的提示词/问题（必填）"),
    image_url: tool.schema.string().optional().describe("图片 URL（http/https 或 data url）"),
    file_path: tool.schema.string().optional().describe("本地图片路径（png/jpg）"),
    model: tool.schema.string().optional().describe("可选：模型名；不传则默认 doubao-seed-2-0-pro-260215"),
  },

  async execute(args) {
    try {
      const { prompt, image_url, file_path, model } = args as {
        prompt: string
        image_url?: string
        file_path?: string
        model?: string
      }

      if (!prompt) throw new Error("prompt is required")
      if (!image_url && !file_path) throw new Error("image_url or file_path is required")

      const MODEL = model ?? "doubao-seed-2-0-pro-260215"

      // image_url 支持 http/https、data:image base64，或本地路径（自动转 data url）
      const img = resolveImageInput(image_url, file_path)

      // OpenAI 兼容 /chat/completions 多模态格式（关键：image_url: { url }）
      const payload: any = {
        model: MODEL,
        messages: [
          {
            role: "user",
            content: [
              { type: "text", text: prompt },
              { type: "image_url", image_url: { url: img } },
            ],
          },
        ],
        temperature: 0.2,
      }

      const resp = await postImageRead(payload)

      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(formatImageReadError(resp.status, resp.statusText, text))
      }

      const json: any = await resp.json()

      const content = json?.choices?.[0]?.message?.content
      if (typeof content === "string") return content

      return JSON.stringify(json, null, 2)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      if (message === "prompt is required") {
        throw new Error("缺少 prompt 参数，请描述你希望识别图片中的什么内容。")
      }
      if (message === "image_url or file_path is required") {
        throw new Error("缺少图片输入，请提供 image_url 或 file_path。")
      }
      if (message === "image_url must be an http/https URL, a data:image base64 URL, or a valid local image path") {
        throw new Error("image_url 仅支持 http/https、data:image base64，或可访问的本地图片路径。")
      }
      if (message.includes("Local image is") && message.includes("auto compression is currently only supported on Windows")) {
        throw new Error("当前仅 Windows 支持超大本地图片自动压缩，请先手动压缩图片后重试。")
      }
      if (message.includes("Failed to compress oversized image on Windows")) {
        throw new Error("图片压缩失败，请先手动压缩图片后重试。")
      }
      if (message.includes("Compressed image is still") && message.includes("exceeds")) {
        throw new Error("输入图像过大，请进一步压缩后重试。")
      }
      throw error
    }
  },
})
