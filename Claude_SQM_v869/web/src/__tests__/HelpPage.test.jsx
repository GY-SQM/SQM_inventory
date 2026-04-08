/**
 * HelpPage 렌더링 테스트
 */
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import HelpPage from '../pages/HelpPage.jsx'

describe('HelpPage', () => {
  it('페이지 제목 렌더링', () => {
    render(<HelpPage />)
    expect(screen.getByText(/도움말/)).toBeTruthy()
  })

  it('4개 탭 모두 렌더링', () => {
    render(<HelpPage />)
    expect(screen.getByText(/단축키/)).toBeTruthy()
    expect(screen.getByText(/STATUS 안내/)).toBeTruthy()
    expect(screen.getByText(/업무 흐름/)).toBeTruthy()
    expect(screen.getByText(/탭 안내/)).toBeTruthy()
  })

  it('단축키 탭 — 기본으로 표시됨', () => {
    render(<HelpPage />)
    // F5 단축키가 기본 탭에 보여야 함
    expect(screen.getByText('F5')).toBeTruthy()
  })

  it('STATUS 탭 클릭 시 AVAILABLE 표시', () => {
    render(<HelpPage />)
    const statusTab = screen.getByText(/STATUS 안내/)
    fireEvent.click(statusTab)
    expect(screen.getByText('AVAILABLE')).toBeTruthy()
  })

  it('업무 흐름 탭 클릭 시 입고 단계 표시', () => {
    render(<HelpPage />)
    const workflowTab = screen.getByText(/업무 흐름/)
    fireEvent.click(workflowTab)
    expect(screen.getByText(/1. 입고/)).toBeTruthy()
  })
})
