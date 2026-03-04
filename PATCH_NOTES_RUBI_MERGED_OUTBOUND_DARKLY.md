# RUBI MERGED PATCH (v6.3.2)
- Combines:
  - OUTBOUND UI: outbound_no dropdown + banner (from OUTBOUND_UI_TIMELINE_DROPDOWN patch)
  - COLORFUL RESKIN P1: darkly-based navy palette + table styling + assets icons

## Apply order
- If you already applied the two patches, just apply this merged patch last (overwrite).
- Goal: prevent outbound_scheduled_tab from being overwritten by reskin patch.

## Quick verification
- Log should show theme=darkly or dark=True (if UI theme is not overridden)
- Outbound tab top bar should show: '출고번호:' dropdown + status banner.
