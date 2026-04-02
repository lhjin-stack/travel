"""
server.py — 운임 달성률 보고서 로컬 서버
사내 PC에서 실행 후 팀원들이 http://<PC-IP>:8000 으로 접속

실행:  python server.py
"""
import subprocess, sys, logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler

BASE_DIR    = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("freight-server")

app = FastAPI(title="KMTC 운임 달성률")

# ── 캐시 ─────────────────────────────────────────────────────
_cached_html: str = ""
_last_updated: str = ""


def _run_generation() -> bool:
    """gen_freight_ach.py → gen_html_ach.py 순차 실행."""
    python = sys.executable
    for script in ["gen_freight_ach.py", "gen_html_ach.py"]:
        log.info(f"실행: {script}")
        r = subprocess.run(
            [python, str(BASE_DIR / script)],
            cwd=str(BASE_DIR),
            capture_output=True, text=True, timeout=180
        )
        if r.returncode != 0:
            log.error(f"{script} 실패:\n{r.stderr}")
            return False
        log.info(r.stdout.strip())
    return True


def _load_latest_html() -> str:
    """reports/ 에서 가장 최신 freight_ach_*.html 읽기."""
    files = sorted(REPORTS_DIR.glob("freight_ach_*.html"), reverse=True)
    if not files:
        return "<h2>아직 데이터가 없습니다. 잠시 후 새로고침 해주세요.</h2>"
    return files[0].read_text(encoding="utf-8")


def _deploy_to_vercel():
    """최신 HTML을 public/index.html에 복사 후 git push → Vercel 자동 배포."""
    try:
        html = _load_latest_html()
        (BASE_DIR / "index.html").write_text(html, encoding="utf-8")
        subprocess.run(
            ["git", "add", str(BASE_DIR / "index.html")],
            cwd=str(BASE_DIR.parent), capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"auto: freight-ach update {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
            cwd=str(BASE_DIR.parent), capture_output=True
        )
        r = subprocess.run(
            ["git", "push"],
            cwd=str(BASE_DIR.parent), capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            log.info("Vercel 배포 push 완료")
        else:
            log.warning(f"git push 실패: {r.stderr.strip()}")
    except Exception as e:
        log.warning(f"Vercel 배포 실패 (로컬 서버는 정상): {e}")


def refresh():
    """데이터 재생성 + 캐시 갱신."""
    global _cached_html, _last_updated
    log.info("데이터 갱신 시작...")
    ok = _run_generation()
    if ok:
        _cached_html  = _load_latest_html()
        _last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")
        log.info(f"갱신 완료: {_last_updated}")
        _deploy_to_vercel()
    else:
        log.error("갱신 실패 — 이전 캐시 유지")
    return ok


# ── 라우트 ────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def index():
    if not _cached_html:
        return HTMLResponse("<h2>데이터 준비 중... 잠시 후 새로고침 해주세요.</h2>")
    return HTMLResponse(_cached_html)


@app.post("/api/refresh")
def api_refresh():
    ok = refresh()
    if ok:
        return JSONResponse({"status": "ok", "updated_at": _last_updated})
    return JSONResponse({"status": "error"}, status_code=500)


@app.get("/api/status")
def api_status():
    return {"last_updated": _last_updated, "cached": bool(_cached_html)}


# ── 스케줄러: 매일 오전 8시 자동 갱신 ─────────────────────────
scheduler = BackgroundScheduler(timezone="Asia/Seoul")
scheduler.add_job(refresh, "cron", hour=8, minute=0, id="daily_refresh")
scheduler.start()


# ── 시작 시 초기 데이터 로드 ──────────────────────────────────
@app.on_event("startup")
def startup():
    global _cached_html, _last_updated
    # 기존 HTML이 있으면 바로 서빙, 없으면 생성
    existing = sorted(REPORTS_DIR.glob("freight_ach_*.html"), reverse=True)
    if existing:
        _cached_html  = existing[0].read_text(encoding="utf-8")
        _last_updated = datetime.fromtimestamp(
            existing[0].stat().st_mtime
        ).strftime("%Y-%m-%d %H:%M")
        log.info(f"기존 HTML 로드: {existing[0].name}")
    else:
        log.info("기존 HTML 없음 → 최초 생성 시작")
        refresh()


if __name__ == "__main__":
    import uvicorn
    import socket

    # 로컬 IP 출력 (팀원 공유용)
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"\n{'='*50}")
    print(f"  서버 시작!")
    print(f"  내 PC에서:   http://localhost:8000")
    print(f"  팀원 접속:   http://{local_ip}:8000")
    print(f"  매일 08:00 자동 갱신")
    print(f"{'='*50}\n")

    uvicorn.run("server:app", host="0.0.0.0", port=8002, reload=False)
