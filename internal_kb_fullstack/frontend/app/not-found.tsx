import Link from 'next/link'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="max-w-lg p-8 text-center">
        <div className="mb-3 text-sm font-semibold text-blue-600">404</div>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">문서를 찾을 수 없습니다.</h1>
        <p className="mt-3 text-sm leading-7 text-neutral-500">slug가 바뀌었거나 아직 수집되지 않은 문서일 수 있습니다.</p>
        <div className="mt-6 flex justify-center gap-3">
          <Link href="/docs"><Button variant="outline">문서 탐색</Button></Link>
          <Link href="/new"><Button>새 문서 만들기</Button></Link>
        </div>
      </Card>
    </div>
  )
}
