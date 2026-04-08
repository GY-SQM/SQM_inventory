/**
 * 중앙 API 클라이언트 테스트
 * web/src/api/index.js
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { apiGet, apiPost, apiDelete, buildQS } from '../api/index.js'

describe('apiGet', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })

  it('정상 GET 요청 시 JSON 반환', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ success: true, rows: [] }),
    })
    const result = await apiGet('/inventory/list')
    expect(result.success).toBe(true)
    expect(fetch).toHaveBeenCalledWith('/api/inventory/list', { method: 'GET' })
  })

  it('서버 오류 시 ApiError 발생', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ detail: '내부 서버 오류' }),
    })
    await expect(apiGet('/fail')).rejects.toThrow('내부 서버 오류')
  })

  it('네트워크 오류 시 ApiError 발생', async () => {
    fetch.mockRejectedValueOnce(new Error('Network error'))
    await expect(apiGet('/offline')).rejects.toThrow('네트워크 오류')
  })
})

describe('apiPost', () => {
  it('JSON body를 올바르게 전송', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ success: true }),
    })
    await apiPost('/tools/db-optimize', {})
    expect(fetch).toHaveBeenCalledWith(
      '/api/tools/db-optimize',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
    )
  })
})

describe('apiDelete', () => {
  it('DELETE 요청 전송', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ success: true }),
    })
    await apiDelete('/templates/inbound/TPL001')
    expect(fetch).toHaveBeenCalledWith(
      '/api/templates/inbound/TPL001',
      { method: 'DELETE' }
    )
  })
})

describe('buildQS', () => {
  it('빈 객체면 빈 문자열 반환', () => {
    expect(buildQS({})).toBe('')
  })

  it('값이 있는 키만 포함', () => {
    const qs = buildQS({ lot_no: 'L001', status: '', page: 1 })
    expect(qs).toContain('lot_no=L001')
    expect(qs).toContain('page=1')
    expect(qs).not.toContain('status')
  })

  it('null/undefined 제외', () => {
    const qs = buildQS({ a: null, b: undefined, c: 'hello' })
    expect(qs).toBe('?c=hello')
  })
})
