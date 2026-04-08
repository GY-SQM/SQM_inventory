/**
 * SQM Electron Desktop App — main.js
 * ★ React UI를 Electron 창에서 실행
 * ★ FastAPI 백엔드를 child_process로 자동 시작/종료
 *
 * 설치: npm install electron electron-builder --save-dev (web/ 폴더에서)
 * 실행: npx electron electron/main.js
 * 빌드: npx electron-builder
 */
const { app, BrowserWindow, shell, dialog, Menu } = require('electron');
const path   = require('path');
const { spawn, execSync } = require('child_process');
const http   = require('http');
const fs     = require('fs');

// ── 설정 ────────────────────────────────────────────────────────
const API_PORT   = 8000;
const API_URL    = `http://127.0.0.1:${API_PORT}`;
const PROJECT    = path.join(__dirname, '..');        // SQM 프로젝트 루트
const REACT_DIST = path.join(PROJECT, 'web', 'dist'); // React 빌드 파일

let mainWindow  = null;
let apiProcess  = null;

// ================================================================
// FastAPI 서버 시작
// ================================================================
function startApiServer() {
  return new Promise((resolve, reject) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    const script    = path.join(PROJECT, 'run_react_api.py');

    if (!fs.existsSync(script)) {
      reject(new Error(`run_react_api.py 없음: ${script}`));
      return;
    }

    console.log('[Electron] FastAPI 서버 시작:', script);

    apiProcess = spawn(pythonCmd, [script], {
      cwd:   PROJECT,
      stdio: ['ignore', 'pipe', 'pipe'],
      env:   { ...process.env, PYTHONUNBUFFERED: '1' },
      windowsHide: true,   // Windows에서 콘솔 창 숨김
    });

    apiProcess.stdout.on('data', d => console.log('[API]', d.toString().trim()));
    apiProcess.stderr.on('data', d => console.error('[API]', d.toString().trim()));
    apiProcess.on('error', reject);

    // 서버 준비 대기 (최대 20초)
    let attempts = 0;
    const check = setInterval(() => {
      attempts++;
      http.get(`${API_URL}/api/health`, res => {
        if (res.statusCode === 200) {
          clearInterval(check);
          console.log('[Electron] FastAPI 준비 완료');
          resolve();
        }
      }).on('error', () => {
        if (attempts > 40) {
          clearInterval(check);
          reject(new Error('FastAPI 시작 시간 초과'));
        }
      });
    }, 500);
  });
}

// ================================================================
// 메인 창 생성
// ================================================================
function createWindow() {
  mainWindow = new BrowserWindow({
    width:          1400,
    height:         900,
    minWidth:       1024,
    minHeight:      768,
    title:          'SQM 재고관리 v8.7.1',
    backgroundColor:'#0f172a',
    webPreferences: {
      nodeIntegration:    false,
      contextIsolation:   true,
      webSecurity:        true,
    },
    // 아이콘 (있으면 활성화)
    // icon: path.join(__dirname, 'icon.ico'),
  });

  // ── 로딩 화면 표시 ─────────────────────────────────────────
  mainWindow.loadURL(`data:text/html,
    <html>
      <head>
        <style>
          body { margin:0; background:#0f172a; display:flex; align-items:center;
                 justify-content:center; height:100vh; font-family:sans-serif; }
          .wrap { text-align:center; color:#f1f5f9; }
          .spinner { width:44px; height:44px; border:3px solid #334155;
                     border-top-color:#3b82f6; border-radius:50%;
                     animation:spin 0.8s linear infinite; margin:24px auto 0; }
          @keyframes spin { to { transform:rotate(360deg); } }
        </style>
      </head>
      <body>
        <div class="wrap">
          <div style="font-size:56px">📦</div>
          <div style="font-size:22px;font-weight:700;margin:12px 0 6px">SQM 재고관리</div>
          <div style="font-size:13px;color:#64748b">시스템 시작 중...</div>
          <div class="spinner"></div>
        </div>
      </body>
    </html>
  `);

  // ── FastAPI 시작 후 React 로드 ──────────────────────────────
  startApiServer()
    .then(() => {
      console.log('[Electron] React 앱 로드:', API_URL);
      mainWindow.loadURL(API_URL);
    })
    .catch(err => {
      console.error('[Electron] 서버 시작 실패:', err);
      dialog.showErrorBox(
        'SQM 시작 실패',
        `FastAPI 서버를 시작할 수 없습니다.\n\n오류: ${err.message}\n\n` +
        `Python이 설치되어 있는지 확인하세요.`
      );
      app.quit();
    });

  // 외부 링크는 브라우저로 열기
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ================================================================
// 메뉴 설정
// ================================================================
function setupMenu() {
  const menu = Menu.buildFromTemplate([
    {
      label: '파일',
      submenu: [
        { label: '새로고침', accelerator: 'F5', click: () => mainWindow?.webContents.reload() },
        { type: 'separator' },
        { label: '종료', accelerator: 'Alt+F4', click: () => app.quit() },
      ],
    },
    {
      label: '보기',
      submenu: [
        { label: '확대', accelerator: 'Ctrl+=', click: () => { const z = mainWindow?.webContents.getZoomFactor(); mainWindow?.webContents.setZoomFactor(z + 0.1); } },
        { label: '축소', accelerator: 'Ctrl+-', click: () => { const z = mainWindow?.webContents.getZoomFactor(); mainWindow?.webContents.setZoomFactor(Math.max(0.5, z - 0.1)); } },
        { label: '원래 크기', accelerator: 'Ctrl+0', click: () => mainWindow?.webContents.setZoomFactor(1) },
        { type: 'separator' },
        { label: '개발자 도구', accelerator: 'F12', click: () => mainWindow?.webContents.toggleDevTools() },
      ],
    },
  ]);
  Menu.setApplicationMenu(menu);
}

// ================================================================
// 앱 이벤트
// ================================================================
app.whenReady().then(() => {
  setupMenu();
  createWindow();
});

app.on('window-all-closed', () => {
  // FastAPI 서버 종료
  if (apiProcess) {
    console.log('[Electron] FastAPI 서버 종료');
    if (process.platform === 'win32') {
      try { execSync(`taskkill /PID ${apiProcess.pid} /T /F`); } catch(e) {}
    } else {
      apiProcess.kill('SIGTERM');
    }
    apiProcess = null;
  }
  app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
