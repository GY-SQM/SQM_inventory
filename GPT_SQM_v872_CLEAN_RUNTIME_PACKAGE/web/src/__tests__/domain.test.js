/**
 * SQM 핵심 도메인 로직 유닛 테스트
 * 순수 JavaScript 함수 테스트 — 서버/브라우저 불필요
 */
import { describe, it, expect } from 'vitest'
import { buildQS } from '../api/index.js'

// ── STATUS 상태 전이 규칙 ──────────────────────────────────────
describe('STATUS 상태 전이', () => {
  const VALID_TRANSITIONS = {
    AVAILABLE: ['RESERVED', 'PICKED', 'OUTBOUND'],
    RESERVED:  ['AVAILABLE', 'PICKED', 'CANCELLED'],
    PICKED:    ['OUTBOUND', 'AVAILABLE'],
    OUTBOUND:  ['SOLD'],
    SOLD:      [],
    RETURN:    ['AVAILABLE'],
  }

  it('AVAILABLE → RESERVED 허용', () => {
    const transitions = VALID_TRANSITIONS['AVAILABLE']
    expect(transitions).toContain('RESERVED')
  })

  it('SOLD → 다른 상태 불가 (최종 상태)', () => {
    const transitions = VALID_TRANSITIONS['SOLD']
    expect(transitions).toHaveLength(0)
  })

  it('RETURN → AVAILABLE (재입고 가능)', () => {
    const transitions = VALID_TRANSITIONS['RETURN']
    expect(transitions).toContain('AVAILABLE')
  })
})

// ── LOT 번호 유효성 검사 ───────────────────────────────────────
describe('LOT 번호 유효성', () => {
  // 8~11자리 숫자 허용 (OCR 오인식 대비)
  const LOT_REGEX = /^\d{8,11}$/

  it('10자리 표준 LOT → 유효', () => {
    expect(LOT_REGEX.test('1125072340')).toBe(true)
  })

  it('9자리 (OCR 오인식) → 허용', () => {
    expect(LOT_REGEX.test('112507234')).toBe(true)
  })

  it('11자리 (OCR 오인식) → 허용', () => {
    expect(LOT_REGEX.test('11250723401')).toBe(true)
  })

  it('8자리 미만 → 거부', () => {
    expect(LOT_REGEX.test('1234567')).toBe(false)
  })

  it('문자 포함 → 거부', () => {
    expect(LOT_REGEX.test('LOT1234567')).toBe(false)
  })
})

// ── 무게 계산 ─────────────────────────────────────────────────
describe('무게 계산', () => {
  it('톤백 단가 계산: (총무게 - 1kg) / 톤백수', () => {
    const total_kg  = 5001  // 10개 × 500kg + 샘플 1kg
    const bag_count = 10
    const unit_kg   = (total_kg - 1) / bag_count
    expect(unit_kg).toBe(500)
  })

  it('MT → kg 변환', () => {
    const mt = 5.001
    expect(Math.round(mt * 1000)).toBe(5001)
  })

  it('정합성 오차 허용 범위 ±1.0kg', () => {
    const initial = 5001
    const current = 3001.5
    const picked  = 1999
    const diff    = Math.abs(initial - (current + picked))
    expect(diff).toBeLessThanOrEqual(1.0)
  })
})

// ── Allocation 유효성 ──────────────────────────────────────────
describe('Allocation 유효성', () => {
  it('동일 SALE REF → 동일 고객이어야 함', () => {
    const allocations = [
      { sale_ref: 'SR-001', customer: 'CATL' },
      { sale_ref: 'SR-001', customer: 'CATL' },   // 같은 고객 → OK
      { sale_ref: 'SR-001', customer: 'BYD'  },   // 다른 고객 → 오류
    ]
    const saleRefMap = {}
    const errors = []
    for (const a of allocations) {
      if (saleRefMap[a.sale_ref] && saleRefMap[a.sale_ref] !== a.customer) {
        errors.push(`${a.sale_ref}: 고객 불일치`)
      }
      saleRefMap[a.sale_ref] = a.customer
    }
    expect(errors).toHaveLength(1)
    expect(errors[0]).toContain('SR-001')
  })

  it('샘플 행 식별: qty_mt < 0.01', () => {
    const rows = [
      { lot_no: 'L001', qty_mt: 5.000, is_sample: false },
      { lot_no: 'L001', qty_mt: 0.001, is_sample: true  },  // 샘플
    ]
    const sampleRow = rows.find(r => r.qty_mt < 0.01)
    expect(sampleRow).toBeTruthy()
    expect(sampleRow.is_sample).toBe(true)
  })
})

// ── buildQS 헬퍼 ──────────────────────────────────────────────
describe('buildQS', () => {
  it('페이지네이션 파라미터 생성', () => {
    const qs = buildQS({ page: 2, page_size: 50 })
    expect(qs).toContain('page=2')
    expect(qs).toContain('page_size=50')
  })

  it('빈 문자열 필터 제외', () => {
    const qs = buildQS({ lot_no: '', status: 'AVAILABLE' })
    expect(qs).not.toContain('lot_no')
    expect(qs).toContain('status=AVAILABLE')
  })
})
