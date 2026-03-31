const INTERNAL_ORIGIN = 'http://knowledgehub.local'
const CONTROL_CHAR_RE = /[\u0000-\u001f\u007f]/

function normalizeFallbackPath(fallback: string) {
  const candidate = fallback.trim()
  if (candidate && candidate.startsWith('/') && !candidate.startsWith('//')) {
    return candidate
  }
  return '/'
}

export function coerceInternalPath(value: string | null | undefined, fallback = '/') {
  const safeFallback = normalizeFallbackPath(fallback)
  if (typeof value !== 'string') return safeFallback

  const candidate = value.trim()
  if (!candidate || candidate.includes('\\') || CONTROL_CHAR_RE.test(candidate)) {
    return safeFallback
  }
  if (!candidate.startsWith('/') || candidate.startsWith('//')) {
    return safeFallback
  }

  try {
    const parsed = new URL(candidate, INTERNAL_ORIGIN)
    if (parsed.origin !== INTERNAL_ORIGIN) {
      return safeFallback
    }
    if (!parsed.pathname || !parsed.pathname.startsWith('/') || parsed.pathname.startsWith('//')) {
      return safeFallback
    }
    return `${parsed.pathname}${parsed.search}${parsed.hash}`
  } catch {
    return safeFallback
  }
}
