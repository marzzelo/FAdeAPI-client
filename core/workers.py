# core/workers.py
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
import traceback

class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(str)
    result = Signal(object)

class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(res)
        except Exception:
            self.signals.error.emit(traceback.format_exc())
        finally:
            self.signals.finished.emit()

def run_bg(fn, on_result=None, on_error=None, *args, **kwargs):
    """Convenience para lanzar en el pool global."""
    w = Worker(fn, *args, **kwargs)
    if on_result:
        w.signals.result.connect(on_result)
    if on_error:
        w.signals.error.connect(on_error)
    QThreadPool.globalInstance().start(w)
