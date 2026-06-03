from pathlib import Path
from motiftap.harness import MotifApp


def test_open_valid_file():
    with MotifApp(['./examples/fake_motif_app', '--test-mode']) as app:
        app.wait_for_idle()
        app.click('myApp.mainWindow.form.openButton', button=1)  # HIGH: XmPushButton, recorded at root (110, 50)
        app.type_text('/tmp')  # HIGH: coalesced text input
        app.press('Return')  # HIGH: keyboard action

        # Add real application assertions below.
        # Prefer files, logs, database state, dialogs, or domain results over screenshots.
        # Example:
        # assert Path('/tmp/output.dat').exists()
