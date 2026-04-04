# GPT P0 초기코드골격
생성일: 2026-04-04 16:25 (Asia/Seoul)
인코딩: UTF-8
용도: Recon 이후 Claude Code 또는 Cursor에서 바로 붙여 넣어 시작할 수 있는 P0 starter skeleton

---

## [질문]
P0 기준으로 실제 코딩 초안까지 작성 가능한지 요청

## [질문의도]
아래 코드는 **최종 완성본이 아니라**, Recon 이후 실제 시그니처와 경로를 맞춰 빠르게 진입하기 위한 골격 코드다.

주의:
- import 경로는 실제 v867 구조에 맞게 수정해야 한다.
- engine 호출 인자는 Recon에서 확인한 실제 시그니처 기준으로 맞춰야 한다.
- DB 세션/커넥션 방식도 기존 react_api 구조에 맞춰야 한다.

---

## [응답]

## 1. `react_api/schemas/actions.py`

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: Dict[str, Any] = Field(default_factory=dict)


class FileUploadResponse(BaseModel):
    filename: str
    file_type: str
    preview: Dict[str, Any] = Field(default_factory=dict)


class InboundCreateRequest(BaseModel):
    source_file: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[str] = None


class OutboundExecuteRequest(BaseModel):
    lot_no: Optional[str] = None
    tonbag_ids: List[str] = Field(default_factory=list)
    qty_mt: Optional[float] = None
    customer_name: Optional[str] = None
    outbound_ref: Optional[str] = None
    created_by: Optional[str] = None


class OutboundCancelRequest(BaseModel):
    outbound_id: Optional[str] = None
    outbound_ref: Optional[str] = None
    tonbag_ids: List[str] = Field(default_factory=list)
    reason: Optional[str] = None
    cancelled_by: Optional[str] = None


class LocationUpdateRequest(BaseModel):
    tonbag_id: str
    new_location: str
    updated_by: Optional[str] = None
    note: Optional[str] = None
```

---

## 2. `react_api/services/engine_adapter.py`

```python
from __future__ import annotations

from typing import Any, Dict


class EngineAdapter:
    def __init__(self, engine: Any):
        self.engine = engine

    def get_lot_detail(self, lot_no: str) -> Dict[str, Any]:
        # TODO: Recon 후 실제 함수명/반환형에 맞게 조정
        detail = self.engine.get_lot_detail(lot_no)
        items = self.engine.get_lot_items(lot_no)
        return {
            "lot": detail or {},
            "items": items or [],
        }

    def process_inbound(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: 실제 시그니처 확인 후 수정
        result = self.engine.process_inbound(payload)
        return {"result": result}

    def process_outbound(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: 실제 시그니처 확인 후 수정
        result = self.engine.process_outbound(payload)
        return {"result": result}

    def cancel_outbound(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: 실제 시그니처 확인 후 수정
        result = self.engine.cancel_outbound_tonbag(payload)
        return {"result": result}

    def update_location(self, tonbag_id: str, new_location: str, note: str | None = None) -> Dict[str, Any]:
        # TODO: 실제 시그니처 확인 후 수정
        result = self.engine.update_tonbag_location(tonbag_id, new_location, note=note)
        return {"result": result}
```

---

## 3. `react_api/services/action_service.py`

```python
from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Callable, Dict

from react_api.schemas.actions import (
    FileUploadResponse,
    InboundCreateRequest,
    LocationUpdateRequest,
    OutboundCancelRequest,
    OutboundExecuteRequest,
)
from react_api.services.engine_adapter import EngineAdapter


class ActionService:
    def __init__(self, engine_factory: Callable[[], Any], tx_factory: Callable[[], AbstractContextManager[Any]]):
        self.engine_factory = engine_factory
        self.tx_factory = tx_factory

    def _adapter(self) -> EngineAdapter:
        return EngineAdapter(self.engine_factory())

    def create_inbound(self, req: InboundCreateRequest) -> Dict[str, Any]:
        with self.tx_factory():
            return self._adapter().process_inbound(req.payload)

    def execute_outbound(self, req: OutboundExecuteRequest) -> Dict[str, Any]:
        payload = req.model_dump()
        with self.tx_factory():
            return self._adapter().process_outbound(payload)

    def cancel_outbound(self, req: OutboundCancelRequest) -> Dict[str, Any]:
        payload = req.model_dump()
        with self.tx_factory():
            return self._adapter().cancel_outbound(payload)

    def update_location(self, req: LocationUpdateRequest) -> Dict[str, Any]:
        with self.tx_factory():
            return self._adapter().update_location(
                tonbag_id=req.tonbag_id,
                new_location=req.new_location,
                note=req.note,
            )

    def parse_uploaded_file(self, saved_path: str, file_type: str) -> FileUploadResponse:
        # TODO: Recon 후 실제 parser registry/dispatcher 연결
        preview = {
            "saved_path": saved_path,
            "file_type": file_type,
            "status": "preview_not_connected_yet",
        }
        return FileUploadResponse(filename=saved_path, file_type=file_type, preview=preview)
```

---

## 4. `react_api/routes/actions.py`

```python
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from react_api.schemas.actions import (
    ApiResponse,
    InboundCreateRequest,
    LocationUpdateRequest,
    OutboundCancelRequest,
    OutboundExecuteRequest,
)
from react_api.services.action_service import ActionService

router = APIRouter(prefix="", tags=["actions"])


def get_action_service() -> ActionService:
    # TODO: 실제 engine factory / transaction factory 연결
    raise NotImplementedError("Connect real engine_factory and tx_factory after Recon")


@router.post("/files/upload", response_model=ApiResponse)
async def upload_file(
    file: UploadFile = File(...),
    service: Annotated[ActionService, Depends(get_action_service)] = None,
):
    upload_dir = Path("uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / file.filename
    data = await file.read()
    target.write_bytes(data)

    suffix = target.suffix.lower()
    if suffix in {".pdf"}:
        file_type = "pdf"
    elif suffix in {".xls", ".xlsx", ".csv"}:
        file_type = "excel"
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    parsed = service.parse_uploaded_file(str(target), file_type)
    return ApiResponse(success=True, message="Upload completed", data=parsed.model_dump())


@router.post("/inbound/create", response_model=ApiResponse)
def create_inbound(
    req: InboundCreateRequest,
    service: Annotated[ActionService, Depends(get_action_service)],
):
    result = service.create_inbound(req)
    return ApiResponse(success=True, message="Inbound created", data=result)


@router.post("/outbound/execute", response_model=ApiResponse)
def execute_outbound(
    req: OutboundExecuteRequest,
    service: Annotated[ActionService, Depends(get_action_service)],
):
    result = service.execute_outbound(req)
    return ApiResponse(success=True, message="Outbound executed", data=result)


@router.put("/outbound/cancel", response_model=ApiResponse)
def cancel_outbound(
    req: OutboundCancelRequest,
    service: Annotated[ActionService, Depends(get_action_service)],
):
    result = service.cancel_outbound(req)
    return ApiResponse(success=True, message="Outbound cancelled", data=result)


@router.put("/location/update", response_model=ApiResponse)
def update_location(
    req: LocationUpdateRequest,
    service: Annotated[ActionService, Depends(get_action_service)],
):
    result = service.update_location(req)
    return ApiResponse(success=True, message="Location updated", data=result)
```

---

## 5. `web/src/api/actionApi.js`

```javascript
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function request(url, options = {}) {
  const response = await fetch(`${API_BASE}${url}`, options);
  const data = await response.json();
  if (!response.ok || data.success === false) {
    throw new Error(data.detail || data.message || "Request failed");
  }
  return data;
}

export async function uploadActionFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  return request("/files/upload", {
    method: "POST",
    body: formData,
  });
}

export async function createInbound(payload) {
  return request("/inbound/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function executeOutbound(payload) {
  return request("/outbound/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function cancelOutbound(payload) {
  return request("/outbound/cancel", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateLocation(payload) {
  return request("/location/update", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
```

---

## 6. `web/src/components/TopMenuBar.jsx`

```jsx
import { useState } from "react";

export default function TopMenuBar({ currentTab, onOpenInbound, onOpenOutbound, onOpenSearch, onRunIntegrityCheck }) {
  const [openMenu, setOpenMenu] = useState(null);

  const toggleMenu = (name) => {
    setOpenMenu((prev) => (prev === name ? null : name));
  };

  return (
    <div className="top-menu-bar">
      <div className="menu-group">
        <button onClick={() => toggleMenu("search")}>검색</button>
        {openMenu === "search" && (
          <div className="dropdown-panel">
            <button onClick={onOpenSearch}>통합 검색 열기</button>
          </div>
        )}
      </div>

      <div className="menu-group">
        <button onClick={() => toggleMenu("tools")}>도구</button>
        {openMenu === "tools" && (
          <div className="dropdown-panel">
            <button onClick={onRunIntegrityCheck}>정합성 체크</button>
          </div>
        )}
      </div>

      <div className="menu-group">
        <button onClick={() => toggleMenu("inbound")}>입고</button>
        {openMenu === "inbound" && (
          <div className="dropdown-panel">
            <button onClick={onOpenInbound}>입고 파싱 모달</button>
          </div>
        )}
      </div>

      <div className="menu-group">
        <button onClick={() => toggleMenu("outbound")}>출고</button>
        {openMenu === "outbound" && (
          <div className="dropdown-panel">
            <button onClick={onOpenOutbound}>출고 처리 모달</button>
          </div>
        )}
      </div>

      <div className="menu-group current-tab">현재 탭: {currentTab || "-"}</div>
    </div>
  );
}
```

---

## 7. `web/src/components/modals/LotDetailModal.jsx`

```jsx
export default function LotDetailModal({ open, lotNo, loading, error, detail, onClose }) {
  if (!open) return null;

  const lot = detail?.lot || {};
  const items = detail?.items || [];
  const history = detail?.history || [];
  const allocation = detail?.allocation || [];

  return (
    <div className="modal-backdrop">
      <div className="modal-panel wide">
        <div className="modal-header">
          <h3>LOT 상세 - {lotNo}</h3>
          <button onClick={onClose}>닫기</button>
        </div>

        {loading && <div>불러오는 중...</div>}
        {error && <div className="error-text">{error}</div>}

        {!loading && !error && (
          <>
            <section>
              <h4>기본정보</h4>
              <pre>{JSON.stringify(lot, null, 2)}</pre>
            </section>

            <section>
              <h4>톤백 목록</h4>
              <pre>{JSON.stringify(items, null, 2)}</pre>
            </section>

            <section>
              <h4>이력</h4>
              <pre>{JSON.stringify(history, null, 2)}</pre>
            </section>

            <section>
              <h4>배정 상태</h4>
              <pre>{JSON.stringify(allocation, null, 2)}</pre>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
```

---

## 8. `web/src/components/modals/InboundParseModal.jsx`

```jsx
import { useState } from "react";
import { createInbound, uploadActionFile } from "../../api/actionApi";

export default function InboundParseModal({ open, onClose }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  if (!open) return null;

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setMessage("");
    try {
      const result = await uploadActionFile(file);
      setPreview(result.data.preview || result.data);
      setMessage("파싱 미리보기 생성 완료");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateInbound = async () => {
    setLoading(true);
    setMessage("");
    try {
      const result = await createInbound({
        source_file: file?.name,
        payload: preview || {},
      });
      setMessage(result.message || "입고 생성 완료");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-panel wide">
        <div className="modal-header">
          <h3>입고 파싱</h3>
          <button onClick={onClose}>닫기</button>
        </div>

        <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <div className="button-row">
          <button onClick={handleUpload} disabled={loading || !file}>업로드/파싱</button>
          <button onClick={handleCreateInbound} disabled={loading || !preview}>입고 생성</button>
        </div>

        {message && <div>{message}</div>}
        {preview && <pre>{JSON.stringify(preview, null, 2)}</pre>}
      </div>
    </div>
  );
}
```

---

## 9. `web/src/components/modals/OutboundExecuteModal.jsx`

```jsx
import { useState } from "react";
import { cancelOutbound, executeOutbound } from "../../api/actionApi";

export default function OutboundExecuteModal({ open, onClose }) {
  const [payload, setPayload] = useState({
    lot_no: "",
    tonbag_ids: [],
    qty_mt: "",
    customer_name: "",
    outbound_ref: "",
  });
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const handleExecute = async () => {
    setLoading(true);
    setMessage("");
    try {
      const result = await executeOutbound({
        ...payload,
        qty_mt: payload.qty_mt ? Number(payload.qty_mt) : null,
      });
      setMessage(result.message || "출고 실행 완료");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    setLoading(true);
    setMessage("");
    try {
      const result = await cancelOutbound({
        outbound_ref: payload.outbound_ref,
        tonbag_ids: payload.tonbag_ids,
      });
      setMessage(result.message || "출고 취소 완료");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-panel">
        <div className="modal-header">
          <h3>출고 처리</h3>
          <button onClick={onClose}>닫기</button>
        </div>

        <input
          placeholder="LOT NO"
          value={payload.lot_no}
          onChange={(e) => setPayload({ ...payload, lot_no: e.target.value })}
        />
        <input
          placeholder="QTY(MT)"
          value={payload.qty_mt}
          onChange={(e) => setPayload({ ...payload, qty_mt: e.target.value })}
        />
        <input
          placeholder="고객명"
          value={payload.customer_name}
          onChange={(e) => setPayload({ ...payload, customer_name: e.target.value })}
        />
        <input
          placeholder="출고 참조번호"
          value={payload.outbound_ref}
          onChange={(e) => setPayload({ ...payload, outbound_ref: e.target.value })}
        />

        <div className="button-row">
          <button onClick={handleExecute} disabled={loading}>출고 실행</button>
          <button onClick={handleCancel} disabled={loading}>출고 취소</button>
        </div>

        {message && <div>{message}</div>}
      </div>
    </div>
  );
}
```

---

## 10. `web/src/App.jsx` 연결 예시

```jsx
import { useState } from "react";
import TopMenuBar from "./components/TopMenuBar";
import LotDetailModal from "./components/modals/LotDetailModal";
import InboundParseModal from "./components/modals/InboundParseModal";
import OutboundExecuteModal from "./components/modals/OutboundExecuteModal";

export default function App() {
  const [currentTab, setCurrentTab] = useState("Dashboard");
  const [showInbound, setShowInbound] = useState(false);
  const [showOutbound, setShowOutbound] = useState(false);
  const [showLotDetail, setShowLotDetail] = useState(false);
  const [lotNo, setLotNo] = useState("");

  return (
    <>
      <TopMenuBar
        currentTab={currentTab}
        onOpenInbound={() => setShowInbound(true)}
        onOpenOutbound={() => setShowOutbound(true)}
        onOpenSearch={() => console.log("TODO: search popup")}
        onRunIntegrityCheck={() => console.log("TODO: integrity check")}
      />

      <InboundParseModal open={showInbound} onClose={() => setShowInbound(false)} />
      <OutboundExecuteModal open={showOutbound} onClose={() => setShowOutbound(false)} />
      <LotDetailModal
        open={showLotDetail}
        lotNo={lotNo}
        loading={false}
        error={""}
        detail={{}}
        onClose={() => setShowLotDetail(false)}
      />
    </>
  );
}
```

---

## 11. 테스트 초안

### Backend

```bash
python -m py_compile react_api/routes/actions.py
python -m py_compile react_api/schemas/actions.py
python -m py_compile react_api/services/action_service.py
python -m py_compile react_api/services/engine_adapter.py
```

### Frontend

```bash
npm run build
```

### Smoke

```text
1. /docs 에 files/upload, inbound/create, outbound/execute, outbound/cancel, location/update 노출 확인
2. 상단 메뉴바 렌더 확인
3. InboundParseModal 열기 확인
4. OutboundExecuteModal 열기 확인
5. LOT 상세 모달 열기 확인
```

---

## 12. 최종 판단

위 코드는 P0의 **시작점**으로는 충분하다.
다만 실제 완성도는 Recon 결과에 따라 아래 4가지를 반드시 보정해야 한다.

1. import 경로
2. engine 함수 시그니처
3. DB transaction 처리 방식
4. parser dispatcher 연결 방식
