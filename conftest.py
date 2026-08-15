"""
pytest configuration and sys.path registration for Missing Person Identification System test suite.
"""
import sys
import os
import importlib
import glob

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

backend_pkgs = ['auth', 'config', 'database', 'models', 'repositories', 'services', 'utils']

for pkg in backend_pkgs:
    b_pkg_name = f"backend.{pkg}"
    try:
        b_pkg = importlib.import_module(b_pkg_name)
        sys.modules[pkg] = b_pkg
    except Exception:
        pass

    target_dir = os.path.join(ROOT_DIR, 'backend', pkg)
    for fpath in glob.glob(os.path.join(target_dir, '*.py')):
        fname = os.path.basename(fpath)
        mod_name = os.path.splitext(fname)[0]
        if mod_name == '__init__':
            continue
        submod_b_name = f"backend.{pkg}.{mod_name}"
        submod_root_name = f"{pkg}.{mod_name}"
        try:
            submod_obj = importlib.import_module(submod_b_name)
            sys.modules[submod_root_name] = submod_obj
        except Exception:
            pass

try:
    f_ui = importlib.import_module("frontend.ui")
    sys.modules["ui"] = f_ui
    for fpath in glob.glob(os.path.join(ROOT_DIR, 'frontend', 'ui', '*.py')):
        fname = os.path.basename(fpath)
        mod_name = os.path.splitext(fname)[0]
        if mod_name == '__init__':
            continue
        submod_f_name = f"frontend.ui.{mod_name}"
        submod_root_name = f"ui.{mod_name}"
        try:
            submod_obj = importlib.import_module(submod_f_name)
            sys.modules[submod_root_name] = submod_obj
        except Exception:
            pass
except Exception:
    pass
