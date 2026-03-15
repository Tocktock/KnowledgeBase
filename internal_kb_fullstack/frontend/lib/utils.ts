import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(value?: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function normalizeSlugSeed(input: string) {
  return input.normalize('NFKC').trim().toLowerCase()
}

export function slugify(input: string) {
  return normalizeSlugSeed(input)
    .replace(/[^\p{L}\p{N}\s_-]/gu, '')
    .replace(/[-\s]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

export function sentence(input?: string | null, limit = 180) {
  if (!input) return ''
  return input.length > limit ? `${input.slice(0, limit).trimEnd()}…` : input
}

export function headingId(text: string) {
  return slugify(text)
}
