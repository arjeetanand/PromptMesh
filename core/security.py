"""Small, process-local controls for the HTTP API's untrusted work."""

from collections import OrderedDict, deque
from datetime import datetime
import threading
import time
import uuid

from starlette.responses import JSONResponse


MAX_REQUEST_BODY_BYTES = 128 * 1024
MAX_PROMPT_CHARS = 16_000
MAX_RENDERED_PROMPT_CHARS = 32_000
MAX_INPUT_CHARS = 4_000
MAX_TEST_INPUTS = 20
MAX_MODELS = 5
MAX_EVOLUTION_INPUTS = 10
MAX_EVOLUTION_ITERATIONS = 3
MAX_OUTPUT_TOKENS = 2_048
MODEL_REQUEST_TIMEOUT_SECONDS = 240
MAX_ACTIVE_JOBS = 4
MAX_ACTIVE_JOBS_PER_CALLER = 2
MAX_RETAINED_JOBS = 100
JOB_RETENTION_SECONDS = 30 * 60
MAX_REQUESTS_PER_MINUTE = 10


class JobLimitError(Exception):
    """Base class for job admission failures."""


class CallerJobLimitError(JobLimitError):
    pass


class ServerJobLimitError(JobLimitError):
    pass


class JobStore:
    """Bound active jobs and retained results, with lazy TTL cleanup."""

    def __init__(
        self,
        *,
        max_active=MAX_ACTIVE_JOBS,
        max_active_per_caller=MAX_ACTIVE_JOBS_PER_CALLER,
        max_retained=MAX_RETAINED_JOBS,
        retention_seconds=JOB_RETENTION_SECONDS,
        clock=time.monotonic,
    ):
        self.max_active = max_active
        self.max_active_per_caller = max_active_per_caller
        self.max_retained = max_retained
        self.retention_seconds = retention_seconds
        self._clock = clock
        self._lock = threading.RLock()
        self._records = {}
        self._owners = {}
        self._active_owners = {}
        self._completed_at = {}

    def _prune_locked(self, now):
        expired = [
            job_id
            for job_id, completed_at in self._completed_at.items()
            if now - completed_at >= self.retention_seconds
        ]
        for job_id in expired:
            self._remove_locked(job_id)

    def _remove_locked(self, job_id):
        self._records.pop(job_id, None)
        self._owners.pop(job_id, None)
        self._active_owners.pop(job_id, None)
        self._completed_at.pop(job_id, None)

    def prune(self):
        with self._lock:
            self._prune_locked(self._clock())

    def _admit_locked(self, owner):
        active_for_owner = sum(
            1 for active_owner in self._active_owners.values() if active_owner == owner
        )
        if active_for_owner >= self.max_active_per_caller:
            raise CallerJobLimitError
        if len(self._active_owners) >= self.max_active:
            raise ServerJobLimitError
        token = str(uuid.uuid4())
        self._active_owners[token] = owner
        return token

    def reserve(self, owner):
        """Reserve a slot for bounded synchronous model work."""
        with self._lock:
            self._prune_locked(self._clock())
            return self._admit_locked(owner)

    def release_work(self, token):
        with self._lock:
            self._active_owners.pop(token, None)

    def create(self, owner):
        now = self._clock()
        with self._lock:
            self._prune_locked(now)
            while len(self._records) >= self.max_retained:
                completed = sorted(self._completed_at, key=self._completed_at.get)
                if not completed:
                    raise ServerJobLimitError
                self._remove_locked(completed[0])

            job_id = self._admit_locked(owner)
            self._records[job_id] = {
                "status": "running",
                "progress": 0,
                "results": None,
                "error": None,
                "started_at": datetime.utcnow().isoformat(),
            }
            self._owners[job_id] = owner
            return job_id

    def update(self, job_id, changes):
        with self._lock:
            record = self._records.get(job_id)
            if record is None:
                return False
            record.update(changes)
            if changes.get("status") in {"completed", "failed"}:
                self._active_owners.pop(job_id, None)
                self._completed_at.setdefault(job_id, self._clock())
            return True

    def finish(self, job_id):
        """Release a slot even if a worker exits before setting a final state."""
        with self._lock:
            record = self._records.get(job_id)
            if record is None:
                return
            if record.get("status") == "running":
                record.update({
                    "status": "failed",
                    "progress": 100,
                    "error": "Job stopped before completion",
                    "completed_at": datetime.utcnow().isoformat(),
                })
            self._active_owners.pop(job_id, None)
            self._completed_at.setdefault(job_id, self._clock())

    def get(self, job_id, owner):
        with self._lock:
            self._prune_locked(self._clock())
            if self._owners.get(job_id) != owner:
                return None
            record = self._records.get(job_id)
            return dict(record) if record is not None else None


class RequestRateLimiter:
    """A bounded sliding-window limiter keyed by a server-derived caller ID."""

    def __init__(self, *, limit, window_seconds=60, max_callers=4096, clock=time.monotonic):
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_callers = max_callers
        self._clock = clock
        self._lock = threading.Lock()
        self._requests = OrderedDict()

    def allow(self, caller):
        now = self._clock()
        cutoff = now - self.window_seconds
        with self._lock:
            requests = self._requests.get(caller, deque())
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if not requests:
                self._requests.pop(caller, None)
                requests = deque()
            if len(requests) >= self.limit:
                self._requests[caller] = requests
                self._requests.move_to_end(caller)
                return False
            requests.append(now)
            self._requests[caller] = requests
            self._requests.move_to_end(caller)

            while self._requests and not self._requests[next(iter(self._requests))]:
                self._requests.popitem(last=False)
            while len(self._requests) > self.max_callers:
                self._requests.popitem(last=False)
            return True


class RequestBodyLimitMiddleware:
    """Reject oversized API bodies before JSON parsing or model work starts."""

    def __init__(self, app, max_bytes=MAX_REQUEST_BODY_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or not scope.get("path", "").startswith("/api/"):
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    await JSONResponse(
                        {"detail": "Request body is too large"}, status_code=413
                    )(scope, receive, send)
                    return
            except ValueError:
                pass

        received = 0
        response_started = False

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _RequestBodyTooLarge
            return message

        async def tracked_send(message):
            nonlocal response_started
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _RequestBodyTooLarge:
            if not response_started:
                await JSONResponse(
                    {"detail": "Request body is too large"}, status_code=413
                )(scope, receive, send)


class _RequestBodyTooLarge(Exception):
    pass
