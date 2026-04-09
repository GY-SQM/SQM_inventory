/**
 * InboundModal — detectDocType 단위 테스트
 * Android 멀티파일 업로드 시 파일명으로 문서 유형을 자동 감지하는 함수를 검증합니다.
 */
import { describe, it, expect } from 'vitest';
import { detectDocType } from '../components/InboundModal.jsx';

describe('detectDocType', () => {
  it('BL 파일명 감지', () => {
    expect(detectDocType('BL_2025_001.pdf')).toBe('bl');
    expect(detectDocType('bill_of_lading.pdf')).toBe('bl');
    expect(detectDocType('선하증권_MIC9000.pdf')).toBe('bl');
  });

  it('PL 파일명 감지', () => {
    expect(detectDocType('PL_2025_001.pdf')).toBe('pl');
    expect(detectDocType('packing_list.pdf')).toBe('pl');
    expect(detectDocType('packinglist_MIC.pdf')).toBe('pl');
  });

  it('FA 파일명 감지', () => {
    expect(detectDocType('FA_2025_001.pdf')).toBe('fa');
    expect(detectDocType('invoice_MIC9000.pdf')).toBe('fa');
    expect(detectDocType('commercial_invoice.pdf')).toBe('fa');
  });

  it('DO 파일명 감지 (우선순위 최상)', () => {
    expect(detectDocType('DO_2025_001.pdf')).toBe('do');
    expect(detectDocType('delivery_order_01.pdf')).toBe('do');
  });

  it('알 수 없는 파일명은 null 반환', () => {
    expect(detectDocType('random_document.pdf')).toBeNull();
    expect(detectDocType('2025_shipment.pdf')).toBeNull();
  });

  it('대소문자 구분 없이 감지', () => {
    expect(detectDocType('BL_ABC.PDF')).toBe('bl');
    expect(detectDocType('PACKING_LIST.pdf')).toBe('pl');
    expect(detectDocType('Invoice.PDF')).toBe('fa');
  });
});
