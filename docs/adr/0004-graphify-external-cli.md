# ADR-004: Graphify as an external CLI

**Status:** Accepted.

**Context:** Knowledge-graph extraction is a complex problem. There is an existing open-source CLI ([graphifyy](https://pypi.org/project/graphifyy/)) that does it well.

**Decision:** Invoke `graphifyy` as a subprocess from the API via `asyncio.create_subprocess_exec`. The tool is installed as a system-level `uv tool`, **not** as a Python package dependency.

**Consequences:** (+) No need to maintain extraction code. (−) Subprocess startup is slow (~5-10s). (−) Requires `uv` and the `graphifyy` tool in the runtime image. (−) Long-running (1h) subprocess inside a request handler is fragile on platforms with HTTP timeouts.
