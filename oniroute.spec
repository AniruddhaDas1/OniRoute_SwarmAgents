# OniRoute PyInstaller Spec — Standalone Executable Build
# Usage: pyinstaller oniroute.spec
# Output: dist/oniroute (single executable)

import platform

block_cipher = None

a = Analysis(
    ['cli/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config/', 'config/'),
        ('agents/', 'agents/'),
        ('skills/', 'skills/'),
        ('workflows/', 'workflows/'),
    ],
    hiddenimports=[
        'runtime',
        'runtime.loader',
        'runtime.resolver',
        'runtime.validator',
        'runtime.intent',
        'runtime.mission',
        'runtime.router',
        'runtime.experience',
        'runtime.control',
        'runtime.distribution',
        'runtime.workspace',
        'runtime.skills',
        'runtime.engineering',
        'typer',
        'pydantic',
        'yaml',
        'rich',
        'networkx',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe_name = 'oniroute'
if platform.system() == 'Windows':
    exe_name = 'oniroute.exe'

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
