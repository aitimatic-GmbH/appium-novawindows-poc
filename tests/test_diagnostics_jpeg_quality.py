from appium_novawindows_poc.diagnostics import get_screenshot_jpeg_quality


def test_get_screenshot_jpeg_quality_uses_default_when_unset(monkeypatch):
    monkeypatch.delenv("WINDOWS_SCREENSHOT_JPEG_QUALITY", raising=False)
    assert get_screenshot_jpeg_quality() == 80


def test_get_screenshot_jpeg_quality_reads_valid_value(monkeypatch):
    monkeypatch.setenv("WINDOWS_SCREENSHOT_JPEG_QUALITY", "65")
    assert get_screenshot_jpeg_quality() == 65


def test_get_screenshot_jpeg_quality_accepts_lower_bound(monkeypatch):
    monkeypatch.setenv("WINDOWS_SCREENSHOT_JPEG_QUALITY", "1")
    assert get_screenshot_jpeg_quality() == 1


def test_get_screenshot_jpeg_quality_accepts_upper_bound(monkeypatch):
    monkeypatch.setenv("WINDOWS_SCREENSHOT_JPEG_QUALITY", "100")
    assert get_screenshot_jpeg_quality() == 100


def test_get_screenshot_jpeg_quality_falls_back_on_non_numeric_value(monkeypatch, capsys):
    monkeypatch.setenv("WINDOWS_SCREENSHOT_JPEG_QUALITY", "hoch")
    assert get_screenshot_jpeg_quality() == 80
    assert "hoch" in capsys.readouterr().out


def test_get_screenshot_jpeg_quality_falls_back_on_out_of_range_value(monkeypatch, capsys):
    monkeypatch.setenv("WINDOWS_SCREENSHOT_JPEG_QUALITY", "120")
    assert get_screenshot_jpeg_quality() == 80
    assert "120" in capsys.readouterr().out
