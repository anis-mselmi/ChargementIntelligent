import os, sys, math, json, time, hashlib, threading, requests
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

CHUNK_SIZE = 1024 * 1024
MAX_RETRIES = 5
BACKOFF_FACTOR = 1.5
USER_AGENT = "PyEdgeDownloader/1.0"

def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def safe_mkdir(p):
    try: os.makedirs(p)
    except: pass

def download_chunk(session, url, start, end, tmp_path, headers, progress_callback):
    h = dict(headers); h["Range"] = f"bytes={start}-{end}"
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(url, headers=h, stream=True, timeout=30)
            if r.status_code in (200, 206):
                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(32768):
                        if not chunk: continue
                        f.write(chunk)
                        if progress_callback: progress_callback(len(chunk))
                return True
        except requests.RequestException:
            time.sleep(BACKOFF_FACTOR ** attempt)
    return False

class Downloader:
    def __init__(self, url, out=None, threads=4, resume=True):
        self.url = url
        self.out = out or url.split("/")[-1] or "file"
        self.threads = max(1, threads)
        self.resume = resume
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.tmp = self.out + ".parts"
        safe_mkdir(self.tmp)

    def _info(self):
        r = self.session.head(self.url, allow_redirects=True, timeout=10)
        r.raise_for_status()
        size = int(r.headers.get("Content-Length", 0))
        ok = "bytes" in r.headers.get("Accept-Ranges", "").lower()
        return size, ok

    def download(self, expected_sha=None):
        size, ok = self._info()
        if not ok or self.threads == 1:
            return self._single(expected_sha)
        num = math.ceil(size / CHUNK_SIZE)
        parts = [(i, i * CHUNK_SIZE, min(size - 1, (i + 1) * CHUNK_SIZE - 1)) for i in range(num)]
        lock = threading.Lock()
        done = [0]
        pbar = tqdm(total=size, unit="B", unit_scale=True, desc=self.out) if tqdm else None

        def cb(n):
            with lock:
                done[0] += n
                if pbar: pbar.update(n)
                else:
                    pct = done[0] * 100 / size
                    sys.stdout.write(f"\r{pct:.1f}%"); sys.stdout.flush()

        def worker(tasks):
            while True:
                with lock:
                    if not tasks: return
                    i, s, e = tasks.pop()
                tmpf = os.path.join(self.tmp, f"part-{i:05d}.tmp")
                download_chunk(self.session, self.url, s, e, tmpf, self.session.headers, cb)

        tasks = parts[:]
        ths = [threading.Thread(target=worker, args=(tasks,)) for _ in range(self.threads)]
        [t.start() for t in ths]; [t.join() for t in ths]
        if pbar: pbar.close()

        tmp_final = self.out + ".part"
        with open(tmp_final, "wb") as out:
            for i, s, e in parts:
                pf = os.path.join(self.tmp, f"part-{i:05d}.tmp")
                with open(pf, "rb") as f:
                    out.write(f.read())
        os.replace(tmp_final, self.out)
        try:
            for f in os.listdir(self.tmp): os.remove(os.path.join(self.tmp, f))
            os.rmdir(self.tmp)
        except: pass
        if expected_sha:
            got = sha256_of_file(self.out)
            if got.lower() != expected_sha.lower():
                raise RuntimeError("SHA256 mismatch")
        meta = {"url": self.url, "file": self.out, "size": os.path.getsize(self.out), "sha256": sha256_of_file(self.out)}
        with open(self.out + ".json", "w") as mf: json.dump(meta, mf, indent=2)
        print(f"\nSaved: {self.out}")

    def _single(self, expected_sha):
        r = self.session.get(self.url, stream=True)
        tmp = self.out + ".part"
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(32768):
                if chunk: f.write(chunk)
        os.replace(tmp, self.out)
        if expected_sha:
            got = sha256_of_file(self.out)
            if got.lower() != expected_sha.lower():
                raise RuntimeError("SHA256 mismatch")
        print(f"Saved: {self.out}")
