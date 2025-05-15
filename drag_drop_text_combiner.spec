# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

# Collect data files for tkinterdnd2 (e.g., tkdnd DLLs on Windows)
tkdnd_datas = collect_data_files('tkinterdnd2')

a = Analysis(
    ['drag_drop_text_combiner.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('C:\\Users\\jacad\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages\\pywin32_system32', 'pywin32_system32')
    ],
    hiddenimports=['win32serviceutil', 'win32service'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='jac_combiner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='drag_drop_text_combiner',
)
