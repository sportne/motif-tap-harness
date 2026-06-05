import subprocess


def test_xttap_duplicate_path_self_test():
    subprocess.run(["make", "-C", "c", "test"], check=True)
