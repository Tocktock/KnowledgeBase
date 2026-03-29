'use client'

import type { ReactNode } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Bold,
  CheckSquare,
  Code2,
  Eye,
  FileUp,
  Heading2,
  Link2,
  List,
  ListOrdered,
  LoaderCircle,
  Pilcrow,
  Quote,
  Sparkles,
} from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Markdown } from '@tiptap/markdown'
import TiptapLink from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'

import { MarkdownRenderer } from '@/components/docs/markdown-renderer'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type {
  DefinitionDraftReference,
  GenerateDefinitionDraftRequest,
  GenerateDefinitionDraftResponse,
  IngestDocumentRequest,
  IngestDocumentResponse,
  SlugConflictDetail,
} from '@/lib/types'
import { formatStatusLabel, slugify } from '@/lib/utils'

type EditorMode = 'visual' | 'source' | 'preview'
type DocumentAuthoringFlow = 'manual' | 'upload' | 'definition'

class SlugConflictError extends Error {
  detail: SlugConflictDetail

  constructor(detail: SlugConflictDetail) {
    super(detail.message)
    this.name = 'SlugConflictError'
    this.detail = detail
  }
}

async function ingestDocument(payload: IngestDocumentRequest) {
  const response = await fetch('/api/documents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = (await response.json()) as IngestDocumentResponse | { detail?: string | SlugConflictDetail }
  if (!response.ok) {
    if ('detail' in data && typeof data.detail === 'object' && data.detail?.code === 'slug_conflict') {
      throw new SlugConflictError(data.detail)
    }
    throw new Error(
      'detail' in data && typeof data.detail === 'string'
        ? data.detail || '문서 생성에 실패했습니다.'
        : '문서 생성에 실패했습니다.',
    )
  }
  return data as IngestDocumentResponse
}

async function uploadDocument(formData: FormData) {
  const response = await fetch('/api/documents/upload', {
    method: 'POST',
    body: formData,
  })
  const data = (await response.json()) as IngestDocumentResponse | { detail?: string }
  if (!response.ok) {
    throw new Error('detail' in data ? data.detail ?? '파일 업로드에 실패했습니다.' : '파일 업로드에 실패했습니다.')
  }
  return data as IngestDocumentResponse
}

async function generateDefinitionDraft(payload: GenerateDefinitionDraftRequest) {
  const response = await fetch('/api/documents/generate-definition', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = (await response.json()) as GenerateDefinitionDraftResponse | { detail?: string }
  if (!response.ok) {
    throw new Error('detail' in data ? data.detail ?? '정의 초안 생성에 실패했습니다.' : '정의 초안 생성에 실패했습니다.')
  }
  return data as GenerateDefinitionDraftResponse
}

function ToolbarButton({
  active,
  label,
  onClick,
  children,
}: {
  active?: boolean
  label: string
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={`inline-flex h-9 w-9 items-center justify-center rounded-xl border transition ${
        active
          ? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300'
          : 'border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-300 dark:hover:bg-neutral-900'
      }`}
    >
      {children}
    </button>
  )
}

export function DocumentEditor() {
  return <DocumentEditorWorkspace flow="manual" />
}

export function DocumentModeChooserPage() {
  const flows: Array<{
    href: string
    title: string
    description: string
    badge: string
  }> = [
    {
      href: '/new/manual',
      title: '직접 작성',
      description: '처음부터 문서를 쓰고 위키 링크와 메타데이터를 함께 정리합니다.',
      badge: 'Manual',
    },
    {
      href: '/new/upload',
      title: '파일에서 시작',
      description: 'Markdown, Text, HTML 파일을 업로드해 문서를 빠르게 저장합니다.',
      badge: 'Upload',
    },
    {
      href: '/new/definition',
      title: '정의 초안 생성',
      description: '기존 근거 문서를 바탕으로 핵심 개념 정의 초안을 만든 뒤 편집합니다.',
      badge: 'Definition',
    },
  ]

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="mb-2 flex items-center gap-2">
          <Badge>Document Authoring</Badge>
          <Badge className="border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-300">Mode chooser</Badge>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">새 문서 추가</h1>
        <p className="mt-2 text-sm leading-7 text-neutral-500">
          이 페이지에서는 작성 방식만 고릅니다. 실제 편집과 업로드, 정의 초안 작업은 각각의 전용 화면에서 진행합니다.
        </p>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        {flows.map((flow) => (
          <Link
            key={flow.href}
            href={flow.href}
            className="rounded-3xl border border-neutral-200 bg-white/80 p-6 transition hover:border-blue-300 hover:bg-blue-50/40 dark:border-neutral-800 dark:bg-neutral-950/70 dark:hover:border-blue-900 dark:hover:bg-blue-950/20"
          >
            <div className="mb-3 flex items-center gap-2">
              <Badge>{flow.badge}</Badge>
            </div>
            <div className="text-lg font-semibold text-neutral-950 dark:text-neutral-50">{flow.title}</div>
            <div className="mt-2 text-sm leading-7 text-neutral-500">{flow.description}</div>
          </Link>
        ))}
      </div>
    </div>
  )
}

export function DocumentEditorWorkspace({
  flow,
}: {
  flow: DocumentAuthoringFlow
}) {
  const router = useRouter()
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<EditorMode>('visual')
  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [ownerTeam, setOwnerTeam] = useState('platform')
  const [docType, setDocType] = useState('knowledge')
  const [status, setStatus] = useState<'draft' | 'published' | 'archived'>('published')
  const [sourceUrl, setSourceUrl] = useState('')
  const [markdown, setMarkdown] = useState('# 새 문서\n\n여기에 내용을 작성하세요.')
  const [definitionTopic, setDefinitionTopic] = useState('')
  const [definitionDomain, setDefinitionDomain] = useState('')
  const [generationSourceSystem, setGenerationSourceSystem] = useState('')
  const [generationOwnerTeam, setGenerationOwnerTeam] = useState('')
  const [generationDocType, setGenerationDocType] = useState('')
  const [generatedReferences, setGeneratedReferences] = useState<DefinitionDraftReference[]>([])
  const [pendingSlugConflict, setPendingSlugConflict] = useState<SlugConflictDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const flowMeta = useMemo(() => {
    if (flow === 'upload') {
      return {
        badge: 'Upload-first',
        title: '파일로 문서 만들기',
        description: '파일 업로드와 업로드 메타데이터만 노출합니다. 직접 작성 편집은 같은 화면 왼쪽 폼에서 이어집니다.',
      }
    }
    if (flow === 'definition') {
      return {
        badge: 'Definition draft',
        title: '정의 초안 만들기',
        description: '근거 문서를 검색해 초안을 채운 뒤 저장 전 마지막 편집을 합니다.',
      }
    }
    return {
      badge: 'Manual authoring',
      title: '새 문서 작성',
      description: '처음부터 문서를 쓰고, 위키처럼 연결되는 수동 문서를 만듭니다.',
    }
  }, [flow])

  useEffect(() => {
    if (!slug && title) setSlug(slugify(title))
  }, [slug, title])

  useEffect(() => {
    setPendingSlugConflict(null)
  }, [slug])

  const editor = useEditor({
    immediatelyRender: false,
    content: markdown,
    contentType: 'markdown',
    extensions: [
      StarterKit.configure({
        link: false,
      }),
      TiptapLink.configure({
        openOnClick: false,
        HTMLAttributes: {
          rel: 'noreferrer',
          target: '_blank',
        },
      }),
      TaskList,
      TaskItem.configure({ nested: true }),
      Placeholder.configure({ placeholder: '팀 문서의 시작 문장을 입력하세요…' }),
      Markdown.configure({ markedOptions: { gfm: true } }),
    ],
    onUpdate({ editor: currentEditor }) {
      setMarkdown(currentEditor.getMarkdown())
    },
  })

  useEffect(() => {
    if (!editor) return
    const currentMarkdown = editor.getMarkdown()
    if (currentMarkdown !== markdown) {
      editor.commands.setContent(markdown, { contentType: 'markdown' })
    }
  }, [editor, markdown])

  const createMutation = useMutation({
    mutationFn: ingestDocument,
    onSuccess(data) {
      setError(null)
      setPendingSlugConflict(null)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      router.push(`/docs/${data.document.slug}`)
    },
    onError(err) {
      if (err instanceof SlugConflictError) {
        setPendingSlugConflict(err.detail)
        setError(null)
        return
      }
      setPendingSlugConflict(null)
      setError(err instanceof Error ? err.message : '문서 생성에 실패했습니다.')
    },
  })

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess(data) {
      router.push(`/docs/${data.document.slug}`)
    },
    onError(err) {
      setError(err instanceof Error ? err.message : '파일 업로드에 실패했습니다.')
    },
  })

  const generateMutation = useMutation({
    mutationFn: generateDefinitionDraft,
    onSuccess(data) {
      setError(null)
      setGeneratedReferences(data.references)
      setTitle((current) => current.trim() || data.title)
      setSlug((current) => current.trim() || data.slug)
      setStatus('draft')
      setMarkdown(data.markdown)
      setMode('visual')
    },
    onError(err) {
      setError(err instanceof Error ? err.message : '정의 초안 생성에 실패했습니다.')
    },
  })

  const submitDisabled = !title.trim() || !slug.trim() || !markdown.trim() || createMutation.isPending
  const tips = useMemo(
    () => [
      '[[문서주소]] 또는 [[문서주소|표시명]] 문법을 그대로 써도 됩니다.',
      '시각 편집 모드와 위키 소스 모드를 즉시 전환할 수 있습니다.',
      '정의 초안 생성은 기존 문서를 검색해 인용과 함께 편집 가능한 Markdown을 채웁니다.',
      '저장하면 백엔드가 바로 청크를 만들고 임베딩 작업을 큐에 넣습니다.',
    ],
    [],
  )

  const syncEditorFromMarkdown = () => {
    if (!editor) return
    editor.commands.setContent(markdown, { contentType: 'markdown' })
  }

  const buildIngestPayload = (allowSlugUpdate: boolean): IngestDocumentRequest => ({
    source_system: 'manual',
    title,
    slug,
    source_url: sourceUrl || undefined,
    content_type: 'markdown',
    content: markdown,
    doc_type: docType,
    language_code: 'ko',
    owner_team: ownerTeam || undefined,
    status,
    priority: 100,
    allow_slug_update: allowSlugUpdate,
    metadata: {
      ui: 'nextjs-notion-wiki-fusion',
    },
  })

  const insertInternalLink = () => {
    const rawSlug = window.prompt('링크할 문서 주소를 입력하세요', slug || 'example-doc')
    if (!rawSlug) return
    const normalized = slugify(rawSlug)
    const label = window.prompt('표시할 텍스트를 입력하세요', normalized) || normalized
    if (mode === 'source') {
      setMarkdown((current) => `${current}\n\n[[${normalized}|${label}]]`)
      return
    }
    editor?.commands.insertContent(`[${label}](/docs/${normalized})`, { contentType: 'markdown' })
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setPendingSlugConflict(null)
    createMutation.mutate(buildIngestPayload(false))
  }

  const handleFileUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    const form = new FormData(event.currentTarget)
    const file = form.get('file')
    if (!(file instanceof File) || file.size === 0) {
      setError('업로드할 파일을 선택하세요.')
      return
    }
    await uploadMutation.mutateAsync(form)
  }

  const handleGenerateDefinition = () => {
    setError(null)
    setGeneratedReferences([])

    const payload: GenerateDefinitionDraftRequest = {
      topic: definitionTopic.trim(),
      domain: definitionDomain.trim() || undefined,
      doc_type: generationDocType.trim() || undefined,
      owner_team: generationOwnerTeam.trim() || undefined,
      source_system: generationSourceSystem.trim() || undefined,
    }

    generateMutation.mutate(payload)
  }

  const handleConfirmSlugUpdate = () => {
    setError(null)
    createMutation.mutate(buildIngestPayload(true))
  }

  const handleCancelSlugUpdate = () => {
    setPendingSlugConflict(null)
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_340px]">
        <form onSubmit={handleSubmit} className="space-y-6">
          <Card className="p-6">
            <div className="mb-5 flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div className="min-w-0">
                <div className="mb-2 flex items-center gap-2">
                  <Badge>Visual + Wiki Source</Badge>
                  <Badge className="border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-300">{flowMeta.badge}</Badge>
                </div>
                <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">{flowMeta.title}</h1>
                <p className="mt-2 text-sm leading-6 text-neutral-500">{flowMeta.description}</p>
                <div className="mt-3 flex flex-wrap gap-2 text-sm">
                  <Link href="/new" className="text-blue-600 hover:text-blue-500 dark:text-blue-400">작성 방식 다시 고르기</Link>
                  {flow !== 'manual' ? <Link href="/new/manual" className="text-blue-600 hover:text-blue-500 dark:text-blue-400">직접 작성</Link> : null}
                  {flow !== 'upload' ? <Link href="/new/upload" className="text-blue-600 hover:text-blue-500 dark:text-blue-400">파일 업로드</Link> : null}
                  {flow !== 'definition' ? <Link href="/new/definition" className="text-blue-600 hover:text-blue-500 dark:text-blue-400">정의 초안</Link> : null}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant={mode === 'visual' ? 'secondary' : 'outline'} onClick={() => { syncEditorFromMarkdown(); setMode('visual') }}>
                  <Sparkles className="size-4" /> 시각 편집
                </Button>
                <Button type="button" variant={mode === 'source' ? 'secondary' : 'outline'} onClick={() => setMode('source')}>
                  <Code2 className="size-4" /> 위키 소스
                </Button>
                <Button type="button" variant={mode === 'preview' ? 'secondary' : 'outline'} onClick={() => setMode('preview')}>
                  <Eye className="size-4" /> 미리보기
                </Button>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label htmlFor="document-title" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">문서 제목</label>
                <Input id="document-title" name="document_title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="예: 배포 체크리스트" />
              </div>
              <div>
                <label htmlFor="document-slug" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">문서 주소</label>
                <Input id="document-slug" name="document_slug" value={slug} onChange={(event) => setSlug(slugify(event.target.value))} placeholder="예: deployment-checklist" />
              </div>
              <div>
                <label htmlFor="document-source-url" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">소스 URL</label>
                <Input id="document-source-url" name="document_source_url" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="선택 입력" />
              </div>
              <div>
                <label htmlFor="document-owner-team" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">소유 그룹</label>
                <Input id="document-owner-team" name="document_owner_team" value={ownerTeam} onChange={(event) => setOwnerTeam(event.target.value)} placeholder="예: platform, product" />
              </div>
              <div>
                <label htmlFor="document-doc-type" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">문서 타입</label>
                <Input id="document-doc-type" name="document_doc_type" value={docType} onChange={(event) => setDocType(event.target.value)} placeholder="예: runbook" />
              </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {(['published', 'draft', 'archived'] as const).map((value) => (
                <Button
                  key={value}
                  type="button"
                  variant={status === value ? 'secondary' : 'outline'}
                  size="sm"
                  onClick={() => setStatus(value)}
                >
                  {formatStatusLabel(value)}
                </Button>
              ))}
            </div>
          </Card>

          <Card className="overflow-hidden">
            <div className="flex flex-wrap items-center gap-2 border-b border-neutral-200 bg-neutral-50/80 px-4 py-3 dark:border-neutral-800 dark:bg-neutral-900/70">
              <ToolbarButton label="굵게" onClick={() => editor?.chain().focus().toggleBold().run()} active={editor?.isActive('bold')}>
                <Bold className="size-4" />
              </ToolbarButton>
              <ToolbarButton label="제목 2" onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()} active={editor?.isActive('heading', { level: 2 })}>
                <Heading2 className="size-4" />
              </ToolbarButton>
              <ToolbarButton label="글머리 목록" onClick={() => editor?.chain().focus().toggleBulletList().run()} active={editor?.isActive('bulletList')}>
                <List className="size-4" />
              </ToolbarButton>
              <ToolbarButton label="번호 목록" onClick={() => editor?.chain().focus().toggleOrderedList().run()} active={editor?.isActive('orderedList')}>
                <ListOrdered className="size-4" />
              </ToolbarButton>
              <ToolbarButton label="체크리스트" onClick={() => editor?.chain().focus().toggleTaskList().run()} active={editor?.isActive('taskList')}>
                <CheckSquare className="size-4" />
              </ToolbarButton>
              <ToolbarButton label="인용문" onClick={() => editor?.chain().focus().toggleBlockquote().run()} active={editor?.isActive('blockquote')}>
                <Quote className="size-4" />
              </ToolbarButton>
              <ToolbarButton label="코드 블록" onClick={() => editor?.chain().focus().toggleCodeBlock().run()} active={editor?.isActive('codeBlock')}>
                <Code2 className="size-4" />
              </ToolbarButton>
              <ToolbarButton label="구분선" onClick={() => editor?.chain().focus().setHorizontalRule().run()}>
                <Pilcrow className="size-4" />
              </ToolbarButton>
              <ToolbarButton label="내부 문서 링크" onClick={insertInternalLink}>
                <Link2 className="size-4" />
              </ToolbarButton>
            </div>

            <div className="min-h-[580px] bg-white dark:bg-neutral-950">
              {mode === 'visual' && editor ? (
                <EditorContent editor={editor} className="editor-pane min-h-[580px] px-6 py-5" />
              ) : null}
              {mode === 'source' ? (
                <Textarea
                  id="document-markdown"
                  name="document_markdown"
                  value={markdown}
                  onChange={(event) => setMarkdown(event.target.value)}
                  className="min-h-[580px] rounded-none border-0 px-6 py-5 font-mono text-[13px] leading-7 shadow-none focus:border-0"
                />
              ) : null}
              {mode === 'preview' ? (
                <div className="min-h-[580px] px-6 py-5">
                  <MarkdownRenderer markdown={markdown} />
                </div>
              ) : null}
            </div>
          </Card>

          {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-950 dark:bg-red-950/30 dark:text-red-300">{error}</div> : null}

          {pendingSlugConflict ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/20 dark:text-amber-200">
              <div className="font-medium">같은 문서 주소의 문서가 이미 있습니다.</div>
              <div className="mt-2 leading-6">
                이 문서를 저장하면 기존 문서에 새 리비전을 추가합니다.
                <div className="mt-2 rounded-xl bg-white/70 px-3 py-3 text-xs leading-6 text-amber-900 dark:bg-neutral-950/40 dark:text-amber-100">
                  <div>제목: {pendingSlugConflict.document.title}</div>
                  <div>문서 주소: {pendingSlugConflict.document.slug}</div>
                  <div>상태: {formatStatusLabel(pendingSlugConflict.document.status)}</div>
                  <div>소유 그룹: {pendingSlugConflict.document.owner_team || '미지정'}</div>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button type="button" onClick={handleConfirmSlugUpdate} disabled={createMutation.isPending}>
                  {createMutation.isPending ? <LoaderCircle className="size-4 animate-spin" /> : null}
                  기존 문서에 새 버전 추가
                </Button>
                <Button type="button" variant="outline" onClick={handleCancelSlugUpdate} disabled={createMutation.isPending}>
                  취소
                </Button>
              </div>
            </div>
          ) : null}

          <div className="flex flex-wrap justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => router.push('/docs')}>
              취소
            </Button>
            <Button type="submit" disabled={submitDisabled}>
              {createMutation.isPending ? <LoaderCircle className="size-4 animate-spin" /> : null}
              문서 저장
            </Button>
          </div>
        </form>

        <div className="space-y-6">
          <Card className="p-5">
            <div className="mb-3 text-sm font-semibold text-neutral-900 dark:text-neutral-50">작성 팁</div>
            <div className="space-y-3 text-sm leading-7 text-neutral-600 dark:text-neutral-400">
              {tips.map((tip) => (
                <div key={tip} className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">{tip}</div>
              ))}
            </div>
          </Card>

          {flow === 'definition' ? (
            <Card className="p-5">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                <Sparkles className="size-4 text-blue-500" /> 정의 초안 생성
              </div>
              <div className="space-y-4">
                <div>
                  <label htmlFor="definition-topic" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">정의할 주제</label>
                  <Input id="definition-topic" name="definition_topic" value={definitionTopic} onChange={(event) => setDefinitionTopic(event.target.value)} placeholder="예: 센디 차량" />
                </div>
                <div>
                  <label htmlFor="definition-domain" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">도메인 / 맥락</label>
                  <Input id="definition-domain" name="definition_domain" value={definitionDomain} onChange={(event) => setDefinitionDomain(event.target.value)} placeholder="예: 배송 운영" />
                </div>
                <div>
                  <label htmlFor="definition-source-system" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">생성 필터: 문서 출처</label>
                  <Input
                    id="definition-source-system"
                    name="definition_source_system"
                    value={generationSourceSystem}
                    onChange={(event) => setGenerationSourceSystem(event.target.value)}
                    placeholder="선택 입력 예: notion-export, manual"
                  />
                </div>
                <div>
                  <label htmlFor="definition-owner-team" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">생성 필터: 소유 그룹</label>
                  <Input
                    id="definition-owner-team"
                    name="definition_owner_team"
                    value={generationOwnerTeam}
                    onChange={(event) => setGenerationOwnerTeam(event.target.value)}
                    placeholder="선택 입력 예: product, logistics"
                  />
                </div>
                <div>
                  <label htmlFor="definition-doc-type" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">생성 필터: 문서 타입</label>
                  <Input id="definition-doc-type" name="definition_doc_type" value={generationDocType} onChange={(event) => setGenerationDocType(event.target.value)} placeholder="선택 입력 예: glossary (용어집)" />
                </div>
                <div className="rounded-2xl bg-neutral-50 px-4 py-3 text-xs leading-6 text-neutral-500 dark:bg-neutral-900 dark:text-neutral-400">
                  생성 필터는 선택 사항이며 저장 메타데이터와 분리되어 있습니다. 비워두면 전체 문서를 대상으로 검색하고, 생성된 내용은 자동 저장되지 않고 편집기 안에 초안으로만 채워집니다.
                </div>
                <Button type="button" className="w-full" onClick={handleGenerateDefinition} disabled={!definitionTopic.trim() || generateMutation.isPending}>
                  {generateMutation.isPending ? <LoaderCircle className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                  정의 초안 만들기
                </Button>
                {generatedReferences.length ? (
                  <div className="space-y-2">
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-neutral-400">참고한 문서</div>
                    {generatedReferences.map((reference) => (
                      <div key={`${reference.document_slug}-${reference.index}`} className="rounded-2xl border border-neutral-200 px-4 py-3 text-sm dark:border-neutral-800">
                        <a href={`/docs/${reference.document_slug}`} className="inline-block break-words font-medium text-neutral-900 hover:text-blue-600 dark:text-neutral-50 dark:hover:text-blue-400">
                          [{reference.index}] {reference.document_title}
                        </a>
                        {reference.section_title ? <div className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{reference.section_title}</div> : null}
                        <div className="mt-2 text-xs leading-6 text-neutral-500 dark:text-neutral-400">{reference.excerpt}</div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </Card>
          ) : null}

          {flow === 'upload' ? (
            <Card className="p-5">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                <FileUp className="size-4 text-blue-500" /> 파일 업로드로 생성
              </div>
              <form onSubmit={handleFileUpload} className="space-y-4">
                <input type="hidden" name="source_system" value="upload" />
                <input type="hidden" name="language_code" value="ko" />
                <input type="hidden" name="doc_type" value="knowledge" />
                <input type="hidden" name="status" value="published" />
                <div>
                  <label htmlFor="upload-title" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">제목</label>
                  <Input id="upload-title" name="title" placeholder="업로드 문서 제목" />
                </div>
                <div>
                  <label htmlFor="upload-slug" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">문서 주소</label>
                  <Input id="upload-slug" name="slug" placeholder="선택 입력" />
                </div>
                <div>
                  <label htmlFor="upload-owner-team" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">소유 그룹</label>
                  <Input id="upload-owner-team" name="owner_team" defaultValue={ownerTeam} />
                </div>
                <div>
                  <label htmlFor="upload-file" className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">Markdown / Text / HTML 파일</label>
                  <input
                    id="upload-file"
                    ref={fileInputRef}
                    name="file"
                    type="file"
                    accept=".md,.markdown,.txt,.html,.htm"
                    className="block w-full rounded-2xl border border-dashed border-neutral-300 px-4 py-8 text-sm text-neutral-500 file:hidden dark:border-neutral-700"
                  />
                </div>
                <Button type="submit" variant="outline" className="w-full" disabled={uploadMutation.isPending}>
                  {uploadMutation.isPending ? <LoaderCircle className="size-4 animate-spin" /> : <FileUp className="size-4" />}
                  파일로 문서 만들기
                </Button>
              </form>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  )
}
