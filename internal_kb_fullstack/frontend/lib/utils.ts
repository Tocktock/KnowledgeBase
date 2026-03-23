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
  active: '활성',
  paused: '일시중지',
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
  'google-drive': 'Google Drive',
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
  connector_sync: '연결 동기화',
}

const CONNECTOR_STATUS_LABELS: Record<string, string> = {
  active: '정상 연결',
  needs_reauth: '재인증 필요',
  revoked: '권한 해제됨',
  disconnected: '연결 해제됨',
}

const CONNECTOR_SCOPE_LABELS: Record<string, string> = {
  shared: '조직 연결',
  user: '내 연결',
}

const CONNECTOR_TARGET_TYPE_LABELS: Record<string, string> = {
  folder: '폴더',
  shared_drive: '공유 드라이브',
}

const CONNECTOR_SYNC_MODE_LABELS: Record<string, string> = {
  manual: '수동',
  auto: '자동',
}

const CONNECTOR_ITEM_STATUS_LABELS: Record<string, string> = {
  imported: '가져옴',
  unchanged: '변경 없음',
  unsupported: '지원하지 않음',
  failed: '실패',
  deleted: '대상에서 사라짐',
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

export function formatConnectorStatusLabel(value?: string | null) {
  return formatMappedLabel(value, CONNECTOR_STATUS_LABELS)
}

export function formatConnectorScopeLabel(value?: string | null) {
  return formatMappedLabel(value, CONNECTOR_SCOPE_LABELS)
}

export function formatConnectorTargetTypeLabel(value?: string | null) {
  return formatMappedLabel(value, CONNECTOR_TARGET_TYPE_LABELS)
}

export function formatConnectorSyncModeLabel(value?: string | null) {
  return formatMappedLabel(value, CONNECTOR_SYNC_MODE_LABELS)
}

export function formatConnectorItemStatusLabel(value?: string | null) {
  return formatMappedLabel(value, CONNECTOR_ITEM_STATUS_LABELS)
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
  if (value === 'Drive 동기화') return 'Drive 동기화'
  return value
}
