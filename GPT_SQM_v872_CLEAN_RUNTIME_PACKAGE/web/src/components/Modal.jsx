/**
 * 공통 모달 래퍼.
 * Props: open, onClose, title, children, width
 */
const overlay = {
  position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
  background: 'rgba(0,0,0,0.5)', display: 'flex',
  alignItems: 'center', justifyContent: 'center', zIndex: 9999,
};

const box = (width) => ({
  background: '#fff', borderRadius: 10, padding: 0,
  width: width || 600, maxWidth: '95vw', maxHeight: '90vh',
  overflow: 'auto', boxShadow: '0 12px 40px rgba(0,0,0,0.2)',
});

const header = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  padding: '14px 20px', borderBottom: '1px solid #e2e8f0',
  background: '#f8fafc',
};

const closeBtn = {
  border: 'none', background: 'none', fontSize: 20,
  cursor: 'pointer', color: '#64748b', lineHeight: 1,
};

export default function Modal({ open, onClose, title, children, width }) {
  if (!open) return null;
  return (
    <div style={overlay} onClick={onClose}>
      <div style={box(width)} onClick={(e) => e.stopPropagation()}>
        <div style={header}>
          <strong style={{ fontSize: 15 }}>{title}</strong>
          <button style={closeBtn} onClick={onClose}>&times;</button>
        </div>
        <div style={{ padding: 20 }}>{children}</div>
      </div>
    </div>
  );
}
