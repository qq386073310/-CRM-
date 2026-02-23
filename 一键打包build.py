import os
import shutil
import subprocess
import sys
import time

def clean_build_dirs():
    """清理构建目录"""
    dirs = ['build', 'dist']
    for d in dirs:
        if os.path.exists(d):
            print(f"Cleaning {d}...")
            try:
                shutil.rmtree(d)
            except Exception as e:
                print(f"Warning: Could not fully clean {d}: {e}")

def build():
    print("Starting build process...")
    
    # 1. Clean previous builds
    clean_build_dirs()

    # Detect platform
    is_mac = sys.platform == 'darwin'
    is_win = sys.platform.startswith('win')

    # Define dist dir by platform
    if is_mac:
        # Inside the .app bundle's executable directory
        dist_dir = os.path.join('dist', 'CustomerManager.app', 'Contents', 'MacOS')
    else:
        dist_dir = os.path.join('dist', 'CustomerManager')
    
    # PyInstaller command
    add_data_sep = ':' if is_mac else ';'
    cmd = ['pyinstaller', '--noconfirm', '--clean', '--onedir', '--windowed', '--name', 'CustomerManager']

    # Icon per platform (optional on mac if .icns not present)
    if is_win and os.path.exists('assets/icons/48x48.ico'):
        cmd += ['--icon', 'assets/icons/48x48.ico']
    elif is_mac and os.path.exists('assets/icons/app.icns'):
        cmd += ['--icon', 'assets/icons/app.icns']

    # Embed resources (accessible via _MEIPASS if using get_resource_path)
    cmd += ['--add-data', f'config/style.qss{add_data_sep}config']
    cmd += ['--add-data', f'config/dark_style.qss{add_data_sep}config']
    cmd += ['--add-data', f'assets/icons{add_data_sep}assets/icons']
    cmd += ['--add-data', f'resources/icons{add_data_sep}resources/icons']

    # Hidden imports - Critical for dynamic imports
    hidden_imports = [
        'fitz',
        'openpyxl',
        'docxtpl',
        'sqlite3',
        'json',
        'ctypes',
        # Project Modules
        'modules.dashboard',
        'modules.customer',
        'modules.business',
        'modules.finance',
        'modules.contract',
        'modules.work_arrangement',
        'modules.invoice_system',
        'modules.web_nav',
        'modules.settings',
        'modules.recycle_bin',
        'modules.todo',
        'modules.notes',
        'modules.common_widgets',
        'modules.base_card',
    ]
    for mod in hidden_imports:
        cmd += ['--hidden-import', mod]

    # Entry point
    cmd += ['main.py']
    
    print("Running PyInstaller...")
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Error: PyInstaller failed with code {e.returncode}")
        sys.exit(1)
    
    print("Post-build copy operations...")
    
    # Ensure destination directories exist
    os.makedirs(os.path.join(dist_dir, 'config'), exist_ok=True)
    os.makedirs(os.path.join(dist_dir, 'assets', 'favicons'), exist_ok=True)
    os.makedirs(os.path.join(dist_dir, 'data'), exist_ok=True)
    
    # 1. Copy Config Files (Editable by user)
    if os.path.exists('config/table_config.json'):
        shutil.copy2('config/table_config.json', os.path.join(dist_dir, 'config', 'table_config.json'))
        print("- Copied table_config.json")
        
    # 2. Copy Root Data Files
    root_files = [
        'web_nav.json',
        'auth.db',
        'invoice_config.json',
        'notes.json',
        'todo_list.json'
    ]
    
    for f in root_files:
        if os.path.exists(f):
            shutil.copy2(f, os.path.join(dist_dir, f))
            print(f"- Copied {f}")
            
    # 3. Copy Data Directory Content (Databases)
    # Note: Copying .db files ensures the built app has the current data
    if os.path.exists('data'):
        for f in os.listdir('data'):
            src = os.path.join('data', f)
            dst = os.path.join(dist_dir, 'data', f)
            
            if os.path.isfile(src):
                if f.endswith('.db') or f.endswith('.db-wal') or f.endswith('.db-shm'):
                    shutil.copy2(src, dst)
                    print(f"- Copied {src}")
            elif os.path.isdir(src):
                # Copy directories like contract_attachments
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"- Copied directory {src}")

    # 4. Copy Favicons Cache
    if os.path.exists('assets/favicons'):
        for f in os.listdir('assets/favicons'):
            src = os.path.join('assets/favicons', f)
            dst = os.path.join(dist_dir, 'assets', 'favicons', f)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
        print("- Copied favicons")

    # 5. Copy Templates (Important for contract generation)
    if os.path.exists('templates'):
        dst = os.path.join(dist_dir, 'templates')
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree('templates', dst)
        print("- Copied templates")

    print(f"\nBuild complete successfully!")
    if is_mac:
        app_path = os.path.abspath(os.path.join('dist', 'CustomerManager.app'))
        print(f"App bundle location: {app_path}")
    else:
        exe_path = os.path.abspath(os.path.join(dist_dir, 'CustomerManager.exe'))
        print(f"Executable location: {exe_path}")

if __name__ == "__main__":
    build()
