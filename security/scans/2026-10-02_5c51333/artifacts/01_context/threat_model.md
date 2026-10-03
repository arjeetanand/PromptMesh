# Threat Model — PromptMesh

## Scope
PromptMesh is a FastAPI service for comparing and evolving prompts. The browser submits evaluation, comparison, evolution, and test-case jobs; the server loads prompt definitions, renders Jinja templates, calls configured model adapters, stores job state in process memory, and returns results to the browser. The target is the complete tracked repository at commit 5c51333fe4cbfc3f2ac5b3271ad3766ffc68e8ab (50 tracked files). The direct server entry point binds to 0.0.0.0.

## Assets
- Integrity and confidentiality of prompt templates and prompt evaluation inputs/results.
- Host process integrity and any files or credentials reachable to the Python process.
- Configured model-provider credentials, quota, and cost (OCI, Cohere, and local Ollama integrations are present; active credentials are unknown).
- API availability and retained in-memory job/result state.
- Integrity of browser-rendered evaluation/evolution output.

## Trust boundaries
- Unauthenticated HTTP clients to FastAPI: routes accept job and prompt requests without authentication or authorization.
- Client-controlled prompt text to Jinja: evaluation and evolution accept custom prompt strings and pass them to the shared render_prompt helper.
- Client-controlled task/version identifiers to the prompt registry: the registry forms filesystem paths from these values and loads YAML.
- FastAPI to model adapters: request-selected model names can invoke configured local or cloud-backed providers.
- Job results to browser DOM: serialized evaluation and evolution data is inserted into innerHTML.

## Attacker capabilities
A network caller able to reach the service can submit JSON requests, select model names and inputs, provide custom prompts, select task/version values, and poll the returned job ID. The application code contains no route authentication and its direct entry point listens on all interfaces. Whether a deployed service is currently reachable from the Internet and which provider credentials are configured are unknown.

## Security objectives
- Treat client prompt text as data, never executable server-side template source.
- Confine prompt-file reads to the prompt version directory.
- Bound unauthenticated access to model calls, CPU, memory, and retained job state.
- Render untrusted prompt and model output as text in the browser.

## Assumptions and limits
- This is a static review of the immutable target revision; no live deployment or runtime credentials were inspected.
- The repository contains model adapters for OCI, Cohere, and Ollama, but whether any credentialed provider is enabled in production is unknown.
- The initial review did not execute a crafted request against any live service.
- The repository itself is public; that does not establish that the FastAPI service is deployed publicly.

Repository: https://github.com/arjeetanand/PromptMesh
Version: 5c51333fe4cbfc3f2ac5b3271ad3766ffc68e8ab