# PyInstaller one-folder build; run on Windows for a Windows executable.
from pathlib import Path
import sys
import sysconfig
root = Path(SPECPATH)
datas = [(str(root/'radar'/'static'),'radar/static'),(str(root/'radar'/'seed.json'),'radar')]
for name in ['VERSION','RESEARCH.md']:
    datas.append((str(root/name),'.'))
# Portable Linux test runtimes may keep Tcl shared libraries outside ldconfig.
# Windows collects its Tcl/Tk DLLs through PyInstaller's standard hook.
binaries=[]
if sys.platform.startswith('linux'):
    libdirs={Path(sysconfig.get_config_var('LIBDIR') or sys.base_prefix+'/lib'),Path(sys.base_prefix)/'lib'}
    binaries=[(str(p),'.') for d in libdirs for p in d.glob('libtcl*.so')]
a = Analysis([str(root/'window_app.py')],pathex=[str(root)],binaries=binaries,datas=datas,
             hiddenimports=['pypdf','tkinter'],hookspath=[],hooksconfig={},runtime_hooks=[],excludes=[],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='AviationCareerRadar',debug=False,
        bootloader_ignore_signals=False,strip=False,upx=False,console=False,
        disable_windowed_traceback=False,argv_emulation=False,target_arch=None,
        codesign_identity=None,entitlements_file=None)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='AviationCareerRadar')
