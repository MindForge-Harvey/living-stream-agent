"""Run the local MySQL, API and Vite services without affecting other projects."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".local"
PYTHON = ROOT / ".venv/bin/python"
COMPOSE = ["docker", "compose", "-f", "compose.local.yml"]
SERVICES = {
    "backend": (3001, [str(PYTHON), "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "3001"], "/chat/api/health"),
    "frontend": (5172, ["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "5172", "--strictPort"], "/chat/"),
}


def owned_pid(name: str) -> int | None:
    """Only operate on a recorded process whose working directory is this repo."""
    path = STATE / f"{name}.pid"
    if not path.exists():
        return None
    pid = int(path.read_text().strip())
    result = subprocess.run(
        ["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
        capture_output=True, text=True,
    )
    if f"n{ROOT}" in result.stdout.splitlines():
        return pid
    path.unlink(missing_ok=True)
    return None


def stop_service(name: str) -> None:
    """Terminate only a process launched by this script."""
    pid = owned_pid(name)
    if pid:
        os.kill(pid, signal.SIGTERM)
        for _ in range(50):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError(f"{name} 未在 5 秒内退出，请检查 PID {pid}")
    (STATE / f"{name}.pid").unlink(missing_ok=True)


def wait_ready(name: str, process: subprocess.Popen | None = None) -> None:
    """Check HTTP readiness and fail if a newly launched service exits."""
    port, _, path = SERVICES[name]
    for _ in range(60):
        if process is not None and process.poll() is not None:
            break
        try:
            with urlopen(f"http://127.0.0.1:{port}{path}", timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            pass
        time.sleep(0.5)
    log = STATE / f"{name}.log"
    tail = "\n".join(log.read_text(errors="replace").splitlines()[-15:]) if log.exists() else ""
    raise RuntimeError(f"{name} 启动失败；日志：{log}\n{tail}")


def start() -> None:
    """Initialize the local database and start both app processes."""
    if not (ROOT / ".env").is_file():
        raise RuntimeError("缺少 .env，请按 README.md 配置本地环境。")
    for executable in ("docker", "node", "lsof"):
        if not shutil.which(executable):
            raise RuntimeError(f"找不到 {executable}，请安装后重试。")
    if not (ROOT / "node_modules/vite/bin/vite.js").is_file():
        raise RuntimeError("缺少前端依赖，请先运行 npm ci。")

    # Check ports before starting or changing any services.
    for name, (port, _, _) in SERVICES.items():
        if owned_pid(name):
            wait_ready(name)
            continue
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as error:
                raise RuntimeError(f"端口 {port} 已被其他程序占用，未停止任何程序。") from error

    subprocess.run(["docker", "info"], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(COMPOSE + ["up", "-d", "--wait", "--wait-timeout", "180", "mysql"], check=True, cwd=ROOT)
    print("初始化数据库、模板和管理员……", flush=True)
    subprocess.run([str(PYTHON), "-m", "app.core.migrations"], check=True, cwd=ROOT / "backend")
    subprocess.run([str(PYTHON), "init_db.py"], check=True, cwd=ROOT / "backend")

    STATE.mkdir(exist_ok=True)
    launched = []
    try:
        for name, (_, command, _) in SERVICES.items():
            if owned_pid(name):
                continue
            with (STATE / f"{name}.log").open("ab") as log:
                process = subprocess.Popen(
                    command, cwd=ROOT, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                )
            (STATE / f"{name}.pid").write_text(str(process.pid))
            launched.append(name)
            wait_ready(name, process)
    except Exception:
        for name in reversed(launched):
            stop_service(name)
        raise
    print("本地登录：http://127.0.0.1:5172/__local/login")
    print("超级管理：http://127.0.0.1:5172/chat/#/superlogin")
    print("账号：admin；密码见 .env 的 SUPER_ADMIN_INITIAL_PASSWORD")
    print("日志：.local/backend.log、.local/frontend.log；停止：./stop-local")


def stop() -> None:
    """Stop local processes and MySQL while retaining the database volume."""
    for name in reversed(SERVICES):
        stop_service(name)
    subprocess.run(COMPOSE + ["stop", "mysql"], check=True, cwd=ROOT)
    print("本地服务已停止，数据库数据保留。")


if __name__ == "__main__":
    try:
        if len(sys.argv) == 2 and sys.argv[1] in {"start", "stop"}:
            {"start": start, "stop": stop}[sys.argv[1]]()
        else:
            raise RuntimeError("用法：local.py start|stop")
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
