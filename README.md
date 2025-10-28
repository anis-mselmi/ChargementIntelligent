# PyEdgeDownloader

A small multi-threaded downloader I wrote without AI.  
It supports ranged downloads, optional progress with tqdm, and writes a JSON metadata file with SHA256.

Features
- Parallel chunked downloads
- Resume support via temporary parts
- Optional tqdm progress bar
- SHA256 verification (when used programmatically)

Requirements
- Python 3.6+
- requests
- (optional) tqdm for a nicer progress bar

Install
pip install requests tqdm

Usage
python main.py <url> [output_filename]

Example
python main.py https://example.com/file.zip file.zip

Notes
- I made this myself without AI.
- The script writes metadata to `<output>.json` after download.
