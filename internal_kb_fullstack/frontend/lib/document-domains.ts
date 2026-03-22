export type DocumentDomainKey = 'knowledge' | 'operations-design' | 'data' | 'glossary'

export type DocumentDomainCard = {
  key: DocumentDomainKey
  title: string
  badge: string
  description: string
  href: string
  cta: string
  docsTitle?: string
  docsSubtitle?: string
  docTypes?: string[]
}

export const documentDomains: DocumentDomainCard[] = [
  {
    key: 'knowledge',
    title: '지식 문서',
    badge: '기본 문서',
    description: '팀이 공유하는 설명서, 정책, 배경지식처럼 자주 참고하는 일반 문서를 모아두는 층입니다.',
    href: '/docs?domain=knowledge',
    cta: '문서 탐색 열기',
    docsTitle: '지식 문서',
    docsSubtitle: '설명서, 정책, 배경지식처럼 자주 참고하는 일반 문서를 모아 탐색합니다.',
    docTypes: ['knowledge'],
  },
  {
    key: 'operations-design',
    title: '운영/설계 자료',
    badge: '운영 가이드 · 명세',
    description: '실행 절차와 설계 기준을 함께 다루는 자료입니다. 운영 가이드와 명세를 한곳에서 찾을 수 있습니다.',
    href: '/docs?domain=operations-design',
    cta: '운영/설계 문서 보기',
    docsTitle: '운영/설계 자료',
    docsSubtitle: '운영 가이드와 명세 문서를 함께 모아, 실행 절차와 설계 기준을 한 흐름으로 탐색합니다.',
    docTypes: ['runbook', 'spec'],
  },
  {
    key: 'data',
    title: '데이터 자료',
    badge: '표 · 기준 데이터',
    description: '표나 기준값처럼 참고용 데이터 성격이 강한 문서를 구분해 관리하는 영역입니다.',
    href: '/docs?domain=data',
    cta: '데이터 문서 보기',
    docsTitle: '데이터 자료',
    docsSubtitle: '표, 기준값, 참조용 데이터처럼 구조화된 자료를 중심으로 살펴봅니다.',
    docTypes: ['data'],
  },
  {
    key: 'glossary',
    title: '용어집',
    badge: '대표 개념 문서',
    description: '여러 문서에 흩어진 개념을 근거와 함께 정리한 대표 설명 모음입니다.',
    href: '/glossary',
    cta: '용어집으로 이동',
  },
]

export type DocsDomainPreset = Required<Pick<DocumentDomainCard, 'key' | 'title' | 'docsTitle' | 'docsSubtitle' | 'docTypes'>> & {
  badge: string
}

export function getDocsDomainPreset(domain?: string | string[] | null): DocsDomainPreset | null {
  const key = Array.isArray(domain) ? domain[0] : domain
  if (!key) return null

  const match = documentDomains.find((item) => item.key === key && item.docTypes?.length && item.docsTitle && item.docsSubtitle)
  if (!match || !match.docTypes || !match.docsTitle || !match.docsSubtitle) return null

  return {
    key: match.key,
    title: match.title,
    badge: match.badge,
    docsTitle: match.docsTitle,
    docsSubtitle: match.docsSubtitle,
    docTypes: match.docTypes,
  }
}
