'use client'

import { MoonStar, SunMedium } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => setMounted(true), [])

  const dark = mounted && resolvedTheme === 'dark'

  return (
    <Button
      variant="ghost"
      size="sm"
      aria-label="테마 전환"
      onClick={() => setTheme(dark ? 'light' : 'dark')}
      className="w-9 px-0"
    >
      {dark ? <SunMedium className="size-4" /> : <MoonStar className="size-4" />}
    </Button>
  )
}
