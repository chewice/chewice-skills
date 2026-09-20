#!/usr/bin/env python3
"""Shared proxy, disk reservations and cancellable child processes for acquisition."""
from __future__ import annotations

import argparse
import contextlib
import csv
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from urllib.parse import urlparse
import uuid
import fcntl

DEFAULTS = {
    "download_workers": "2", "download_connections": "4", "conversion_workers": "1",
    "sra_threads": "8", "compress_threads": "8", "max_same_error_attempts": "3",
    "retry_delays_seconds": "0;30;120", "require_proxy": "true",
    "min_headroom_bytes": str(10 * 1024**3), "storage_check_interval_seconds": "1",
}
ENV_SETTINGS = {
    "GEO_SRA_DOWNLOAD_WORKERS": "download_workers", "GEO_SRA_CONNECTIONS": "download_connections",
    "GEO_SRA_SRA_THREADS": "sra_threads", "GEO_SRA_COMPRESS_THREADS": "compress_threads",
    "GEO_SRA_MAX_ATTEMPTS": "max_same_error_attempts", "GEO_SRA_RETRY_DELAYS": "retry_delays_seconds",
}
_PROXY_KEYS = ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY")
_LOCAL = "localhost,127.0.0.1,::1"
_TOKEN = "GEO_ACQUISITION_RESERVATION_TOKEN"
_PROCESS_TOKEN = "GEO_ACQUISITION_PROCESS_TOKEN"
_controllers: dict[str, "RuntimeSupervisor"] = {}
_controllers_lock = threading.RLock()
_quota_cache = (0.0, None)
_quota_lock = threading.Lock()


class ResourceLimitError(RuntimeError):
    """The configured budget cannot admit or continue this work."""


class RuntimeConfigurationError(RuntimeError):
    """A requested configuration cannot be honored."""


class RuntimeCancelled(RuntimeError):
    def __init__(self, signum=signal.SIGINT):
        self.returncode = 128 + int(signum)
        super().__init__(f"Acquisition cancelled by signal {int(signum)}")


def effective_config(root) -> dict[str, str]:
    config = dict(DEFAULTS)
    path = Path(root) / "metadata/acquisition_config.tsv"
    if path.is_file():
        with path.open(newline="") as handle:
            config.update({row["key"]: row.get("value", "") for row in csv.DictReader(handle, delimiter="\t")})
    for variable, key in ENV_SETTINGS.items():
        if os.environ.get(variable):
            config[key] = os.environ[variable].replace(",", ";") if key == "retry_delays_seconds" else os.environ[variable]
    for key in ("download_workers", "download_connections", "conversion_workers", "sra_threads", "compress_threads", "max_same_error_attempts"):
        if not config[key].isdigit() or int(config[key]) < 1:
            raise RuntimeConfigurationError(f"{key} must be a positive integer")
    for key in ("max_project_bytes", "max_temporary_bytes", "min_headroom_bytes", "user_quota_bytes"):
        if config.get(key) and (not config[key].isdigit() or int(config[key]) < 0):
            raise RuntimeConfigurationError(f"{key} must be a nonnegative integer")
    if config.get("materialize_peak_bytes") and (not config["materialize_peak_bytes"].isdigit() or int(config["materialize_peak_bytes"]) <= 0):
        raise RuntimeConfigurationError("materialize_peak_bytes must be a positive integer")
    if config["require_proxy"] != "true":
        raise RuntimeConfigurationError("require_proxy must remain true; external direct access is not permitted")
    if any(not value.isdigit() for value in config["retry_delays_seconds"].split(";")):
        raise RuntimeConfigurationError("retry_delays_seconds must contain semicolon-separated nonnegative integers")
    try:
        if float(config["storage_check_interval_seconds"]) <= 0:
            raise ValueError
    except ValueError:
        raise RuntimeConfigurationError("storage_check_interval_seconds must be positive") from None
    return config


def _local_url(url):
    host = urlparse(url or "").hostname or ""
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def network_env(root, url=None, env=None, *, proxy=None) -> dict[str, str]:
    """Return an explicit HTTP(S) proxy environment; never inherit broad bypasses."""
    root = Path(root).resolve()
    config = effective_config(root)
    result = dict(os.environ if env is None else env)
    env_file = (result.get("GEO_SRA_PROXY_ENV") or config.get("proxy_env_file")) if proxy is None else None
    if env_file:
        path = Path(env_file).expanduser()
        if not path.is_absolute():
            path = root / path
        if not path.is_file():
            raise RuntimeConfigurationError("Configured proxy environment file is missing")
        file_environment = {key: value for key, value in result.items() if key not in _PROXY_KEYS}
        loaded = subprocess.run(["bash", "-c", 'set -a; source "$1" >/dev/null || exit; env -0', "proxy-env", str(path)],
                                env=file_environment, capture_output=True, check=False)
        if loaded.returncode:
            raise RuntimeConfigurationError("Configured proxy environment file could not be loaded")
        values = dict(entry.split("=", 1) for entry in loaded.stdout.decode().split("\0") if "=" in entry)
        for key in _PROXY_KEYS:
            result.pop(key, None)
        result.update({key: values[key] for key in _PROXY_KEYS if values.get(key)})
    if proxy is not None:
        for key in _PROXY_KEYS:
            result.pop(key, None)
        result.update(http_proxy=proxy, https_proxy=proxy)
    http = result.get("http_proxy") or result.get("HTTP_PROXY")
    https = result.get("https_proxy") or result.get("HTTPS_PROXY")
    for value in (http, https):
        if value:
            try:
                parsed = urlparse(value)
                valid = parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                parsed.port
            except ValueError:
                valid = False
            if not valid:
                raise RuntimeConfigurationError("Configured proxy must use an HTTP(S) URL")
    http, https = http or https, https or http
    if not http and config["require_proxy"] == "true" and not _local_url(url):
        raise RuntimeConfigurationError("External network access requires an explicitly configured HTTP(S) proxy")
    for key in (*_PROXY_KEYS, "all_proxy", "ALL_PROXY", "no_proxy", "NO_PROXY"):
        result.pop(key, None)
    if http:
        result.update(http_proxy=http, HTTP_PROXY=http, https_proxy=https, HTTPS_PROXY=https)
    result.update(no_proxy=_LOCAL, NO_PROXY=_LOCAL)
    return result


def record_effective_config(root, *, proxy=None):
    """Persist only supported settings and proxy endpoints, without credentials."""
    config = effective_config(root)
    values = {key: config[key] for key in (*DEFAULTS, "max_project_bytes", "max_temporary_bytes", "user_quota_bytes", "materialize_peak_bytes") if key in config}
    quota = _quota_remaining()
    values["filesystem_quota_remaining_bytes"] = quota if quota is not None else "unknown"
    env = network_env(root, "http://localhost", proxy=proxy)
    for scheme in ("http", "https"):
        proxy = env.get(f"{scheme}_proxy")
        parsed = urlparse(proxy) if proxy else None
        values[f"{scheme}_proxy_endpoint"] = f"{parsed.scheme}://{parsed.hostname}:{parsed.port or (443 if parsed.scheme == 'https' else 80)}" if parsed else "unconfigured"
    directory = Path(root) / "reports/status"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "acquisition_config.effective.json"
    temporary = directory / f".acquisition_config.{uuid.uuid4().hex}.tmp"
    temporary.write_text(json.dumps(values, sort_keys=True) + "\n")
    os.replace(temporary, target)


class _StrictProxyHandler(urllib.request.ProxyHandler):
    # urllib's default proxy_open consults process-global no_proxy. This handler does not.
    def proxy_open(self, request, proxy, type):
        if _local_url(request.full_url):
            return None
        from urllib.request import _parse_proxy
        import base64
        scheme, user, password, hostport = _parse_proxy(proxy)
        if user and password:
            from urllib.parse import unquote
            credentials = f"{unquote(user)}:{unquote(password)}".encode()
            request.add_header("Proxy-authorization", "Basic " + base64.b64encode(credentials).decode())
        request.set_proxy(hostport, scheme or request.type)
        if request.type == "https" or (scheme or type) == type:
            return None
        return self.parent.open(request, timeout=request.timeout)


class _RedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, root, proxy=None):
        self.root = root
        self.proxy = proxy

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme not in {"http", "https"}:
            raise RuntimeConfigurationError("Only HTTP(S) acquisition redirects are supported")
        network_env(self.root, newurl, proxy=self.proxy)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(root, url, *, timeout=40, headers=None, method=None, proxy=None):
    if urlparse(url).scheme not in {"http", "https"}:
        raise RuntimeConfigurationError("Only HTTP(S) acquisition URLs are supported")
    env = network_env(root, url, proxy=proxy)
    if proxy is not None:
        record_effective_config(root, proxy=proxy)
    proxies = {scheme: env[f"{scheme}_proxy"] for scheme in ("http", "https") if env.get(f"{scheme}_proxy")}
    opener = urllib.request.build_opener(_StrictProxyHandler(proxies), _RedirectHandler(root, proxy))
    return opener.open(urllib.request.Request(url, headers=headers or {}, method=method), timeout=timeout)


def _identity(pid=None):
    pid = os.getpid() if pid is None else pid
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return {"pid": pid, "start_ticks": fields[19], "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}
    except (FileNotFoundError, ProcessLookupError):
        return None


def _alive(identity):
    return bool(identity and _identity(identity["pid"]) == identity)


def _usage(paths):
    """Logical bytes, counting each inode once; never follow directory symlinks."""
    seen, total = set(), 0
    for entry in paths:
        entry = Path(entry)
        files = [entry] if entry.is_file() else (Path(base) / name for base, _, names in os.walk(entry) for name in names)
        for path in files:
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            key = (stat.st_dev, stat.st_ino)
            if key not in seen:
                seen.add(key)
                total += stat.st_size
    return total


@contextlib.contextmanager
def _ledger(root):
    directory = Path(root) / "reports/status"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "acquisition_runtime.json"
    with (directory / "acquisition_runtime.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(path.read_text()) if path.exists() else {"reservations": {}, "processes": {}}
        yield state
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(state, sort_keys=True) + "\n")
        os.replace(temporary, path)


def _members(pgid):
    members = []
    for directory in Path("/proc").iterdir():
        if not directory.name.isdigit():
            continue
        try:
            fields = (directory / "stat").read_text().rsplit(")", 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != "Z":
                members.append(int(directory.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
    return members


def _owned_group(record):
    identity, token = record["identity"], record["token"]
    current = _identity(identity["pid"])
    if current is not None and current != identity:
        return False  # PID reused: never send a signal to this group.
    members = _members(identity["pid"])
    if current == identity:
        return bool(members)
    for pid in members:
        try:
            environment = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
        except (FileNotFoundError, ProcessLookupError):
            continue
        if f"{_PROCESS_TOKEN}={token}".encode() not in environment:
            raise ResourceLimitError("Stale process ownership is uncertain; inspect acquisition_runtime.json before recovery")
    return bool(members)


def _stop_group(record, grace=1.0):
    if not _owned_group(record):
        return
    pgid = record["identity"]["pid"]
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + grace
    while _members(pgid) and time.monotonic() < deadline:
        time.sleep(.03)
    if _owned_group(record):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 2
    while _members(pgid) and time.monotonic() < deadline:
        time.sleep(.03)
    if _members(pgid):
        raise ResourceLimitError("Managed child processes have not stopped; keep their reservation")


def _stop_tree(root, token, record):
    """Nested runtime invocations have their own sessions; reap those before returning."""
    known = {token}
    first_pass = True
    while True:
        with _ledger(root) as state:
            descendants = {}
            changed = True
            while changed:
                changed = False
                for key, child in state["processes"].items():
                    if key not in descendants and (key in known or child.get("parent_token") in known):
                        descendants[key] = child
                        known.add(key)
                        changed = True
        if not descendants and not first_pass:
            return
        descendants.setdefault(token, record)
        first_pass = False
        for key, child in sorted(descendants.items(), key=lambda item: int(item[1]["identity"]["start_ticks"]), reverse=True):
            _stop_group(child)
            with _ledger(root) as state:
                state["processes"].pop(key, None)


def recover_runtime(root):
    """Stop verifiably owned orphan groups before releasing stale reservations."""
    with _ledger(root) as state:
        stale = [(token, record) for token, record in state["processes"].items() if not _alive(record["owner"])]
    for token, record in stale:
        _stop_tree(root, token, record)
        with _ledger(root) as state:
            state["processes"].pop(token, None)
    with _ledger(root) as state:
        for token, record in list(state["reservations"].items()):
            if not _alive(record["owner"]):
                del state["reservations"][token]


def _check_space(root, state=None, extra=None):
    root = Path(root)
    config = effective_config(root)
    current, temporary = _usage([root]), _usage([root / "temporary"])
    headroom = int(config["min_headroom_bytes"])
    pending_project = pending_temporary = 0
    records = list((state or {}).get("reservations", {}).values())
    if extra:
        records.append(extra)
    for record in records:
        pending_project += max(0, record["project_bytes"] - _usage(record["paths"]))
        pending_temporary += max(0, record["temporary_bytes"] - _usage(record["temporary_paths"]))
    checks = [("project", current + pending_project + headroom, config.get("max_project_bytes")),
              ("temporary", temporary + pending_temporary + headroom, config.get("max_temporary_bytes")),
              ("quota", current + pending_project + headroom, config.get("user_quota_bytes")),
              ("filesystem", pending_project + headroom, shutil.disk_usage(root).free)]
    remaining = _quota_remaining()
    if remaining is not None:
        checks.append(("filesystem_quota", pending_project + headroom, remaining))
    for label, needed, limit in checks:
        if limit is not None and limit != "" and needed > int(limit):
            raise ResourceLimitError(f"{label} capacity: needed={needed} limit={limit}")


def _quota_remaining():
    """Short-lived quota snapshots; unavailable/timeout is unknown, never zero."""
    global _quota_cache
    with _quota_lock:
        now = time.monotonic()
        if now - _quota_cache[0] < 1:
            return _quota_cache[1]
        command = shutil.which("quota")
        remaining = []
        if command:
            process = subprocess.Popen([command, "-w", "-v"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, env={**os.environ, "LC_ALL": "C"})
            try:
                output, _ = process.communicate(timeout=2)
                if process.returncode in {0, 1}:
                    for line in output.splitlines():
                        fields = line.split()
                        values = [value.rstrip("*") for value in fields[1:4]]
                        if len(values) == 3 and all(value.isdigit() for value in values):
                            used, soft, hard = map(int, values)
                            limit = min(value for value in (soft, hard) if value > 0) if soft or hard else 0
                            if limit:
                                remaining.append(max(0, limit - used) * 1024)
            except (OSError, subprocess.TimeoutExpired):
                pass
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()
        _quota_cache = (now, min(remaining) if remaining else None)
        return _quota_cache[1]


@contextlib.contextmanager
def _toolkit_environment(root, command, environment, network):
    """Make toolkit proxy-only/offline settings local to one child and verify loading."""
    if Path(str(command[0])).name not in {"prefetch", "vdb-dump", "vdb-validate", "fasterq-dump", "fastq-dump", "sra-stat"}:
        yield environment
        return
    base = Path(root) / "temporary/runtime_config"
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sra-", dir=base) as directory:
        path = Path(directory) / "user-settings.mkfg"
        values = {"/repository/remote/disabled": "false" if network else "true"}
        if network:
            values.update({"/http/proxy/enabled": "true", "/http/proxy/only": "true", "/http/proxy/use": "env"})
        path.write_text("".join(f'{key} = "{value}"\n' for key, value in values.items()))
        isolated = {key: value for key, value in environment.items() if key not in {"NCBI_VDB_CONFIG", "KLIB_CONFIG", "VDB_CONFIG", "VDBCONFIG"}}
        isolated.update(NCBI_HOME=directory, NCBI_SETTINGS=str(path))
        # NCBI config.c loads NCBI_SETTINGS after default configuration; properties.c
        # uses /repository/remote/disabled, and kns/proxy.c honors proxy/only.
        section = "/http/proxy" if network else "/repository/remote"
        try:
            proof = managed_run(root, ["vdb-config", "-p", "-o", "n", section], env=isolated,
                                capture_output=True, text=True, timeout=20)
        except FileNotFoundError:
            raise RuntimeConfigurationError("vdb-config is required to verify isolated SRA network settings") from None
        observed = dict(re.findall(r'^\s*(/[^\s=]+)\s*=\s*"([^"\n]*)"\s*$', proof.stdout, flags=re.MULTILINE))
        required = {key: value for key, value in values.items() if key.startswith(section + "/")}
        if proof.returncode or any(observed.get(key) != value for key, value in required.items()):
            raise RuntimeConfigurationError("SRA Toolkit did not confirm the required isolated proxy/offline settings")
        yield isolated


class ResourceReservation:
    """Reserve peak totals for owned paths; existing cache counts toward those totals."""
    def __init__(self, root, key, project_bytes, temporary_bytes=0, paths=(), temporary_paths=()):
        self.root = Path(root).resolve()
        self.key, self.token = str(key), uuid.uuid4().hex
        self.inherited = False
        def normalize(values, base):
            result = []
            for value in values:
                path = Path(value)
                path = (self.root / path).resolve() if not path.is_absolute() else path.resolve()
                if not path.is_relative_to(base):
                    raise RuntimeConfigurationError("Reservation paths must stay inside their project/storage scope")
                result.append(str(path))
            return result
        if project_bytes < 0 or temporary_bytes < 0 or temporary_bytes > project_bytes:
            raise RuntimeConfigurationError("Reservation requires 0 <= temporary_bytes <= project_bytes")
        self.record = dict(key=self.key, owner=_identity(), project_bytes=int(project_bytes), temporary_bytes=int(temporary_bytes),
                           paths=normalize(paths, self.root), temporary_paths=normalize(temporary_paths, self.root / "temporary"))

    def __enter__(self):
        recover_runtime(self.root)
        with _ledger(self.root) as state:
            inherited = os.environ.get(_TOKEN)
            if inherited in state["reservations"] and _alive(state["reservations"][inherited]["owner"]):
                self.token, self.inherited = inherited, True
                return self
            if any(record["key"] == self.key for record in state["reservations"].values()):
                raise ResourceLimitError(f"Reservation already active: {self.key}")
            _check_space(self.root, state, self.record)
            state["reservations"][self.token] = self.record
        return self

    def check(self):
        with _controllers_lock:
            controller = _controllers.get(str(self.root))
        if controller is not None and controller.cancelled:
            raise RuntimeCancelled(controller.signum)
        with _ledger(self.root) as state:
            _check_space(self.root, state)

    def __exit__(self, exc_type, exc, tb):
        if not self.inherited:
            with _ledger(self.root) as state:
                if any(record.get("reservation_token") == self.token for record in state["processes"].values()):
                    raise ResourceLimitError("Managed writers remain registered; retain their reservation until recovery")
                state["reservations"].pop(self.token, None)


class RuntimeSupervisor:
    """One main-thread cancellation scope for a project's worker threads."""
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.event = threading.Event()
        self.signum = signal.SIGINT
        self.handlers = {}
        self.spawning = False

    @property
    def cancelled(self):
        return self.event.is_set()

    def cancel(self):
        self.event.set()

    def __enter__(self):
        recover_runtime(self.root)
        record_effective_config(self.root)
        with _controllers_lock:
            if str(self.root) in _controllers:
                raise RuntimeConfigurationError("A supervisor is already active for this project")
            _controllers[str(self.root)] = self
        if threading.current_thread() is threading.main_thread():
            def cancel(signum, frame):
                already_cancelled = self.cancelled
                self.signum = signum
                self.cancel()
                if not already_cancelled and not self.spawning:
                    raise RuntimeCancelled(signum)
            for signum in (signal.SIGINT, signal.SIGTERM):
                self.handlers[signum] = signal.signal(signum, cancel)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.cancel()
        try:
            with _ledger(self.root) as state:
                owned = [(token, record) for token, record in state["processes"].items() if record["owner"] == _identity()]
            for token, record in owned:
                _stop_tree(self.root, token, record)
                with _ledger(self.root) as state:
                    state["processes"].pop(token, None)
        finally:
            for signum, handler in self.handlers.items():
                signal.signal(signum, handler)
            with _controllers_lock:
                _controllers.pop(str(self.root), None)


def managed_run(root, command, *, network=False, url=None, env=None, reservation=None,
                check=False, timeout=None, capture_output=False, text=False, cwd=None,
                stdout=None, stderr=None, input=None, pass_fds=(), proxy=None):
    """Run a process group, checking budgets and waiting for all writers on cancellation."""
    root = Path(root).resolve()
    with _controllers_lock:
        controller = _controllers.get(str(root))
    if controller is None:
        with RuntimeSupervisor(root):
            return managed_run(root, command, network=network, url=url, env=env, reservation=reservation,
                               check=check, timeout=timeout, capture_output=capture_output, text=text,
                               cwd=cwd, stdout=stdout, stderr=stderr, input=input, pass_fds=pass_fds, proxy=proxy)
    if controller.cancelled:
        raise RuntimeCancelled(controller.signum)
    environment = dict(os.environ if env is None else env)
    environment["GEO_SRA_PROJECT_ROOT"] = str(root)
    if network:
        environment = network_env(root, url, environment, proxy=proxy)
        if proxy is not None:
            record_effective_config(root, proxy=proxy)
    if reservation is not None:
        environment[_TOKEN] = reservation.token
    if Path(str(command[0])).name in {"prefetch", "vdb-dump", "vdb-validate", "fasterq-dump", "fastq-dump", "sra-stat"}:
        with _toolkit_environment(root, command, environment, network) as isolated:
            return _run_child(root, command, controller, isolated, check, timeout, capture_output,
                              text, cwd, stdout, stderr, input, pass_fds)
    return _run_child(root, command, controller, environment, check, timeout, capture_output,
                      text, cwd, stdout, stderr, input, pass_fds)


def _run_child(root, command, controller, environment, check, timeout, capture_output,
               text, cwd, stdout, stderr, input, pass_fds):
    token = uuid.uuid4().hex
    parent_token = environment.get(_PROCESS_TOKEN)
    environment[_PROCESS_TOKEN] = token
    if capture_output:
        if stdout is not None or stderr is not None:
            raise ValueError("capture_output cannot be combined with stdout/stderr")
        stdout = stderr = subprocess.PIPE
    with _ledger(root) as state:
        _check_space(root, state)
    process = record = None
    defer_signal = threading.current_thread() is threading.main_thread()
    if defer_signal:
        controller.spawning = True
    try:
        process = subprocess.Popen(command, env=environment, cwd=cwd, stdout=stdout, stderr=stderr,
                                   stdin=subprocess.PIPE if input is not None else None, text=text,
                                   start_new_session=True, pass_fds=pass_fds)
        record = {"owner": _identity(), "identity": _identity(process.pid), "token": token,
                  "reservation_token": environment.get(_TOKEN), "parent_token": parent_token}
        with _ledger(root) as state:
            state["processes"][token] = record
        if defer_signal:
            controller.spawning = False
        started = time.monotonic()
        interval = min(1.0, float(effective_config(root)["storage_check_interval_seconds"]))
        first_input = input
        while True:
            if controller.cancelled:
                raise RuntimeCancelled(controller.signum)
            if timeout is not None and time.monotonic() - started >= timeout:
                raise subprocess.TimeoutExpired(command, timeout)
            with _ledger(root) as state:
                _check_space(root, state)
            try:
                output, errors = process.communicate(first_input, timeout=interval)
                break
            except subprocess.TimeoutExpired:
                first_input = None
        # A shell may exit while background children are still writing.
        _stop_tree(root, token, record)
        result = subprocess.CompletedProcess(command, process.returncode, output, errors)
        if check:
            result.check_returncode()
        return result
    finally:
        try:
            if record is not None:
                _stop_tree(root, token, record)
                process.wait()
                with _ledger(root) as state:
                    state["processes"].pop(token, None)
        finally:
            if defer_signal:
                controller.spawning = False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    config_parser = sub.add_parser("config")
    config_parser.add_argument("--root", required=True, type=Path)
    config_parser.add_argument("--key", required=True, choices=tuple(DEFAULTS) + ("max_project_bytes", "max_temporary_bytes"))
    run = sub.add_parser("exec")
    run.add_argument("--root", required=True, type=Path)
    run.add_argument("--network", action="store_true")
    run.add_argument("--url")
    run.add_argument("--proxy")
    run.add_argument("--key")
    run.add_argument("--project-bytes", type=int, default=0)
    run.add_argument("--temporary-bytes", type=int, default=0)
    run.add_argument("--path", action="append", default=[])
    run.add_argument("--temporary-path", action="append", default=[])
    run.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.action == "config":
            print(effective_config(args.root).get(args.key, ""))
            return 0
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        if not command:
            parser.error("exec requires a command after --")
        reservation = ResourceReservation(args.root, args.key, args.project_bytes, args.temporary_bytes,
                                          args.path, args.temporary_path) if args.key else None
        with reservation or contextlib.nullcontext():
            return managed_run(args.root, command, network=args.network, url=args.url, proxy=args.proxy, reservation=reservation).returncode
    except RuntimeCancelled as exc:
        print(str(exc), file=sys.stderr)
        return exc.returncode
    except (ResourceLimitError, RuntimeConfigurationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
