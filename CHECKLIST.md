# PromptMesh UI redesign checklist

- [x] Inspect the current checkout, working tree, UI, and API request/response shapes.
- [x] Create the task branch `codex/promptmesh-ui-redesign` before editing.
- [x] Replace the old form-first UI with a responsive model experimentation workspace.
- [x] Keep evaluation, comparison, evolution, and test-case flows connected to existing API endpoints.
- [x] Add local run summaries, result export, API state, and explicit fine-tuning scope.
- [x] Document the UI and add a safe launcher on the free project port family 4004/5004/6004.
- [x] Review the rendered UI in a browser at desktop and 480px mobile widths, including mobile navigation and custom-prompt mode.
- [ ] Start the API through `run.sh`; blocked because this environment has no `uvicorn` module (`No module named uvicorn`).
- [x] Commit the reviewed task changes locally on the task branch; no remote push.
