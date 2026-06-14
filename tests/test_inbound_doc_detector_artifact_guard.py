from gui_app_modular.handlers.inbound_doc_detector import InboundDocDetector


def test_collect_candidate_files_skips_gpt_artifact_subdirs(tmp_path):
    artifact = tmp_path / "11. 준글로벌_GPT_CANDIDATE_PICKER"
    artifact.mkdir()
    (artifact / "DO.pdf").write_bytes(b"%PDF-1.4 artifact")

    real_customer = tmp_path / "11. 준글로벌"
    real_customer.mkdir()
    real_file = real_customer / "BL.pdf"
    real_file.write_bytes(b"%PDF-1.4 real")

    logs = []
    detector = InboundDocDetector(logs.append)

    assert detector.collect_candidate_files(str(tmp_path)) == [str(real_file)]
    assert any("GPT 테스트 산출물 폴더 제외" in msg for msg in logs)


def test_detect_from_folder_returns_empty_for_gpt_artifact_folder(tmp_path):
    artifact = tmp_path / "3. 코스모물류_GPT_FILE_CLASSIFICATION"
    artifact.mkdir()
    (artifact / "BL.pdf").write_bytes(b"%PDF-1.4 artifact")

    detector = InboundDocDetector()

    assert detector.detect_from_folder(str(artifact), ["BL.pdf"]) == {}
