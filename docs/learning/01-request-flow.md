# Learning note 01: From browser to backend

The first implemented request is deliberately small: the browser asks whether the API is healthy.

1. `SystemStatus` in the frontend calls the API URL from configuration.
2. FastAPI matches `/api/v1/health` to the health route.
3. The route returns a Pydantic response model, which defines the public shape.
4. The browser validates the unknown JSON before using it.
5. The UI maps transport state to user language: checking, online, or unavailable.

This exposes four useful boundaries: UI state, HTTP transport, public API contract, and backend runtime. The RAG request will cross the same boundaries, then continue into authorization, retrieval, reranking, and generation.

The health endpoint currently proves process reachability only. Later, readiness will separately report whether required dependencies can serve traffic. Keeping liveness and readiness distinct prevents a temporary database outage from causing a process restart loop.
