# Two-Track Packaging Guide

This project supports two package tracks:

## 1) Runtime Package (for end users)
- Purpose: distribute executable/app runtime only
- Tests: excluded
- Output: `packages/runtime/SQM_v<version>_runtime_<timestamp>.zip`
- Command:
  - `package_runtime.bat`
  - or `powershell -ExecutionPolicy Bypass -File scripts/package_tracks.ps1 -Track runtime`

## 2) Dev Package (for QA/dev team)
- Purpose: source bundle for debugging, patching, and test execution
- Tests: included (`tests/`, `requirements-dev.txt`, `pytest.ini`, etc.)
- Output: `packages/dev/SQM_v<version>_dev_<timestamp>.zip`
- Command:
  - `package_dev.bat`
  - or `powershell -ExecutionPolicy Bypass -File scripts/package_tracks.ps1 -Track dev`

## Optional modes
- Build both tracks:
  - `powershell -ExecutionPolicy Bypass -File scripts/package_tracks.ps1 -Track all`
- Skip runtime EXE build and package existing `dist/` only:
  - `powershell -ExecutionPolicy Bypass -File scripts/package_tracks.ps1 -Track runtime -SkipBuild`

## Notes
- Runtime track calls `build_exe.bat` by default.
- Dev track excludes cache/output folders and local virtual environments.
- Generated packages are saved under `packages/`.
