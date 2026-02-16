# v5.2.0 CODE PATCH (applied)

- inbound_mixin: alias(dmsub_lt/DM_SUB_LT/DM SUB LT) 지원 + tonbag_no TEXT 정규화(zfill3)
- db_migration_mixin: v5.2.0 tonbag_no 백필 시 비정형 sub_lt는 HARD STOP (no auto-fix)
- backup cleanup: _cleanup_old_backups() 중앙화(utils/backup.py)로 위임
