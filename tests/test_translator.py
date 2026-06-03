from pathlib import Path

from motiftap.translator import translate_recording


def test_translate_example_recording():
    result = translate_recording(
        Path("examples/recordings/open_valid_file"),
        app_argv=["./examples/fake_motif_app", "--test-mode"],
        test_name="open_valid_file",
    )

    assert "def test_open_valid_file" in result.code
    assert "app.click('myApp.mainWindow.form.openButton'" in result.code
    assert "app.type_text('/tmp')" in result.code
    assert result.counts["HIGH"] >= 2
