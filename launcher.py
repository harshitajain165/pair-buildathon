import asyncio
import sys
import threading
import time
import webbrowser

from dotenv import load_dotenv
load_dotenv()

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from backend import app, launch_queue
from ui import PairWidget
from pair_client import PairClient

PORT = 8421


def _start_server():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


def main():
    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)

    print(f"[pair] starting server on http://localhost:{PORT} ...")
    threading.Thread(target=_start_server, daemon=True).start()

    def _open_browser():
        time.sleep(1.2)
        url = f"http://localhost:{PORT}"
        print(f"[pair] opening {url}")
        webbrowser.open(url)

    threading.Thread(target=_open_browser, daemon=True).start()

    widget = None
    pair_thread = None

    def _check_launch():
        nonlocal widget, pair_thread
        if widget is not None:
            return
        try:
            voice_id = launch_queue.get_nowait()
        except Exception:
            return

        widget = PairWidget()
        widget.show()

        client = PairClient(overlay=widget, voice_id=voice_id)

        def _run():
            asyncio.run(client.run())

        pair_thread = threading.Thread(target=_run, daemon=True)
        pair_thread.start()

    timer = QTimer()
    timer.timeout.connect(_check_launch)
    timer.start(200)

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
