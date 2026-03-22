import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

const DOC_TYPE_LABELS: Record<string, string> = {
  knowledge: '지식 문서',
  runbook: '운영 가이드',
  spec: '명세',
  data: '데이터',
  glossary: '용어집',
}

const STATUS_LABELS: Record<string, string> = {
  draft: '초안',
  published: '게시됨',
  archived: '보관됨',
  suggested: '검토 전',
  drafted: '초안 생성됨',
  approved: '승인됨',
  ignored: '제외됨',
  stale: '최신성 낮음',
  queued: '대기 중',
  processing: '처리 중',
  completed: '완료',
  failed: '실패',
  cancelled: '취소됨',
}

const CONCEPT_TYPE_LABELS: Record<string, string> = {
  term: '용어',
  product: '제품',
  process: '프로세스',
  team: '팀',
  metric: '지표',
  entity: '개체',
}

const SOURCE_SYSTEM_LABELS: Record<string, string> = {
  manual: '직접 작성',
  upload: '파일 업로드',
  repo: '저장소',
  notion: '노션',
  'notion-export': '노션 가져오기',
  glossary: '용어집',
}

const RESULT_TYPE_LABELS: Record<string, string> = {
  document: '문서',
  glossary: '용어집',
}

const EVIDENCE_KIND_LABELS: Record<string, string> = {
  canonical: '대표 문서',
  title: '문서 제목',
  heading: '문단 제목',
  'table-field': '표 항목',
  alias: '별칭',
  semantic: '의미 검색',
  'link-neighbor': '연결 문서',
}

const LANGUAGE_LABELS: Record<string, string> = {
  ko: '한국어',
  en: '영어',
}

const JOB_KIND_LABELS: Record<string, string> = {
  embedding: '임베딩',
  refresh: '용어집 새로고침',
  draft: '용어집 초안',
}

function formatMappedLabel(value: string | null | undefined, labels: Record<string, string>) {
  if (!value) return ''
  return labels[value] ?? value
}

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

export function formatDocTypeLabel(value?: string | null) {
  return formatMappedLabel(value, DOC_TYPE_LABELS)
}

export function formatStatusLabel(value?: string | null) {
  return formatMappedLabel(value, STATUS_LABELS)
}

export function formatConceptTypeLabel(value?: string | null) {
  return formatMappedLabel(value, CONCEPT_TYPE_LABELS)
}

export function formatSourceSystemLabel(value?: string | null) {
  return formatMappedLabel(value, SOURCE_SYSTEM_LABELS)
}

export function formatResultTypeLabel(value?: string | null) {
  return formatMappedLabel(value, RESULT_TYPE_LABELS)
}

export function formatEvidenceKindLabel(value?: string | null) {
  return formatMappedLabel(value, EVIDENCE_KIND_LABELS)
}

export function formatLanguageLabel(value?: string | null) {
  return formatMappedLabel(value, LANGUAGE_LABELS)
}

export function formatJobKindLabel(value?: string | null) {
  return formatMappedLabel(value, JOB_KIND_LABELS)
}

export function formatOwnerTeamLabel(value?: string | null) {
  if (!value) return ''
  return `소유 그룹 ${value}`
}

export function formatJobTitle(value?: string | null) {
  if (!value) return ''
  if (value === 'Embedding reindex') return '문서 인덱스 갱신'
  if (value.startsWith('Embedding reindex: ')) return `문서 인덱스 갱신: ${value.slice('Embedding reindex: '.length)}`
  if (value === 'Glossary draft') return '용어집 초안 생성'
  if (value.startsWith('Glossary draft: ')) return `용어집 초안 생성: ${value.slice('Glossary draft: '.length)}`
  if (value === 'Glossary refresh (full)') return '용어집 새로고침 (전체)'
  if (value === 'Glossary refresh (incremental)') return '용어집 새로고침 (변경분)'
  return value
}
