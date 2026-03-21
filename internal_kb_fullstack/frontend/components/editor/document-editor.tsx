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
import { useRouter } from 'next/navigation'
import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Markdown } from '@tiptap/markdown'
import Link from '@tiptap/extension-link'
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
} from '@/lib/types'
import { slugify } from '@/lib/utils'

type EditorMode = 'visual' | 'source' | 'preview'

async function ingestDocument(payload: IngestDocumentRequest) {
  const response = await fetch('/api/documents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = (await response.json()) as IngestDocumentResponse | { detail?: string }
  if (!response.ok) {
    throw new Error('detail' in data ? data.detail ?? '문서 생성에 실패했습니다.' : '문서 생성에 실패했습니다.')
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
  onClick,
  children,
}: {
  active?: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
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
  const [generatedReferences, setGeneratedReferences] = useState<DefinitionDraftReference[]>([])
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    if (!slug && title) setSlug(slugify(title))
  }, [slug, title])

  const editor = useEditor({
    immediatelyRender: false,
    content: markdown,
    contentType: 'markdown',
    extensions: [
      StarterKit,
      Link.configure({
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
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      router.push(`/docs/${data.document.slug}`)
    },
    onError(err) {
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
      '[[slug]] 또는 [[slug|표시명]] 문법을 그대로 써도 됩니다.',
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

  const insertInternalLink = () => {
    const rawSlug = window.prompt('링크할 문서 slug를 입력하세요', slug || 'example-doc')
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
    createMutation.mutate({
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
      metadata: {
        ui: 'nextjs-notion-wiki-fusion',
      },
    })
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
    generateMutation.mutate({
      topic: definitionTopic.trim(),
      domain: definitionDomain.trim() || undefined,
      doc_type: docType || undefined,
      owner_team: ownerTeam || undefined,
    })
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <form onSubmit={handleSubmit} className="space-y-6">
          <Card className="p-6">
            <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="mb-2 flex items-center gap-2">
                  <Badge>Visual + Wiki Source</Badge>
                  <Badge className="border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-300">Tiptap Markdown</Badge>
                </div>
                <h1 className="text-3xl font-semibold tracking-tight text-neutral-950 dark:text-neutral-50">새 문서 작성</h1>
                <p className="mt-2 text-sm leading-6 text-neutral-500">노션처럼 깔끔하게 쓰고, 위키처럼 서로 연결되는 문서를 만듭니다.</p>
              </div>
              <div className="flex gap-2">
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
                <label className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">문서 제목</label>
                <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="예: 배포 체크리스트" />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">slug</label>
                <Input value={slug} onChange={(event) => setSlug(slugify(event.target.value))} placeholder="예: deployment-checklist" />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">소스 URL</label>
                <Input value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="선택 입력" />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">소유 팀</label>
                <Input value={ownerTeam} onChange={(event) => setOwnerTeam(event.target.value)} placeholder="예: platform" />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">문서 타입</label>
                <Input value={docType} onChange={(event) => setDocType(event.target.value)} placeholder="예: runbook" />
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
                  {value}
                </Button>
              ))}
            </div>
          </Card>

          <Card className="overflow-hidden">
            <div className="flex flex-wrap items-center gap-2 border-b border-neutral-200 bg-neutral-50/80 px-4 py-3 dark:border-neutral-800 dark:bg-neutral-900/70">
              <ToolbarButton onClick={() => editor?.chain().focus().toggleBold().run()} active={editor?.isActive('bold')}>
                <Bold className="size-4" />
              </ToolbarButton>
              <ToolbarButton onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()} active={editor?.isActive('heading', { level: 2 })}>
                <Heading2 className="size-4" />
              </ToolbarButton>
              <ToolbarButton onClick={() => editor?.chain().focus().toggleBulletList().run()} active={editor?.isActive('bulletList')}>
                <List className="size-4" />
              </ToolbarButton>
              <ToolbarButton onClick={() => editor?.chain().focus().toggleOrderedList().run()} active={editor?.isActive('orderedList')}>
                <ListOrdered className="size-4" />
              </ToolbarButton>
              <ToolbarButton onClick={() => editor?.chain().focus().toggleTaskList().run()} active={editor?.isActive('taskList')}>
                <CheckSquare className="size-4" />
              </ToolbarButton>
              <ToolbarButton onClick={() => editor?.chain().focus().toggleBlockquote().run()} active={editor?.isActive('blockquote')}>
                <Quote className="size-4" />
              </ToolbarButton>
              <ToolbarButton onClick={() => editor?.chain().focus().toggleCodeBlock().run()} active={editor?.isActive('codeBlock')}>
                <Code2 className="size-4" />
              </ToolbarButton>
              <ToolbarButton onClick={() => editor?.chain().focus().setHorizontalRule().run()}>
                <Pilcrow className="size-4" />
              </ToolbarButton>
              <ToolbarButton onClick={insertInternalLink}>
                <Link2 className="size-4" />
              </ToolbarButton>
            </div>

            <div className="min-h-[580px] bg-white dark:bg-neutral-950">
              {mode === 'visual' && editor ? (
                <EditorContent editor={editor} className="editor-pane min-h-[580px] px-6 py-5" />
              ) : null}
              {mode === 'source' ? (
                <Textarea
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

          <div className="flex justify-end gap-3">
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
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
              <Sparkles className="size-4 text-blue-500" /> 정의 초안 생성
            </div>
            <div className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">정의할 주제</label>
                <Input value={definitionTopic} onChange={(event) => setDefinitionTopic(event.target.value)} placeholder="예: Transport" />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">도메인 / 맥락</label>
                <Input value={definitionDomain} onChange={(event) => setDefinitionDomain(event.target.value)} placeholder="예: delivery operations" />
              </div>
              <div className="rounded-2xl bg-neutral-50 px-4 py-3 text-xs leading-6 text-neutral-500 dark:bg-neutral-900 dark:text-neutral-400">
                현재 입력한 문서 타입과 소유 팀 값을 검색 필터로 함께 사용합니다. 생성된 내용은 자동 저장되지 않고, 편집기 안에 초안으로만 채워집니다.
              </div>
              <Button type="button" className="w-full" onClick={handleGenerateDefinition} disabled={!definitionTopic.trim() || generateMutation.isPending}>
                {generateMutation.isPending ? <LoaderCircle className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                정의 초안 만들기
              </Button>
              {generatedReferences.length ? (
                <div className="space-y-2">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-neutral-400">References Used</div>
                  {generatedReferences.map((reference) => (
                    <div key={`${reference.document_slug}-${reference.index}`} className="rounded-2xl border border-neutral-200 px-4 py-3 text-sm dark:border-neutral-800">
                      <a href={`/docs/${reference.document_slug}`} className="font-medium text-neutral-900 hover:text-blue-600 dark:text-neutral-50 dark:hover:text-blue-400">
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

          <Card className="p-5">
            <div className="mb-3 text-sm font-semibold text-neutral-900 dark:text-neutral-50">작성 팁</div>
            <div className="space-y-3 text-sm leading-7 text-neutral-600 dark:text-neutral-400">
              {tips.map((tip) => (
                <div key={tip} className="rounded-2xl bg-neutral-50 px-4 py-3 dark:bg-neutral-900">{tip}</div>
              ))}
            </div>
          </Card>

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
                <label className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">제목</label>
                <Input name="title" placeholder="업로드 문서 제목" />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">slug</label>
                <Input name="slug" placeholder="선택 입력" />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">팀</label>
                <Input name="owner_team" defaultValue={ownerTeam} />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300">Markdown / Text / HTML 파일</label>
                <input
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
        </div>
      </div>
    </div>
  )
}
