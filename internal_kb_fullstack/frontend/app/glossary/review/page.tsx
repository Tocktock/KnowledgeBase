import { GlossaryReviewPage } from '@/components/glossary/glossary-review-page'
import { getGlossaryConcepts } from '@/lib/api/server'

export const dynamic = 'force-dynamic'

export default async function GlossaryReviewRoutePage() {
  const initialList = await getGlossaryConcepts({ status: 'suggested', limit: 40 }).catch(() => ({
    items: [],
    total: 0,
    limit: 40,
    offset: 0,
  }))

  return <GlossaryReviewPage initialList={initialList} />
}
