import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import { Inter, Noto_Sans_KR } from 'next/font/google'

import { AppShell } from '@/components/app-shell'
import { Providers } from '@/components/providers'
import { getRecentDocuments } from '@/lib/api/server'
import type { DocumentListItem } from '@/lib/types'

import './globals.css'

export const dynamic = 'force-dynamic'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const notoSansKr = Noto_Sans_KR({ subsets: ['latin'], variable: '--font-noto-kr' })

export const metadata: Metadata = {
  title: 'Internal KB',
  description: 'Notion × NamuWiki inspired internal knowledge base frontend',
}

export default async function RootLayout({ children }: { children: ReactNode }) {
  let recentDocs: DocumentListItem[] = []
  try {
    const data = await getRecentDocuments(12)
    recentDocs = data.items
  } catch {
    recentDocs = []
  }

  return (
    <html lang="ko" suppressHydrationWarning>
      <body className={`${inter.variable} ${notoSansKr.variable} font-sans antialiased`}>
        <Providers>
          <AppShell recentDocs={recentDocs}>{children}</AppShell>
        </Providers>
      </body>
    </html>
  )
}
