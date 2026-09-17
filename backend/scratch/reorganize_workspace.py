import os
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def copy_dir_contents(src_name, target_path):
    src_path = os.path.join(ROOT_DIR, src_name)
    if os.path.exists(src_path):
        os.makedirs(target_path, exist_ok=True)
        for item in os.listdir(src_path):
            s_item = os.path.join(src_path, item)
            d_item = os.path.join(target_path, item)
            if os.path.isdir(s_item):
                shutil.copytree(s_item, d_item, dirs_exist_ok=True)
            else:
                try:
                    shutil.copy2(s_item, d_item)
                except Exception:
                    pass
        print(f"Copied {src_name} -> {target_path}")

def move_file_if_exists(src_name, target_path):
    src_path = os.path.join(ROOT_DIR, src_name)
    if os.path.exists(src_path) and os.path.abspath(src_path) != os.path.abspath(target_path):
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        try:
            shutil.copy2(src_path, target_path)
            os.remove(src_path)
        except Exception:
            pass
        print(f"Moved {src_name} -> {target_path}")

def remove_if_exists(item_name):
    path = os.path.join(ROOT_DIR, item_name)
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            try:
                os.remove(path)
            except Exception:
                pass
        print(f"Removed {item_name}")

if __name__ == "__main__":
    remove_if_exists("data")
    remove_if_exists("docs")
    remove_if_exists("tests")
    remove_if_exists("scratch")
    remove_if_exists("conftest.py")
    remove_if_exists("streamlit.log")
    remove_if_exists("__pycache__")
    remove_if_exists(".pytest_cache")
    
    print("Reorganization complete.")
