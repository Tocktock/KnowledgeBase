export function normalizeSourceUrl(sourceUrl?: string | null): string | null {
  if (typeof sourceUrl !== 'string') {
    return null
  }
  const normalized = sourceUrl.trim()
  return normalized.length > 0 ? normalized : null
}

export function isExternalSourceUrl(sourceUrl?: string | null): sourceUrl is string {
  const normalized = normalizeSourceUrl(sourceUrl)
  return normalized !== null && normalized.toLowerCase().startsWith('https://')
}

export function getDisplaySourceUrl(sourceUrl?: string | null): string | null {
  return normalizeSourceUrl(sourceUrl)
}

export function getOutboundSourceUrl(sourceUrl?: string | null): string | null {
  const normalized = normalizeSourceUrl(sourceUrl)
  return isExternalSourceUrl(normalized) ? normalized : null
}
