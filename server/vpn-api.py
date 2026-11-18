#!/usr/bin/env python3
"""Uygulamalar icin kucuk cihaz kayit API'si (sadece Python standart kutuphanesi).

Uygulama, kullaniciya verilen davet kodu ile cihazini kaydeder ve WireGuard
ayarlarini JSON olarak alir. Peer olusturma isini wg-kur.sh yapar.

  POST /api/cihaz   {"kod": "<davet kodu>", "cihaz": "telefon"}
      -> {"config": "<wireguard .conf metni>", "ad": "<kullanici>-telefon"}
  DELETE /api/cihaz {"kod": "...", "cihaz": "telefon"}
  GET  /api/saglik  -> {"ok": true}

Davet kodlari: /etc/wireguard/api-kodlar  (her satir: "<kullanici> <kod>")
Varsayilan olarak 127.0.0.1:8787 dinler; disariya mevcut nginx/caddy uzerinden
HTTPS ile acilmalidir (ornek: location /vpn-api/ { proxy_pass http://127.0.0.1:8787/; }).
"""
import hmac, json, os, re, subprocess, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCRIPT = os.environ.get("WG_SCRIPT", "/opt/vpn/wg-kur.sh")
KOD_DOSYA = os.environ.get("WG_KODLAR", "/etc/wireguard/api-kodlar")
CLIENT_DIR = os.environ.get("WG_CLIENT_DIR", "/etc/wireguard/clients")
HOST = os.environ.get("API_HOST", "127.0.0.1")
PORT = int(os.environ.get("API_PORT", "8787"))
AD_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}$")


def kullanici_bul(kod):
    try:
        with open(KOD_DOSYA) as f:
            for satir in f:
                p = satir.split()
                if len(p) == 2 and hmac.compare_digest(p[1], kod):
                    return p[0]
    except FileNotFoundError:
        pass
    return None


class H(BaseHTTPRequestHandler):
    def _yanit(self, kod, veri):
        b = json.dumps(veri, ensure_ascii=False).encode()
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _govde(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 4096:
            return None
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return None

    def _yetki(self):
        g = self._govde()
        if not isinstance(g, dict):
            self._yanit(400, {"hata": "gecersiz istek"}); return None
        kul = kullanici_bul(str(g.get("kod", "")))
        cihaz = str(g.get("cihaz", "")).lower()
        if not kul:
            self._yanit(401, {"hata": "gecersiz davet kodu"}); return None
        if not AD_RE.match(cihaz) or not AD_RE.match(kul):
            self._yanit(400, {"hata": "gecersiz cihaz adi"}); return None
        return f"{kul}-{cihaz}"

    def do_GET(self):
        if self.path == "/api/saglik":
            return self._yanit(200, {"ok": True})
        self._yanit(404, {"hata": "bulunamadi"})

    def do_POST(self):
        if self.path != "/api/cihaz":
            return self._yanit(404, {"hata": "bulunamadi"})
        ad = self._yetki()
        if not ad:
            return
        r = subprocess.run(["bash", SCRIPT, "ekle", ad], capture_output=True, text=True)
        yol = os.path.join(CLIENT_DIR, ad + ".conf")
        if not os.path.exists(yol):
            return self._yanit(500, {"hata": "olusturulamadi", "detay": r.stdout[-300:] + r.stderr[-300:]})
        with open(yol) as f:
            self._yanit(200, {"ad": ad, "config": f.read()})

    def do_DELETE(self):
        if self.path != "/api/cihaz":
            return self._yanit(404, {"hata": "bulunamadi"})
        ad = self._yetki()
        if not ad:
            return
        r = subprocess.run(["bash", SCRIPT, "sil", ad], capture_output=True, text=True)
        self._yanit(200 if r.returncode == 0 else 404, {"ad": ad, "silindi": r.returncode == 0})

    def log_message(self, fmt, *a):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % a))


if __name__ == "__main__":
    print(f"vpn-api {HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
