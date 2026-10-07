"""Runs the fine-tuning helper checks under pytest."""
import os, subprocess, sys
def test_ft_lib_checks_pass():
    here = os.path.dirname(os.path.abspath(__file__))
    r = subprocess.run([sys.executable, os.path.join(here, "check_ft_lib.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
