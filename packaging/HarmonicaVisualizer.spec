# -*- mode: python ; coding: utf-8 -*-
# HarmonicaVisualizer.spec - PyInstaller onedir distribution configuration

import sys
import os

block_cipher = None

# Support running PyInstaller from either project root or packaging/ directory
if 'SPECPATH' in globals():
    base_dir = os.path.abspath(os.path.join(SPECPATH, '..'))
else:
    base_dir = os.path.abspath('.')

a = Analysis(
    [os.path.join(base_dir, 'src', 'main.py')],
    pathex=[os.path.join(base_dir, 'src')],
    binaries=[],
    datas=[
        (os.path.join(base_dir, 'src', 'skins'), 'skins'),
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtOpenGLWidgets',
        'PyQt6.QtOpenGL',
        'pygame',
        'numpy',
        'mido',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'pytest',
        'test',
        'xmlrpc',
        'pydoc',
        'setuptools',
        'distutils',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HarmonicaVisualizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='HarmonicaVisualizer',
)
