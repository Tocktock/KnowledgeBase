export function encodePathSegment(value: string) {
  try {
    // Next route params can arrive already URL-encoded for non-ASCII segments.
    return encodeURIComponent(decodeURIComponent(value))
  } catch {
    return encodeURIComponent(value)
  }
}

export function decodePathSegment(value: string) {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}
