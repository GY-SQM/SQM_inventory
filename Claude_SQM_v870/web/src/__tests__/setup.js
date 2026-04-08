/**
 * Vitest 전역 셋업
 * 모든 테스트 파일 실행 전 자동 적용
 */
import '@testing-library/jest-dom'

// fetch 모킹 (브라우저 환경 시뮬레이션)
global.fetch = vi.fn()

// localStorage 모킹
const localStorageMock = (() => {
  let store = {}
  return {
    getItem:    (k) => store[k] ?? null,
    setItem:    (k, v) => { store[k] = String(v) },
    removeItem: (k) => { delete store[k] },
    clear:      () => { store = {} },
  }
})()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// 각 테스트 후 초기화
afterEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
})
