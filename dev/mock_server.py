"""마젯 서버 대역(개발·화면 확인용).

실제 마젯 서버(8801 공개 창구, /public/*)와 같은 형식으로 응답해서, 집 PC 서버 없이 web/ 페이지를 시험해 볼 수 있다.
  python dev/mock_server.py          ->  http://localhost:8787
- GET  /api/health      : 항상 정상
- POST /api/chat        : 줄 단위 JSON 스트림(start -> text/emotion/seg -> done). 글자와 문장 사이에 지연을 둔다
- GET  /api/speech      : 1초쯤 되는 톤(입 모양 시험용). 실제 목소리가 아니다
- POST /api/transcribe  : 올라온 소리의 형식과 크기만 기록하고 고정된 문장을 돌려준다
- GET  /__mock/state    : 마지막 요청 기록(테스트용)
"""
import io, json, math, os, struct, sys, threading, time, wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
STATE = {"chat": [], "transcribe": [], "speech": 0, "limit_transcribe": 0, "limit_chat": 0, "reply_delay": 0.25}
TRANSCRIPT = os.environ.get("MOCK_TRANSCRIPT", "안녕 맞짱이 오늘 뭐해")


def tone(sec=1.1, rate=16000):
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        n = int(sec * rate); fr = bytearray()
        for i in range(n):
            t = i / rate
            amp = 0.35 * (0.5 + 0.5 * math.sin(2 * math.pi * 4 * t)) * min(1, t * 20, (sec - t) * 20)
            fr += struct.pack("<h", int(32767 * amp * math.sin(2 * math.pi * 220 * t)))
        w.writeframes(bytes(fr))
    return out.getvalue()


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"  # 응답 끝에서 연결을 닫아 스트림이 끝났음을 알린다

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/health":
            return self._json({"ok": True})
        if u.path == "/__mock/state":
            return self._json(STATE)
        if u.path == "/__mock/set":  # 예: /__mock/set?limit_chat=1  (다음 N번 요청을 429로 답한다)
            for k, v in parse_qs(u.query).items():
                if k in STATE and isinstance(STATE[k], (int, float)):
                    STATE[k] = type(STATE[k])(v[0])
            return self._json(STATE)
        if u.path == "/api/speech":
            STATE["speech"] += 1
            b = tone()
            self.send_response(200); self.send_header("Content-Type", "audio/wav"); self.send_header("Content-Length", str(len(b)))
            self.end_headers(); self.wfile.write(b); return
        p = u.path.lstrip("/") or "index.html"
        f = os.path.normpath(os.path.join(ROOT, p))
        if not f.startswith(os.path.normpath(ROOT)) or not os.path.isfile(f):
            self.send_response(404); self.end_headers(); return
        types = {".html": "text/html; charset=utf-8", ".webp": "image/webp", ".json": "application/json"}
        b = open(f, "rb").read()
        self.send_response(200); self.send_header("Content-Type", types.get(os.path.splitext(f)[1], "application/octet-stream"))
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n)
        if u.path == "/api/transcribe":
            if STATE["limit_transcribe"] > 0:
                STATE["limit_transcribe"] -= 1
                return self._json({"error": "rate"}, 429)
            STATE["transcribe"].append({"bytes": n, "riff": b"RIFF" in body[:400], "wave": b"WAVEfmt" in body[:600]})
            time.sleep(0.3)
            return self._json({"text": TRANSCRIPT})
        if u.path == "/api/chat":
            if STATE["limit_chat"] > 0:
                STATE["limit_chat"] -= 1
                return self._json({"error": "rate"}, 429)
            req = json.loads(body or b"{}")
            STATE["chat"].append(req.get("messages", [])[-1:])
            self.send_response(200); self.send_header("Content-Type", "application/x-ndjson"); self.end_headers()
            d = STATE["reply_delay"]

            def w(o):
                self.wfile.write((json.dumps(o, ensure_ascii=False) + "\n").encode()); self.wfile.flush()
            rid = "mock%d" % int(time.time() * 1000)
            w({"t": "start", "reply": rid})
            w({"t": "text", "d": "<|ACT {\"emotion\":\"happy\"}|>"}); w({"t": "emotion", "e": "happy"})
            for i, s in enumerate(["어 마짱이 왔네. ", "오늘은 그냥 느리게 쉬고 있었어. ", "너는 뭐 했어?"]):
                time.sleep(d)
                for ch in s:
                    w({"t": "text", "d": ch}); time.sleep(0.01)
                w({"t": "seg", "i": i})
            w({"t": "done"}); return
        self.send_response(404); self.end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    print("mock server: http://localhost:%d" % port)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
