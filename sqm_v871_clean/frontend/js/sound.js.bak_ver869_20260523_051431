// SQM v8.6.8 — DB 저장 사운드 (Web Audio API, 외부 파일 불필요)
// 성공: 딩동댕 3음 상승 | 실패: beep 2회 경고음

function _tone(ac, freq, startTime, duration, type = 'sine', volume = 0.35) {
  const osc  = ac.createOscillator();
  const gain = ac.createGain();
  osc.connect(gain);
  gain.connect(ac.destination);
  osc.type = type;
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(volume, startTime);
  gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
  osc.start(startTime);
  osc.stop(startTime + duration + 0.01);
}

export function playSuccess() {
  try {
    const ac = new (window.AudioContext || window.webkitAudioContext)();
    const t  = ac.currentTime;
    _tone(ac, 587,  t + 0.00, 0.18);   // 딩 — D5
    _tone(ac, 784,  t + 0.20, 0.18);   // 동 — G5
    _tone(ac, 1047, t + 0.40, 0.28);   // 댕 — C6 (더 길게)
    setTimeout(() => ac.close(), 900);
  } catch { /* AudioContext 미지원 환경 무시 */ }
}

export function playError() {
  try {
    const ac = new (window.AudioContext || window.webkitAudioContext)();
    const t  = ac.currentTime;
    _tone(ac, 220, t + 0.00, 0.14, 'square', 0.4);   // 비프 1
    _tone(ac, 220, t + 0.22, 0.14, 'square', 0.4);   // 비프 2
    setTimeout(() => ac.close(), 700);
  } catch {}
}

// 전역 노출 (기존 코드에서 window.playSuccess() 직접 호출 가능)
if (typeof window !== 'undefined') {
  window.playSuccess = playSuccess;
  window.playError   = playError;
}
