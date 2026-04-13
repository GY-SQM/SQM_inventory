/**
 * DevPage (개발자 모드) 테스트
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import DevPage from '../pages/DevPage.jsx'

describe('DevPage', () => {
  const defaultProps = {
    devMode:           false,
    toggleDevMode:     vi.fn(),
    fontScale:         1.0,
    increaseFontScale: vi.fn(),
    decreaseFontScale: vi.fn(),
    resetFontScale:    vi.fn(),
  }

  it('페이지 제목 렌더링', () => {
    render(<DevPage {...defaultProps} />)
    expect(screen.getByText(/개발자 모드/)).toBeTruthy()
  })

  it('devMode OFF 상태 표시', () => {
    render(<DevPage {...defaultProps} devMode={false} />)
    expect(screen.getByText('OFF')).toBeTruthy()
  })

  it('devMode ON 상태 표시', () => {
    render(<DevPage {...defaultProps} devMode={true} />)
    expect(screen.getByText('ON')).toBeTruthy()
  })

  it('글꼴 크기 100% 표시', () => {
    render(<DevPage {...defaultProps} fontScale={1.0} />)
    expect(screen.getByText('100%')).toBeTruthy()
  })

  it('A+ 버튼 클릭 시 increaseFontScale 호출', () => {
    const increase = vi.fn()
    render(<DevPage {...defaultProps} increaseFontScale={increase} />)
    fireEvent.click(screen.getByText('A+'))
    expect(increase).toHaveBeenCalledOnce()
  })

  it('A- 버튼 클릭 시 decreaseFontScale 호출', () => {
    const decrease = vi.fn()
    render(<DevPage {...defaultProps} decreaseFontScale={decrease} />)
    fireEvent.click(screen.getByText('A-'))
    expect(decrease).toHaveBeenCalledOnce()
  })

  it('환경 정보 섹션 표시', () => {
    render(<DevPage {...defaultProps} />)
    expect(screen.getByText(/환경 정보/)).toBeTruthy()
    expect(screen.getByText('SQM v8.6.9')).toBeTruthy()
  })

  it('localStorage 섹션 표시', () => {
    render(<DevPage {...defaultProps} />)
    expect(screen.getByText(/localStorage/)).toBeTruthy()
  })
})
