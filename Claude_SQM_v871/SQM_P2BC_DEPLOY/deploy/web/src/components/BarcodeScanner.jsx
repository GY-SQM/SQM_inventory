/**
 * BarcodeScanner.jsx — 스마트폰 카메라 바코드 스캔 (P2-D)
 * 광양 창고에서 톤백 바코드 → 즉시 PICKED 처리
 * 배치 위치: web/src/components/BarcodeScanner.jsx
 *
 * 의존성: quagga2 (npm install @ericblade/quagga2)
 * 또는 BarcodeDetector API (최신 크롬/안드로이드 지원)
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { api } from '../api/client';

// ── 유틸 ──────────────────────────────────────────────────────
function useNativeBarcodeDetector() {
  return typeof window !== 'undefined' && 'BarcodeDetector' in window;
}

// ── 스캔 결과 히스토리 행 ──────────────────────────────────────
function ScanHistoryRow({ item }) {
  const statusColor = item.ok ? '#22c55e' : '#ef4444';
  return (
    <div style={{
      padding: '10px 14px',
      borderBottom: '1px solid #1e293b',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    }}>
      <div>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#f1f5f9' }}>
          {item.uid}
        </div>
        <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
          {item.message}
        </div>
      </div>
      <div style={{
        width: 10, height: 10, borderRadius: '50%',
        background: statusColor, flexShrink: 0,
      }} />
    </div>
  );
}

// ── 메인 BarcodeScanner ───────────────────────────────────────
export default function BarcodeScanner({ onClose }) {
  const videoRef      = useRef(null);
  const canvasRef     = useRef(null);
  const intervalRef   = useRef(null);
  const streamRef     = useRef(null);
  const lastScannedRef = useRef('');

  const [scanning,  setScanning]  = useState(false);
  const [history,   setHistory]   = useState([]);
  const [error,     setError]     = useState('');
  const [processing, setProcessing] = useState(false);
  const [mode,      setMode]      = useState('pick');
  // mode: 'pick' = RESERVED→PICKED, 'confirm' = PICKED→OUTBOUND

  const hasNativeDetector = useNativeBarcodeDetector();

  // ── 카메라 시작 ─────────────────────────────────────────────
  const startCamera = useCallback(async () => {
    setError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',   // 후면 카메라
          width:  { ideal: 1280 },
          height: { ideal: 720 },
        }
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setScanning(true);
        startDetection();
      }
    } catch (e) {
      setError(`카메라 접근 실패: ${e.message}`);
    }
  }, []);

  // ── 카메라 중지 ─────────────────────────────────────────────
  const stopCamera = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    setScanning(false);
  }, []);

  useEffect(() => () => stopCamera(), [stopCamera]);

  // ── 바코드 감지 루프 ────────────────────────────────────────
  const startDetection = useCallback(() => {
    if (hasNativeDetector) {
      startNativeDetection();
    } else {
      // Quagga2 폴백 (동적 로드)
      startQuaggaDetection();
    }
  }, [hasNativeDetector]);

  // BarcodeDetector API (크롬 안드로이드 지원)
  const startNativeDetection = useCallback(() => {
    const detector = new window.BarcodeDetector({
      formats: ['code_128', 'code_39', 'qr_code', 'ean_13', 'data_matrix']
    });

    intervalRef.current = setInterval(async () => {
      if (!videoRef.current || !canvasRef.current) return;
      const video  = videoRef.current;
      const canvas = canvasRef.current;
      const ctx    = canvas.getContext('2d');

      canvas.width  = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);

      try {
        const barcodes = await detector.detect(canvas);
        if (barcodes.length > 0) {
          const code = barcodes[0].rawValue;
          if (code && code !== lastScannedRef.current) {
            lastScannedRef.current = code;
            await handleScan(code);
            // 2초 쿨다운
            setTimeout(() => { lastScannedRef.current = ''; }, 2000);
          }
        }
      } catch (e) {
        // 감지 중 에러 무시 (프레임마다 발생 가능)
      }
    }, 300);
  }, []);

  // Quagga2 폴백 (동적 import)
  const startQuaggaDetection = useCallback(async () => {
    try {
      const Quagga = (await import('@ericblade/quagga2')).default;
      Quagga.init({
        inputStream: {
          type: 'LiveStream',
          target: videoRef.current,
          constraints: { facingMode: 'environment' },
        },
        decoder: {
          readers: ['code_128_reader', 'code_39_reader', 'ean_reader'],
        },
      }, (err) => {
        if (err) { setError(`Quagga 초기화 실패: ${err}`); return; }
        Quagga.start();
        Quagga.onDetected(async (result) => {
          const code = result?.codeResult?.code;
          if (code && code !== lastScannedRef.current) {
            lastScannedRef.current = code;
            await handleScan(code);
            setTimeout(() => { lastScannedRef.current = ''; }, 2000);
          }
        });
      });
    } catch (e) {
      setError('바코드 라이브러리 로드 실패. 수동 입력을 이용하세요.');
    }
  }, []);

  // ── 스캔 결과 처리 ──────────────────────────────────────────
  const handleScan = useCallback(async (uid) => {
    if (processing) return;
    setProcessing(true);

    // 진동 피드백 (모바일)
    if ('vibrate' in navigator) navigator.vibrate(100);

    try {
      let res, message;

      if (mode === 'pick') {
        // tonbag_uid로 피킹 처리
        res = await api.post('/outbound/execute', {
          items: [{ uid, qty_kg: 0, sub_lt: 0 }],
          source: 'BARCODE_SCAN',
          stop_at_picked: true,
        });
        message = res?.success
          ? `✅ 피킹 완료 (PICKED)`
          : `❌ ${res?.message || '처리 실패'}`;
      } else {
        // confirm mode
        res = await api.post('/outbound/execute', {
          items: [{ uid, qty_kg: 0, sub_lt: 0 }],
          source: 'BARCODE_SCAN',
          stop_at_picked: false,
        });
        message = res?.success
          ? `✅ 출고 확정 (OUTBOUND)`
          : `❌ ${res?.message || '처리 실패'}`;
      }

      setHistory(prev => [
        { uid, ok: res?.success, message, ts: new Date().toLocaleTimeString() },
        ...prev.slice(0, 19)
      ]);
    } catch (e) {
      setHistory(prev => [
        { uid, ok: false, message: e.message, ts: new Date().toLocaleTimeString() },
        ...prev.slice(0, 19)
      ]);
    } finally {
      setProcessing(false);
    }
  }, [mode, processing]);

  // ── 수동 입력 ───────────────────────────────────────────────
  const [manualUid, setManualUid] = useState('');
  const handleManualSubmit = async () => {
    if (!manualUid.trim()) return;
    await handleScan(manualUid.trim());
    setManualUid('');
  };

  // ── 렌더 ────────────────────────────────────────────────────
  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: '#0f172a',
      display: 'flex', flexDirection: 'column',
      fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
      zIndex: 9000,
    }}>
      {/* 헤더 */}
      <div style={{
        background: '#1e293b', padding: '12px 16px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderBottom: '1px solid #334155',
      }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9' }}>
            📷 바코드 스캔
          </div>
          <div style={{ fontSize: 11, color: '#64748b' }}>
            {hasNativeDetector ? 'BarcodeDetector' : 'Quagga2'} 엔진
          </div>
        </div>
        <button onClick={onClose || stopCamera} style={{
          background: '#334155', border: 'none', borderRadius: 8,
          color: '#94a3b8', padding: '6px 12px', cursor: 'pointer',
        }}>✕ 닫기</button>
      </div>

      {/* 모드 선택 */}
      <div style={{ display: 'flex', gap: 8, padding: '12px 16px' }}>
        {[
          { id: 'pick',    label: '피킹 처리', sub: 'RESERVED→PICKED' },
          { id: 'confirm', label: '출고 확정', sub: 'PICKED→OUTBOUND' },
        ].map(({ id, label, sub }) => (
          <button key={id} onClick={() => setMode(id)} style={{
            flex: 1, padding: '10px 8px', borderRadius: 8, border: 'none',
            background: mode === id ? '#3b82f6' : '#1e293b',
            color: mode === id ? '#fff' : '#64748b',
            cursor: 'pointer',
          }}>
            <div style={{ fontSize: 13, fontWeight: 700 }}>{label}</div>
            <div style={{ fontSize: 10 }}>{sub}</div>
          </button>
        ))}
      </div>

      {/* 카메라 뷰 */}
      <div style={{ position: 'relative', flex: '0 0 220px', background: '#000', margin: '0 16px', borderRadius: 12, overflow: 'hidden' }}>
        <video ref={videoRef} style={{ width: '100%', height: '100%', objectFit: 'cover' }} playsInline muted />
        <canvas ref={canvasRef} style={{ display: 'none' }} />

        {/* 스캔 가이드 라인 */}
        {scanning && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <div style={{
              width: '80%', height: 2,
              background: 'rgba(59,130,246,0.8)',
              boxShadow: '0 0 8px #3b82f6',
              animation: 'scan-line 2s ease-in-out infinite',
            }} />
          </div>
        )}

        {processing && (
          <div style={{
            position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontSize: 18,
          }}>
            ⏳ 처리 중...
          </div>
        )}

        {!scanning && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexDirection: 'column', gap: 12,
          }}>
            <button onClick={startCamera} style={{
              background: '#3b82f6', border: 'none', borderRadius: 10,
              color: '#fff', padding: '12px 24px', fontSize: 15,
              fontWeight: 700, cursor: 'pointer',
            }}>
              📷 카메라 시작
            </button>
          </div>
        )}
      </div>

      {error && (
        <div style={{ margin: '8px 16px', padding: 10, background: '#7f1d1d', borderRadius: 8, fontSize: 12, color: '#fca5a5' }}>
          {error}
        </div>
      )}

      {/* 수동 입력 */}
      <div style={{ padding: '10px 16px', display: 'flex', gap: 8 }}>
        <input
          value={manualUid}
          onChange={e => setManualUid(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleManualSubmit()}
          placeholder="바코드 수동 입력 (Enter)"
          style={{
            flex: 1, background: '#1e293b', border: '1px solid #334155',
            borderRadius: 8, padding: '10px 12px', color: '#f1f5f9',
            fontSize: 14, outline: 'none',
          }}
        />
        <button onClick={handleManualSubmit} style={{
          background: '#3b82f6', border: 'none', borderRadius: 8,
          color: '#fff', padding: '10px 16px', cursor: 'pointer', fontSize: 14,
        }}>
          처리
        </button>
      </div>

      {/* 스캔 이력 */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <div style={{ padding: '8px 16px 4px', fontSize: 12, color: '#64748b', fontWeight: 600 }}>
          스캔 이력 ({history.length}건)
        </div>
        {history.length === 0
          ? <div style={{ color: '#475569', textAlign: 'center', padding: 24, fontSize: 13 }}>
              바코드를 스캔하세요
            </div>
          : history.map((item, i) => <ScanHistoryRow key={i} item={item} />)
        }
      </div>

      {/* 스캔 라인 애니메이션 CSS */}
      <style>{`
        @keyframes scan-line {
          0%   { transform: translateY(-80px); opacity: 0.3; }
          50%  { opacity: 1; }
          100% { transform: translateY(80px); opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}
