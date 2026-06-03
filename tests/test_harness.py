from pathlib import Path

from motiftap.harness import MotifApp


def test_keep_artifacts_uses_persistent_session_directory():
    app = MotifApp(["/bin/true"], keep_artifacts=True)
    session_dir = app.session_dir

    assert session_dir.exists()
    assert app._tmp is None

    app.__exit__(None, None, None)

    assert session_dir.exists()

    # Clean up the directory created by this unit test. Runtime users who pass
    # keep_artifacts=True keep the path for inspection after a failed GUI test.
    session_dir.rmdir()


def test_default_session_directory_is_cleaned_up():
    app = MotifApp(["/bin/true"])
    session_dir = Path(app.session_dir)

    assert session_dir.exists()

    app.__exit__(None, None, None)

    assert not session_dir.exists()
