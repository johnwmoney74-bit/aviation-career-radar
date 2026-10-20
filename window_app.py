"""Entry point used by the no-console Windows executable."""
import logging
import sys
from radar.runtime import configure_logging

if __name__=='__main__':
    try:
        configure_logging()
        from app import main
        main(desktop=True)
    except Exception as exc:
        logging.getLogger('radar').exception('Application startup/runtime failure')
        if '--self-test-report' not in sys.argv:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root=tk.Tk();root.withdraw()
                messagebox.showerror('Aviation Career Radar',str(exc)+'\n\nDetails are saved under your Radar data folder in logs/radar.log.')
                root.destroy()
            except Exception:pass
        raise SystemExit(1)
