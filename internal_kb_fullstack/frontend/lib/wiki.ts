import { headingId, slugify } from '@/lib/utils'

const WIKI_LINK_RE = /\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|([^\]]+))?\]\]/g
const DOCS_LINK_RE = /\[([^\]]+)\]\(\/docs\/([a-zA-Z0-9\-_/]+)(?:#([^)\s?]+))?(?:\?[^)]*)?\)/g

export function preprocessWikiMarkdown(markdown: string) {
  return markdown.replace(WIKI_LINK_RE, (_match, rawSlug: string, _anchor?: string, label?: string) => {
    const slug = slugify(String(rawSlug).trim())
    const text = label?.trim() || rawSlug.trim()
    return `[${text}](/docs/${slug})`
  })
}

export function extractWikiSlugs(markdown: string) {
  const slugs = new Set<string>()
  for (const match of markdown.matchAll(WIKI_LINK_RE)) {
    slugs.add(slugify(match[1].trim()))
  }
  for (const match of markdown.matchAll(DOCS_LINK_RE)) {
    slugs.add(slugify(match[2].trim()))
  }
  return Array.from(slugs)
}

export function extractHeadings(markdown: string) {
  const headings = markdown
    .split('\n')
    .map((line) => /^(#{1,6})\s+(.+)$/.exec(line)?.[2]?.trim())
    .filter((value): value is string => Boolean(value))

  return headings.map((title) => ({ title, id: headingId(title) }))
}
