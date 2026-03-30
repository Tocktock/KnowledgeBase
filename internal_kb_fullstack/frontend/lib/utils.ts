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
  github: 'GitHub',
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
  validation_run: '용어 검증 실행',
  connector_sync: '연결 동기화',
}

const TRUST_AUTHORITY_LABELS: Record<string, string> = {
  synced_source: '연결된 원본',
  workspace_note: '직접 작성',
  workspace_curated: '워크스페이스 문서',
  approved_concept: '승인된 개념',
  candidate_concept: '검토 중 개념',
  concept_evidence: '개념 근거',
}

const TRUST_FRESHNESS_LABELS: Record<string, string> = {
  fresh: '최신',
  aging: '확인 필요',
  stale: '오래됨',
  unknown: '동기화 정보 없음',
}

const TRUST_SOURCE_LABELS: Record<string, string> = {
  'Google Drive': 'Google Drive',
  GitHub: 'GitHub',
  Notion: 'Notion',
  Repo: '저장소',
  Upload: '업로드 문서',
  Manual: '직접 작성',
  'Workspace note': '워크스페이스 문서',
  'Concept layer': '핵심 개념 레이어',
}

const CONNECTOR_STATUS_LABELS: Record<string, string> = {
  active: '정상 연결',
  needs_reauth: '재인증 필요',
  revoked: '권한 해제됨',
  disconnected: '연결 해제됨',
}

const CONNECTOR_SCOPE_LABELS: Record<string, string> = {
  workspace: '조직 연결',
  personal: '내 연결',
}

const CONNECTOR_PROVIDER_LABELS: Record<string, string> = {
  google_drive: 'Google Drive',
  github: 'GitHub',
  notion: 'Notion',
}

const CONNECTOR_RESOURCE_KIND_LABELS: Record<string, string> = {
  folder: '폴더',
  shared_drive: '공유 드라이브',
  repository_docs: '저장소 문서',
  repository_evidence: '저장소 용어 근거',
  page: '페이지',
  database: '데이터베이스',
  export_upload: 'Notion 내보내기 파일',
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

const CONNECTOR_VISIBILITY_SCOPE_LABELS: Record<string, string> = {
  member_visible: '구성원에게 공개',
  evidence_only: '검증 전용',
}

const VERIFICATION_STATE_LABELS: Record<string, string> = {
  verified: '검증 완료',
  monitoring: '모니터링 중',
  drift_detected: '드리프트 감지',
  evidence_insufficient: '근거 부족',
  archived: '보관됨',
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

export function formatAuthorityKindLabel(value?: string | null) {
  return formatMappedLabel(value, TRUST_AUTHORITY_LABELS)
}

export function formatFreshnessStateLabel(value?: string | null) {
  return formatMappedLabel(value, TRUST_FRESHNESS_LABELS)
}

export function formatTrustSourceLabel(value?: string | null) {
  return formatMappedLabel(value, TRUST_SOURCE_LABELS)
}

export function formatConnectorStatusLabel(value?: string | null) {
  return formatMappedLabel(value, CONNECTOR_STATUS_LABELS)
}

export function formatConnectorScopeLabel(value?: string | null) {
  return formatMappedLabel(value, CONNECTOR_SCOPE_LABELS)
}

export function formatConnectorProviderLabel(value?: string | null) {
  return formatMappedLabel(value, CONNECTOR_PROVIDER_LABELS)
}

export function formatConnectorResourceKindLabel(value?: string | null) {
  return formatMappedLabel(value, CONNECTOR_RESOURCE_KIND_LABELS)
}

export function formatConnectorSyncModeLabel(value?: string | null) {
  return formatMappedLabel(value, CONNECTOR_SYNC_MODE_LABELS)
}

export function formatConnectorItemStatusLabel(value?: string | null) {
  return formatMappedLabel(value, CONNECTOR_ITEM_STATUS_LABELS)
}

export function formatConnectorVisibilityScopeLabel(value?: string | null) {
  return formatMappedLabel(value, CONNECTOR_VISIBILITY_SCOPE_LABELS)
}

export function formatVerificationStateLabel(value?: string | null) {
  return formatMappedLabel(value, VERIFICATION_STATE_LABELS)
}

export function getVerificationStateBadgeClass(value?: string | null) {
  if (value === 'verified') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300'
  }
  if (value === 'monitoring') {
    return 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900 dark:bg-sky-950/30 dark:text-sky-300'
  }
  if (value === 'drift_detected') {
    return 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300'
  }
  if (value === 'archived') {
    return 'border-neutral-200 bg-neutral-100 text-neutral-600 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300'
  }
  return 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-300'
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
  if (value === '리소스 동기화') return '리소스 동기화'
  if (value.startsWith('리소스 동기화: ')) return value
  return value
}
