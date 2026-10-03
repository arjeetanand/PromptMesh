# Remediation report

This archived scan describes the pre-fix repository revision
`5c51333fe4cbfc3f2ac5b3271ad3766ffc68e8ab`. The original scan files in this
directory are retained as received; this report records the fixes made on top
of that revision.

## Findings and fixes

| Original finding | Fix |
| --- | --- |
| Caller-controlled prompt templates reached unsandboxed Jinja rendering. | Replaced Jinja execution with interpolation for simple identifier placeholders such as `{{text}}`. Expressions, filters, calls, control blocks, comments, unmatched braces, and oversized rendered prompts are rejected. Removed the Jinja dependency. |
| Unauthenticated callers could submit unbounded model work and retain results. | Remote API access requires a 32-character-or-longer `PROMPTMESH_API_KEY`; without a key, API work is restricted to loopback. Added exact-origin CORS and cross-site checks, body and input bounds, per-caller request and active-work limits, a server-wide active-work cap, bounded job retention and expiry, model-call timeouts, and bounded output-token limits. Test-case generation now runs in a worker thread under the same work cap. The empty-input variation path now exits rather than looping. |
| Task/version values could escape the prompt registry directory. | Validate task and version identifiers before cache lookup or file access, resolve and check paths remain under the registry root, and apply the same validation to version listing. |

## Verification

`python3 -m unittest discover -s tests -p 'test_security*.py' -v` passed all
18 focused security tests. These cover simple placeholder behavior, rejection
of template execution syntax and path traversal, symlink escape rejection,
request/body/work limits, API access controls, test-case worker dispatch, and
the empty-input fallback. A source compilation check passed for the changed
Python modules, and `git diff --check` passed.

No live service or model-provider request was used. Provider behavior is covered
through boundary stubs, so deployment-specific authentication, installed SDK
versions, and external provider availability were not validated here. The
rate, active-work, and job-retention limits are process-local and should be
combined with deployment controls when running multiple application workers.

## Archived scan integrity note

The source scan bundle was copied byte-for-byte and its `findings.json` and
`coverage.json` digests match the archived manifest. The manifest's
`preservedSources` digests do not match the actual bytes for the checkpoint
files beginning `44f1826d` and `64f69f0a`; the third checkpoint digest matches.
The original manifest and checkpoint files remain unchanged so the scan record
is preserved exactly.
