/// <reference path="../env.d.ts" />
import { tool } from "@opencode-ai/plugin"
import DESCRIPTION from "./baidu_search.txt"
import { postBaiduSearch } from "./auth"

interface SearchFilterRange {
  gte?: string
  gt?: string
  lte?: string
  lt?: string
}

interface SearchFilterMatchImage {
  size?: number // 0-全部, 4-小图, 5-中图, 6-大图, 7-超大图
  ratio?: number // 0-全部, 1-细长竖图, 2-竖图, 3-方图, 4-横图, 5-细长横图
  format?: number // 0-全部, 2-BMP, 3-JPG, 4-PNG, 5-JPEG, 6-GIF
}

interface SearchFilterMatch {
  site?: string[] // 指定站点列表
  image?: SearchFilterMatchImage
}

interface SearchFilter {
  match?: SearchFilterMatch
  range?: {
    page_time?: SearchFilterRange
  }
}

interface BaiduSearchRequest {
  messages: Array<{ role: string; content: string }>
  edition?: string
  search_source?: string
  search_recency_filter?: string
  resource_type_filter?: Array<{ type: string; top_k: number }>
  search_filter?: SearchFilter
  block_websites?: string[]
  safe_search?: boolean
}

interface BaiduSearchResponse {
  code: number
  message: string
  data?: {
    references?: Array<{
      id?: number
      title?: string
      url?: string
      website?: string
      web_anchor?: string
      content?: string
      type?: string
      date?: string
      rerank_score?: number
      authority_score?: number
      image?: { url?: string; height?: string; width?: string }
      video?: { url?: string; height?: string; width?: string; duration?: string }
    }>
  }
}

export default tool({
  description: DESCRIPTION,
  args: {
    query: tool.schema.string().describe("搜索查询内容"),
    edition: tool.schema
      .enum(["standard", "lite"])
      .optional()
      .describe("搜索版本，默认为 standard"),
    search_recency_filter: tool.schema
      .enum(["week", "month", "semiyear", "year"])
      .optional()
      .describe("时间过滤器（周/月/半年/年）"),
    resource_type_filter: tool.schema
      .array(
        tool.schema.object({
          type: tool.schema.enum(["web", "video", "image", "aladdin"]),
          top_k: tool.schema.number().int().min(0).max(50),
        })
      )
      .optional()
      .describe("资源类型和 top_k 限制"),
    block_websites: tool.schema
      .array(tool.schema.string())
      .optional()
      .describe("要屏蔽的网站列表，例如 [\"tieba.baidu.com\"]"),
    timeoutMs: tool.schema
      .number()
      .int()
      .min(1000)
      .max(60000)
      .optional()
      .describe("请求超时时间（毫秒），默认 15000"),
  },
  async execute(args) {
    // 构建请求体
    const body: BaiduSearchRequest = {
      messages: [{ role: "user", content: args.query }],
      edition: args.edition ?? "standard",
      search_source: "baidu_search_v2",
      search_recency_filter: args.search_recency_filter,
      resource_type_filter: args.resource_type_filter,
      //search_filter: args.search_filter, //先不要这个参数，参数封装过于复杂，暂时还没有这个必要
      block_websites: args.block_websites,
      safe_search: true,
    }

    // 移除 undefined 字段
    for (const key of Object.keys(body)) {
      if (body[key as keyof BaiduSearchRequest] === undefined) {
        delete body[key as keyof BaiduSearchRequest]
      }
    }

    // 设置超时
    const controller = new AbortController()
    const timeoutMs = args.timeoutMs ?? 15000
    const timeout = setTimeout(() => controller.abort(), timeoutMs)

    try {
      const response = await postBaiduSearch(body as unknown as Record<string, unknown>, controller.signal)

      const text = await response.text()
      const data: BaiduSearchResponse = text ? JSON.parse(text) : {}

      if (!response.ok) {
        const message = data?.message || response.statusText || "请求失败"
        throw new Error(`搜索错误 (${response.status}): ${message}`)
      }

      // 检查业务错误
      if (data.code !== 0) {
        throw new Error(`搜索错误: ${data.message || "未知错误"}`)
      }

      const references = data?.data?.references || []

      if (references.length === 0) {
        return `搜索: 未找到结果。`
      }

      // 格式化搜索结果
      const lines: string[] = []

      lines.push("搜索结果")
      lines.push(`查询: ${args.query}`)
      if (args.search_recency_filter) {
        lines.push(`时间范围: ${args.search_recency_filter}`)
      }
      if (args.block_websites?.length) {
        lines.push(`屏蔽网站: ${args.block_websites.join(", ")}`)
      }
      lines.push(`结果 (${references.length} 条):`)

      references.forEach((ref, index) => {
        const title = ref.title || ref.web_anchor || ref.website || ref.url || "无标题"
        const type = ref.type || "未知"
        const site = ref.website ? ` | 来源: ${ref.website}` : ""
        const date = ref.date ? ` | 日期: ${ref.date}` : ""

        lines.push(`${index + 1}. ${title}`)
        lines.push(`   链接: ${ref.url || "N/A"}`)
        lines.push(`   类型: ${type}${site}${date}`)

        if (typeof ref.rerank_score === "number") {
          lines.push(`   重排得分: ${ref.rerank_score.toFixed(3)}`)
        }
        if (typeof ref.authority_score === "number") {
          lines.push(`   权威得分: ${ref.authority_score.toFixed(3)}`)
        }
        if (ref.content) {
          const snippet = ref.content.length > 200
            ? ref.content.slice(0, 200) + "…"
            : ref.content
          lines.push(`   摘要: ${snippet}`)
        }

        if (type === "image" && ref.image?.url) {
          lines.push(
            `   图片: ${ref.image.url} (${ref.image.width || "?"}x${ref.image.height || "?"})`
          )
        }
        if (type === "video" && ref.video?.url) {
          lines.push(
            `   视频: ${ref.video.url} (${ref.video.width || "?"}x${ref.video.height || "?"}, ${ref.video.duration || "?"}秒)`
          )
        }
      })

      return lines.join("\n")
    } catch (err) {
      if (err instanceof Error) {
        throw err
      }
      throw new Error("搜索过程中发生未知错误")
    } finally {
      clearTimeout(timeout)
    }
  },
})
