/// <reference path="../env.d.ts" />
import { tool } from "@opencode-ai/plugin"
import DESCRIPTION from "./arxiv_search.txt"

interface ArxivPaper {
  id: string
  title: string
  authors: string[]
  summary: string
  published: string
  url: string
  pdf_url?: string
}

interface ArxivSearchResult {
  total_results: number
  papers: ArxivPaper[]
}

export default tool({
  description: DESCRIPTION,
  args: {
    query: tool.schema.string().describe("搜索查询内容，支持关键词、作者、标题等"),
    max_results: tool.schema
      .number()
      .optional()
      .default(10)
      .describe("返回结果数量，默认 10，最多 50"),
  },
  async execute(args) {
    const { query, max_results = 10 } = args
    const limit = Math.min(Math.max(max_results, 1), 50)

    try {
      // 使用 arxiv 公开 API
      const apiUrl = new URL("http://export.arxiv.org/api/query")
      apiUrl.searchParams.append("search_query", `all:${query}`)
      apiUrl.searchParams.append("start", "0")
      apiUrl.searchParams.append("max_results", limit.toString())
      apiUrl.searchParams.append("sortBy", "submittedDate")
      apiUrl.searchParams.append("sortOrder", "descending")

      // 带重试机制的请求
      const xmlText = await fetchWithRetry(apiUrl.toString())
      const papers = parseArxivXml(xmlText)

      if (papers.length === 0) {
        return `未找到相关论文。请尝试:\n1. 使用英文关键词搜索\n2. 检查拼写\n3. 尝试更通用的搜索词\n\n搜索查询: ${query}`
      }

      // 格式化结果
      const formattedResults = papers
        .map(
          (paper, index) =>
            `${index + 1}. ${paper.title}\n` +
            `   作者: ${paper.authors.join(", ")}\n` +
            `   发布时间: ${paper.published}\n` +
            `   摘要: ${paper.summary}\n` +
            `   链接: ${paper.url}` +
            (paper.pdf_url ? `\n   PDF: ${paper.pdf_url}` : ""),
        )
        .join("\n\n")

      return `找到 ${papers.length} 篇论文:\n\n${formattedResults}`
    } catch (error) {
      if (error instanceof Error) {
        throw error
      }
      throw new Error("搜索过程中发生未知错误")
    }
  },
})

// 带重试机制的 fetch（仅限流时重试）
async function fetchWithRetry(url: string, maxRetries = 3): Promise<string> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    const response = await fetch(url, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      },
    })

    // 成功直接返回
    if (response.ok) {
      return await response.text()
    }

    // 限流则等待重试
    if (response.status === 429 && attempt < maxRetries) {
      const waitTime = Math.pow(2, attempt) * 1000 // 1s, 2s, 4s
      await new Promise((resolve) => setTimeout(resolve, waitTime))
      continue
    }

    // 其他错误直接抛出
    throw new Error(`Arxiv API 错误 (${response.status}): ${response.statusText}`)
  }

  throw new Error("超过最大重试次数")
}

// 解析 arxiv API XML 响应
function parseArxivXml(xml: string): ArxivPaper[] {
  const papers: ArxivPaper[] = []

  // 简单的 XML 解析，提取每个 entry
  const entryRegex = /<entry>([\s\S]*?)<\/entry>/g
  const matches = xml.matchAll(entryRegex)

  for (const match of matches) {
    try {
      const entryXml = match[1]

      // 提取标题
      const titleMatch = entryXml.match(/<title>([\s\S]*?)<\/title>/)
      const title = titleMatch
        ? titleMatch[1]
            .replace(/\s+/g, " ")
            .trim()
        : "未知标题"

      // 提取摘要
      const summaryMatch = entryXml.match(/<summary>([\s\S]*?)<\/summary>/)
      const summary = summaryMatch
        ? summaryMatch[1]
            .replace(/\s+/g, " ")
            .replace(/&lt;/g, "<")
            .replace(/&gt;/g, ">")
            .replace(/&quot;/g, '"')
            .replace(/&amp;/g, "&")
            .trim()
        : "无摘要"

      // 提取作者
      const authors: string[] = []
      const authorRegex = /<name>([^<]+)<\/name>/g
      const authorMatches = entryXml.matchAll(authorRegex)
      for (const authorMatch of authorMatches) {
        authors.push(authorMatch[1].trim())
      }

      // 提取 ID
      const idMatch = entryXml.match(/<id>([^<]+)<\/id>/)
      const arxivId = idMatch ? extractArxivId(idMatch[1]) : ""
      const url = idMatch ? idMatch[1] : ""
      const pdfUrl = arxivId ? `https://arxiv.org/pdf/${arxivId}.pdf` : ""

      // 提取发布日期
      const publishedMatch = entryXml.match(/<published>([^<]+)<\/published>/)
      const published = publishedMatch
        ? formatDate(publishedMatch[1])
        : "未知日期"

      if (arxivId) {
        papers.push({
          id: arxivId,
          title,
          authors: authors.length > 0 ? authors : ["未知作者"],
          summary,
          published,
          url,
          pdf_url: pdfUrl,
        })
      }
    } catch (error) {
      console.error("解析论文信息时出错:", error)
    }
  }

  return papers
}

// 从 arxiv URL 中提取论文 ID
function extractArxivId(url: string): string {
  const match = url.match(/(\d+\.\d+)/)
  return match ? match[1] : ""
}

// 格式化日期
function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "long",
      day: "numeric",
    })
  } catch {
    return dateStr
  }
}
