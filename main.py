import asyncio

from dotenv import load_dotenv

load_dotenv()

from pair_client import PairClient


class TerminalStatus:
    ICONS = {
        "ready":     "✦",
        "listening": "◉",
        "thinking":  "◌",
        "speaking":  "▶",
        "error":     "✗",
    }

    def set_status(self, status: str):
        key = status.split(" ")[0].split(":")[0]
        icon = self.ICONS.get(key, "·")
        print(f"\r[Pair] {icon}  {status:<40}", end="", flush=True)

    def run(self):
        pass


def main():
    status = TerminalStatus()
    client = PairClient(overlay=status)

    print("Pair starting… (Ctrl+C to quit)\n")
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nPair stopped.")


if __name__ == "__main__":
    main()
