import asyncio
import sys
import threading

from dotenv import load_dotenv
load_dotenv()

from PyQt6.QtWidgets import QApplication
from ui import PairWidget
from pair_client import PairClient


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # keep alive even if widget hidden

    widget = PairWidget()
    widget.show()

    client = PairClient(overlay=widget)

    def run_pair():
        asyncio.run(client.run())

    thread = threading.Thread(target=run_pair, daemon=True)
    thread.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
