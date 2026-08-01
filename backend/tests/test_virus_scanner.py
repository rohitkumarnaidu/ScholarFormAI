from unittest.mock import MagicMock, mock_open, patch

import pytest


class TestParseScanResult:
    def test_empty_input(self):
        from app.utils.virus_scanner import _parse_scan_result
        result = _parse_scan_result("")
        assert result["clean"] is True

    def test_found_threat(self):
        from app.utils.virus_scanner import _parse_scan_result
        result = _parse_scan_result("stream: Win.Trojan.Agent FOUND")
        assert result["clean"] is False
        assert "Trojan" in result["result"]

    def test_ok_status(self):
        from app.utils.virus_scanner import _parse_scan_result
        result = _parse_scan_result("stream: OK")
        assert result["clean"] is True

    def test_ok_verbose(self):
        from app.utils.virus_scanner import _parse_scan_result
        result = _parse_scan_result("/path/file: OK")
        assert result["clean"] is True

    def test_error_raises(self):
        from app.utils.virus_scanner import _parse_scan_result
        with pytest.raises(RuntimeError):
            _parse_scan_result("stream: ERROR Some error occurred")

    def test_unknown_payload_is_clean(self):
        from app.utils.virus_scanner import _parse_scan_result
        result = _parse_scan_result("some random output")
        assert result["clean"] is True

    def test_null_bytes_stripped(self):
        from app.utils.virus_scanner import _parse_scan_result
        result = _parse_scan_result("\x00stream: OK\x00")
        assert result["clean"] is True


class TestVirusScannerAsync:
    @pytest.mark.asyncio
    async def test_scan_calls_scan_file(self):
        from app.utils.virus_scanner import VirusScanner
        scanner = VirusScanner()
        with patch("app.utils.virus_scanner.scan_file", return_value={"clean": True, "engine": "clamav", "result": "clean"}):
            result = await scanner.scan("/tmp/test.txt")
        assert result["clean"] is True

    @pytest.mark.asyncio
    async def test_scan_top_level(self):
        from app.utils.virus_scanner import scan
        with patch("app.utils.virus_scanner.scan_file", return_value={"clean": True, "engine": "clamav", "result": "clean"}):
            result = await scan("/tmp/test.txt")
        assert result["clean"] is True


class TestScanFile:
    def test_ping_not_pong(self):
        from app.utils.virus_scanner import scan_file
        with patch("app.utils.virus_scanner.socket.create_connection") as mock_sock:
            mock_sock.return_value.__enter__.return_value.recv.return_value = b"NOT_PONG"
            with patch("app.utils.virus_scanner.settings.CLAMAV_HOST", "localhost"):
                with patch("app.utils.virus_scanner.settings.CLAMAV_PORT", 3310):
                    with patch("app.middleware.prometheus_metrics.MetricsManager.record_clamav_scan_duration"):
                        result = scan_file("/tmp/test.txt")
        assert result["engine"] == "unavailable"

    def test_clamd_raises_exception(self):
        from app.utils.virus_scanner import scan_file
        mock_clamd = MagicMock()
        mock_clamd.ClamdNetworkSocket.side_effect = RuntimeError("clamd crash")
        with patch("app.utils.virus_scanner.socket.create_connection") as mock_sock:
            mock_sock.return_value.__enter__.return_value.recv.side_effect = [b"PONG", b"stream: OK\x00"]
            with patch("app.utils.virus_scanner.clamd", mock_clamd):
                with patch("app.utils.virus_scanner.settings.CLAMAV_HOST", "localhost"):
                    with patch("app.utils.virus_scanner.settings.CLAMAV_PORT", 3310):
                        with patch("builtins.open", mock_open(read_data=b"data")):
                            with patch("app.middleware.prometheus_metrics.MetricsManager.record_clamav_scan_duration"):
                                result = scan_file("/tmp/test.txt")
        assert result["clean"] is True

    def test_socket_scan_fails_after_ping_ok(self):
        from app.utils.virus_scanner import scan_file
        call_log = {"sendall": 0}
        def sendall_side(data):
            call_log["sendall"] += 1
            if call_log["sendall"] >= 2:
                raise RuntimeError("broken pipe")
        with patch("app.utils.virus_scanner.socket.create_connection") as mock_sock:
            mock_sock.return_value.__enter__.return_value.recv.return_value = b"PONG"
            mock_sock.return_value.__enter__.return_value.sendall.side_effect = sendall_side
            with patch("app.utils.virus_scanner.clamd", None):
                with patch("app.utils.virus_scanner.settings.CLAMAV_HOST", "localhost"):
                    with patch("app.utils.virus_scanner.settings.CLAMAV_PORT", 3310):
                        with patch("builtins.open", mock_open(read_data=b"data")):
                            with patch("app.middleware.prometheus_metrics.MetricsManager.record_clamav_scan_duration"):
                                result = scan_file("/tmp/test.txt")
        assert result["engine"] == "unavailable"

    def test_metrics_manager_raises(self):
        from app.utils.virus_scanner import scan_file
        with patch("app.utils.virus_scanner.socket.create_connection") as mock_sock:
            mock_sock.return_value.__enter__.return_value.recv.side_effect = ConnectionRefusedError
            with patch("app.utils.virus_scanner.settings.CLAMAV_HOST", "localhost"):
                with patch("app.utils.virus_scanner.settings.CLAMAV_PORT", 3310):
                    with patch("app.middleware.prometheus_metrics.MetricsManager.record_clamav_scan_duration", side_effect=RuntimeError("metrics fail")):
                        result = scan_file("/tmp/test.txt")
        assert result["clean"] is True

    def test_clamav_unavailable_ping(self):
        from app.utils.virus_scanner import scan_file
        with patch("app.utils.virus_scanner.socket.create_connection", side_effect=ConnectionRefusedError("no clamav")):
            with patch("app.utils.virus_scanner.settings.CLAMAV_HOST", "localhost"):
                with patch("app.utils.virus_scanner.settings.CLAMAV_PORT", 3310):
                    with patch("app.middleware.prometheus_metrics.MetricsManager.record_clamav_scan_duration"):
                        result = scan_file("/tmp/test.txt")
        assert result["clean"] is True
        assert result["engine"] == "unavailable"

    def test_clamd_path(self):
        from app.utils.virus_scanner import scan_file
        mock_clamd = MagicMock()
        mock_clamd.ClamdNetworkSocket.return_value.ping.return_value = "PONG"
        mock_clamd.ClamdNetworkSocket.return_value.instream.return_value = {
            "/path/file": ("FOUND", "Win.Trojan.Test")
        }
        with patch("app.utils.virus_scanner.socket.create_connection") as mock_sock:
            mock_sock.return_value.__enter__.return_value.recv.return_value = b"PONG"
            with patch("app.utils.virus_scanner.clamd", mock_clamd):
                with patch("app.utils.virus_scanner.settings.CLAMAV_HOST", "localhost"):
                    with patch("app.utils.virus_scanner.settings.CLAMAV_PORT", 3310):
                        with patch("builtins.open", mock_open(read_data=b"data")):
                            with patch("app.middleware.prometheus_metrics.MetricsManager.record_clamav_scan_duration"):
                                result = scan_file("/tmp/test.txt")
        assert result["clean"] is False
        assert "Trojan" in result["result"]

    def test_clamd_path_clean(self):
        from app.utils.virus_scanner import scan_file
        mock_clamd = MagicMock()
        mock_clamd.ClamdNetworkSocket.return_value.ping.return_value = "PONG"
        mock_clamd.ClamdNetworkSocket.return_value.instream.return_value = {
            "/path/file": ("OK", None)
        }
        with patch("app.utils.virus_scanner.socket.create_connection") as mock_sock:
            mock_sock.return_value.__enter__.return_value.recv.return_value = b"PONG"
            with patch("app.utils.virus_scanner.clamd", mock_clamd):
                with patch("app.utils.virus_scanner.settings.CLAMAV_HOST", "localhost"):
                    with patch("app.utils.virus_scanner.settings.CLAMAV_PORT", 3310):
                        with patch("builtins.open", mock_open(read_data=b"data")):
                            with patch("app.middleware.prometheus_metrics.MetricsManager.record_clamav_scan_duration"):
                                result = scan_file("/tmp/test.txt")
        assert result["clean"] is True

    def test_clamd_unavailable_falls_to_socket(self):
        from app.utils.virus_scanner import scan_file
        with patch("app.utils.virus_scanner.socket.create_connection") as mock_sock:
            mock_sock.return_value.__enter__.return_value.recv.side_effect = [b"PONG", b"stream: OK\x00"]
            with patch("app.utils.virus_scanner.clamd", None):
                with patch("app.utils.virus_scanner.settings.CLAMAV_HOST", "localhost"):
                    with patch("app.utils.virus_scanner.settings.CLAMAV_PORT", 3310):
                        with patch("app.middleware.prometheus_metrics.MetricsManager.record_clamav_scan_duration"):
                            with patch("builtins.open", mock_open(read_data=b"safe file content")):
                                result = scan_file("/tmp/test.txt")
        assert result["clean"] is True
        assert result["engine"] == "clamav"

    def test_socket_scan_failure(self):
        from app.utils.virus_scanner import scan_file
        with patch("app.utils.virus_scanner.socket.create_connection") as mock_sock:
            mock_sock.return_value.__enter__.return_value.recv.side_effect = [b"PONG"]
            mock_sock.return_value.__enter__.return_value.sendall.side_effect = RuntimeError("broken pipe")
            with patch("app.utils.virus_scanner.clamd", None):
                with patch("app.utils.virus_scanner.settings.CLAMAV_HOST", "localhost"):
                    with patch("app.utils.virus_scanner.settings.CLAMAV_PORT", 3310):
                        with patch("app.middleware.prometheus_metrics.MetricsManager.record_clamav_scan_duration"):
                            with patch("builtins.open", mock_open(read_data=b"data")):
                                result = scan_file("/tmp/test.txt")
        assert result["clean"] is True
        assert result["engine"] == "unavailable"


class TestScanViaSocket:
    def test_clean_file(self):
        from app.utils.virus_scanner import _scan_via_socket
        with patch("builtins.open", mock_open(read_data=b"data")):
            with patch("app.utils.virus_scanner.socket.create_connection") as mock_sock:
                mock_sock.return_value.__enter__.return_value.recv.return_value = b"stream: OK\x00"
                result = _scan_via_socket("/tmp/test.txt", "localhost", 3310)
        assert result["clean"] is True

    def test_threat_found(self):
        from app.utils.virus_scanner import _scan_via_socket
        with patch("builtins.open", mock_open(read_data=b"bad data")):
            with patch("app.utils.virus_scanner.socket.create_connection") as mock_sock:
                mock_sock.return_value.__enter__.return_value.recv.return_value = b"stream: EICAR FOUND\x00"
                result = _scan_via_socket("/tmp/test.txt", "localhost", 3310)
        assert result["clean"] is False
        assert "EICAR" in result["result"]

    def test_multi_packet_response(self):
        from app.utils.virus_scanner import _scan_via_socket
        with patch("builtins.open", mock_open(read_data=b"somedata")):
            with patch("app.utils.virus_scanner.socket.create_connection") as mock_sock:
                mock_sock.return_value.__enter__.return_value.recv.side_effect = [
                    b"partial",
                    b"response",
                    b"stream: OK\x00",
                ]
                result = _scan_via_socket("/tmp/test.txt", "localhost", 3310)
        assert result["clean"] is True

    def test_multi_packet_error(self):
        from app.utils.virus_scanner import _scan_via_socket
        with patch("builtins.open", mock_open(read_data=b"somedata")):
            with patch("app.utils.virus_scanner.socket.create_connection") as mock_sock:
                mock_sock.return_value.__enter__.return_value.recv.side_effect = [
                    b"stream: ",
                    b"ERROR timeout",
                    b"\x00",
                ]
                with pytest.raises(RuntimeError):
                    _scan_via_socket("/tmp/test.txt", "localhost", 3310)


class TestVirusScannerClass:
    @pytest.mark.asyncio
    async def test_virus_scanner_scan(self):
        from app.utils.virus_scanner import virus_scanner
        with patch("app.utils.virus_scanner.scan_file", return_value={"clean": True}):
            result = await virus_scanner.scan("/tmp/test.txt")
        assert result["clean"] is True
