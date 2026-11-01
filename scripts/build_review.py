"""Build the password-protected review section, demo/review/index.html, from review-src/.

    python scripts/build_review.py --password-file PATH      (or set MARCO_MAP_REVIEW_PASSWORD)

GitHub Pages cannot check a password on the server, and a script that only hides a page protects
nothing, since anyone can read the source. So the review page is encrypted instead: the published
file holds only ciphertext (AES-256-GCM, key from PBKDF2-SHA256 with 600,000 rounds and a random
salt) and a small unlock page that decrypts it in the browser with the Web Crypto API. Without the
password the review tool cannot be read. Limits: there is one shared password, not personal
accounts; anyone can download the ciphertext and try passwords offline, so use a long random one;
the map data and tiles the tool opens are the public ones. Personal logins come with Cloudflare
Access (README, review workflow).

The password is never written into the repository. Run this again after changing review-src/, and
to change the password.
"""
import argparse
import base64
import os
import secrets
import sys
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "review-src"
OUT = ROOT / "demo" / "review" / "index.html"
ITERATIONS = 600_000  # OWASP's 2023 figure for PBKDF2-HMAC-SHA256

LOCK_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <title>Review · Marco-Map</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="../css/demo.css">
  <style>
    .lock {{ max-width: 26rem; margin: 18vh auto 0; padding: 0 1.25rem; }}
    .lock h1 {{ font-size: var(--fs-3); margin-bottom: 0.6rem; }}
    .lock p {{ color: var(--ink-2); }}
    .lock form {{ display: flex; gap: 0.5rem; margin-top: 1rem; }}
    .lock input {{ flex: 1; font-family: var(--sans); font-size: var(--fs-1); padding: 0.5rem 0.6rem; border: 1px solid var(--rule-2); background: #fffdf8; border-radius: 2px; }}
    .lock .msg {{ font-family: var(--sans); font-size: var(--fs-0); color: var(--accent-2); min-height: 1.4em; margin-top: 0.6rem; }}
  </style>
</head>
<body>
  <main class="lock">
    <div class="kicker sans muted">Marco-Map · for specialists</div>
    <h1>Review mode</h1>
    <p>Checking and correcting the machine readings is open to the project's reviewers. Enter the password you were given.</p>
    <form id="unlock">
      <input id="pw" type="password" autocomplete="current-password" aria-label="Password" required>
      <button class="btn" type="submit">Open</button>
    </form>
    <div class="msg" id="msg" aria-live="polite"></div>
    <p class="sans muted" style="font-size: var(--fs-0); margin-top: 2rem;"><a href="../index.html">Back to the maps</a></p>
  </main>
  <script>
    (function () {{
      var SALT = '{salt}', IV = '{iv}', DATA = '{data}', ITER = {iterations};
      var KEY = 'marco-map-review-pw';
      function bytes(b64) {{ return Uint8Array.from(atob(b64), function (c) {{ return c.charCodeAt(0); }}); }}
      function decrypt(pw) {{
        var enc = new TextEncoder();
        return crypto.subtle.importKey('raw', enc.encode(pw), 'PBKDF2', false, ['deriveKey'])
          .then(function (base) {{
            return crypto.subtle.deriveKey({{ name: 'PBKDF2', salt: bytes(SALT), iterations: ITER, hash: 'SHA-256' }},
              base, {{ name: 'AES-GCM', length: 256 }}, false, ['decrypt']);
          }})
          .then(function (key) {{ return crypto.subtle.decrypt({{ name: 'AES-GCM', iv: bytes(IV) }}, key, bytes(DATA)); }})
          .then(function (plain) {{ return new TextDecoder().decode(plain); }});
      }}
      function open(pw, remember) {{
        var msg = document.getElementById('msg');
        msg.textContent = 'Opening…';
        return decrypt(pw).then(function (page) {{
          // kept for this tab only, so the page can reload (switching maps, importing) without asking again
          if (remember) {{ try {{ sessionStorage.setItem(KEY, pw); }} catch (e) {{}} }}
          document.open(); document.write(page); document.close();
        }}, function () {{
          try {{ sessionStorage.removeItem(KEY); }} catch (e) {{}}
          msg.textContent = remember ? 'That password does not open the review.' : '';
        }});
      }}
      if (!window.crypto || !crypto.subtle) {{
        document.getElementById('msg').textContent = 'This browser cannot open the review (it needs a secure https page and Web Crypto).';
        return;
      }}
      var saved = null;
      try {{ saved = sessionStorage.getItem(KEY); }} catch (e) {{}}
      if (saved) open(saved, false);
      document.getElementById('unlock').addEventListener('submit', function (e) {{
        e.preventDefault();
        open(document.getElementById('pw').value, true);
      }});
    }})();
  </script>
</body>
</html>
"""


def page_source():
    page = (SRC / "review.html").read_text(encoding="utf-8")
    script = (SRC / "review.js").read_text(encoding="utf-8")
    tag = '<script src="js/review.js"></script>'
    if page.count(tag) != 1 or '<meta charset="utf-8">' not in page:
        sys.exit("review-src/review.html no longer has the expected script tag or charset")
    if "</script" in script.lower():
        sys.exit("review.js contains '</script', which would end the inline script early")
    page = page.replace(tag, "<script>\n" + script + "\n</script>")
    # the page is served from review/, but its links and data paths are relative to the site root
    return page.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n  <base href="../">', 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--password-file")
    args = ap.parse_args()
    if args.password_file:
        password = Path(args.password_file).read_text(encoding="utf-8").strip()
    else:
        password = os.environ.get("MARCO_MAP_REVIEW_PASSWORD", "")
    if len(password) < 16:
        sys.exit("Give a password of at least 16 characters (--password-file or MARCO_MAP_REVIEW_PASSWORD).")

    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS).derive(password.encode("utf-8"))
    data = AESGCM(key).encrypt(iv, page_source().encode("utf-8"), None)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(LOCK_PAGE.format(salt=b64(salt), iv=b64(iv), data=b64(data), iterations=ITERATIONS), encoding="utf-8")
    print(f"{OUT}: {len(data):,} bytes encrypted")


if __name__ == "__main__":
    main()
