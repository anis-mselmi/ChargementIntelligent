import sys
from core import Downloader

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <url> [output_filename]")
        sys.exit(1)
    url = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    d = Downloader(url, out=out, threads=4)
    d.download()
