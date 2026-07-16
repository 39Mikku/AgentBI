import { afterEach, describe, expect, it, vi } from 'vitest'

import type {
  MoegirlArtifactSummary,
  MoegirlFetchResult,
} from '@/api/toolbox-moegirl-types'
import {
  deleteMoegirlArtifact,
  downloadMoegirlArtifact,
  fetchMoegirlPage,
  getMoegirlArtifact,
  listMoegirlArtifacts,
} from '@/api/toolbox-moegirl'
import {
  acceptArchiveResponse,
  applyFetchResult,
  archiveDeleteUnavailable,
  archiveFetchUnavailable,
  beginArchiveRequest,
  removeArtifact,
  selectFallbackArtifact,
} from './moegirl-archive'


const savedArtifact = (id: string): MoegirlArtifactSummary => ({
  id,
  requested_name: `requested-${id}`,
  title: `title-${id}`,
  source_url: `https://mzh.moegirl.org.cn/${id}`,
  fetched_at: `2026-07-15T12:0${id.length}:00+08:00`,
  updated_at: `2026-07-15T12:0${id.length}:00+08:00`,
  character_count: id.length,
  content_sha256: id.repeat(64).slice(0, 64),
})

const savedResult = (id: string): MoegirlFetchResult => ({
  kind: 'saved',
  title: `title-${id}`,
  source_url: `https://mzh.moegirl.org.cn/${id}`,
  markdown: `# title-${id}`,
  message: 'saved',
  artifact: savedArtifact(id),
})

const disambiguationResult = (name: string): MoegirlFetchResult => ({
  kind: 'disambiguation',
  title: name,
  source_url: `https://mzh.moegirl.org.cn/${name}`,
  markdown: `# ${name}`,
  message: 'not saved',
  artifact: null,
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Moegirl archive state', () => {
  it('blocks delete while any state-changing archive request is active', () => {
    const idle = { historyLoading: false, fetching: false, opening: false, deleting: false }

    expect(archiveDeleteUnavailable(idle)).toBe(false)
    expect(archiveDeleteUnavailable({ ...idle, historyLoading: true })).toBe(true)
    expect(archiveDeleteUnavailable({ ...idle, fetching: true })).toBe(true)
    expect(archiveDeleteUnavailable({ ...idle, opening: true })).toBe(true)
    expect(archiveDeleteUnavailable({ ...idle, deleting: true })).toBe(true)
  })

  it('blocks fetch while delete is active', () => {
    expect(archiveFetchUnavailable({ fetching: false, opening: false, deleting: true })).toBe(true)
  })

  it('rejects an in-flight refresh after a delete begins', () => {
    const refreshGeneration = beginArchiveRequest(0)
    const deleteGeneration = beginArchiveRequest(refreshGeneration)

    expect(acceptArchiveResponse(refreshGeneration, deleteGeneration)).toBe(false)
    expect(acceptArchiveResponse(deleteGeneration, deleteGeneration)).toBe(true)
  })

  it('rejects an older history response after a newer fetch begins', () => {
    const historyGeneration = beginArchiveRequest(4)
    const fetchGeneration = beginArchiveRequest(historyGeneration)

    expect(acceptArchiveResponse(historyGeneration, fetchGeneration)).toBe(false)
    expect(acceptArchiveResponse(fetchGeneration, fetchGeneration)).toBe(true)
  })

  it('does not insert a disambiguation preview into saved history', () => {
    const history = [savedArtifact('a')]
    const result = disambiguationResult('芽衣')

    expect(applyFetchResult(history, result)).toEqual(history)
  })

  it('upserts a saved artifact at the front without duplicate ids', () => {
    const previous = [savedArtifact('a'), savedArtifact('b')]
    const next = applyFetchResult(previous, savedResult('b'))

    expect(next.map((item) => item.id)).toEqual(['b', 'a'])
    expect(next[0]?.title).toBe('title-b')
  })

  it('selects the next artifact after deleting the current one', () => {
    const result = removeArtifact(
      [savedArtifact('a'), savedArtifact('b'), savedArtifact('c')],
      'b',
      'b',
    )

    expect(result.history.map((item) => item.id)).toEqual(['a', 'c'])
    expect(result.selectedId).toBe('c')
  })

  it('selects the previous artifact when deleting the last current item', () => {
    const result = removeArtifact(
      [savedArtifact('a'), savedArtifact('b')],
      'b',
      'b',
    )

    expect(result.history.map((item) => item.id)).toEqual(['a'])
    expect(result.selectedId).toBe('a')
  })

  it('keeps the current selection when another artifact is deleted', () => {
    const result = removeArtifact(
      [savedArtifact('a'), savedArtifact('b')],
      'a',
      'b',
    )

    expect(result.history.map((item) => item.id)).toEqual(['a'])
    expect(result.selectedId).toBe('a')
  })

  it('selects the first saved artifact as a deterministic fallback', () => {
    expect(selectFallbackArtifact([savedArtifact('a'), savedArtifact('b')])?.id).toBe('a')
    expect(selectFallbackArtifact([])).toBeNull()
  })
})

describe('Moegirl archive API client', () => {
  it('forwards an AbortSignal for state-changing archive requests', async () => {
    const controller = new AbortController()
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(savedResult('a')), { status: 200 }))
      .mockResolvedValueOnce(new Response('[]', { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...savedArtifact('a'), markdown: '# a' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await fetchMoegirlPage({ user_id: 'alice', name: 'a' }, controller.signal)
    await listMoegirlArtifacts('alice', controller.signal)
    await getMoegirlArtifact('a', 'alice', controller.signal)
    await deleteMoegirlArtifact('a', 'alice', controller.signal)

    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ signal: controller.signal })
    expect(fetchMock.mock.calls[1]?.[1]).toEqual({ signal: controller.signal })
    expect(fetchMock.mock.calls[2]?.[1]).toEqual({ signal: controller.signal })
    expect(fetchMock.mock.calls[3]?.[1]).toEqual({ method: 'DELETE', signal: controller.signal })
  })

  it('posts page names to the Moegirl API base', async () => {
    const result = savedResult('a')
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchMoegirlPage({ user_id: 'alice@example.com', name: '雷电芽衣' }))
      .resolves.toEqual(result)
    expect(fetchMock).toHaveBeenCalledWith('/api/toolbox/moegirl/fetch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: 'alice@example.com', name: '雷电芽衣' }),
    })
  })

  it('encodes artifact ids and user ids for list, get, and delete requests', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response('[]', { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...savedArtifact('a'), markdown: '# a' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await listMoegirlArtifacts('alice+archive@example.com')
    await getMoegirlArtifact('a/b', 'alice+archive@example.com')
    await deleteMoegirlArtifact('a/b', 'alice+archive@example.com')

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      '/api/toolbox/moegirl/artifacts?user_id=alice%2Barchive%40example.com',
      '/api/toolbox/moegirl/artifacts/a%2Fb?user_id=alice%2Barchive%40example.com',
      '/api/toolbox/moegirl/artifacts/a%2Fb?user_id=alice%2Barchive%40example.com',
    ])
    expect(fetchMock.mock.calls[2]?.[1]).toEqual({ method: 'DELETE' })
  })

  it('returns the Markdown Blob with the UTF-8 filename* download name', async () => {
    const body = '# 雷电芽衣'
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, {
      status: 200,
      headers: {
        'Content-Disposition': 'attachment; filename="fallback.md"; filename*=UTF-8\'\'%E9%9B%B7%E7%94%B5%E8%8A%BD%E8%A1%A3.md',
        'Content-Type': 'text/markdown; charset=utf-8',
      },
    })))

    const download = await downloadMoegirlArtifact('artifact-id', 'alice@example.com')

    expect(download.filename).toBe('雷电芽衣.md')
    expect(download.blob).toBeInstanceOf(Blob)
    expect(await download.blob.text()).toBe(body)
  })

  it('surfaces the backend detail message on a failed request', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: '萌娘百科条目不存在' }),
      { status: 404, headers: { 'Content-Type': 'application/json' } },
    )))

    await expect(getMoegirlArtifact('missing', 'alice')).rejects.toThrow('萌娘百科条目不存在')
  })
})
