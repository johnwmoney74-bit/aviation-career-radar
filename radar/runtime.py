"""Desktop lifecycle support shared by the Windows bundle and source launcher."""
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import urllib.request
import webbrowser
from .storage import data_path

ROOT=Path(__file__).resolve().parent.parent
VERSION=(ROOT/'VERSION').read_text(encoding='utf-8').strip()

def configure_logging():
    folder=data_path()/'logs';folder.mkdir(parents=True,exist_ok=True)
    logger=logging.getLogger('radar')
    if not logger.handlers:
        h=RotatingFileHandler(folder/'radar.log',maxBytes=1_000_000,backupCount=2,encoding='utf-8')
        h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(h);logger.setLevel(logging.INFO)
    return logger

def open_existing(path):
    """Only reuse a local instance whose random identity matches our runtime file."""
    try:
        r=json.loads((path/'running.json').read_text())
        port=int(r['port'])
        if not 1<=port<=65535:return False
        url=f'http://127.0.0.1:{port}'
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url+'/api/health',timeout=1.5) as response:health=json.load(response)
        if health.get('instance')!=r['instance']:return False
        webbrowser.open(url);return True
    except (OSError,ValueError,KeyError):return False

def controller(server,engine,url,stopped):
    import tkinter as tk
    from tkinter import ttk
    root=tk.Tk();root.title('Aviation Career Radar');root.geometry('450x235');root.resizable(False,False)
    root.configure(padx=24,pady=20)
    ttk.Label(root,text='Aviation Career Radar',font=('Segoe UI',17,'bold')).pack(anchor='w')
    ttk.Label(root,text='The dashboard runs in your browser.\nKeep this small window open while using it.').pack(anchor='w',pady=(10,12))
    status=tk.StringVar(value='Ready · '+VERSION)
    ttk.Label(root,textvariable=status,wraplength=395).pack(anchor='w')
    controls=ttk.Frame(root);controls.pack(anchor='w',pady=(16,0))
    ttk.Button(controls,text='Open dashboard',command=lambda:webbrowser.open(url)).pack(side='left',padx=(0,12))
    closing=False
    def exit_requested():
        nonlocal closing
        closing=True;finish()
    def finish():
        if engine.progress['running']:
            status.set('Finishing the current refresh before exiting…');root.after(400,finish)
        else:
            import threading
            threading.Thread(target=server.shutdown,daemon=True).start()
    ttk.Button(controls,text='Exit Radar',command=exit_requested).pack(side='left')
    root.protocol('WM_DELETE_WINDOW',exit_requested)
    def poll():
        if stopped.is_set():root.destroy();return
        if not closing:status.set(engine.progress['message'][:100])
        root.after(400,poll)
    root.after(400,poll);root.mainloop()
