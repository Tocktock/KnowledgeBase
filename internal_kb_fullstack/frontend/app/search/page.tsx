import { SemanticSearchPage } from '@/components/search/semantic-search-page'

export default function SearchPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">시맨틱 검색</h1>
        <p className="mt-2 text-sm leading-7 text-neutral-500">벡터 검색과 키워드 검색을 함께 사용해 관련 문서를 더 잘 찾습니다.</p>
      </div>
      <SemanticSearchPage />
    </div>
  )
}
