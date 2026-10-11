# IP address summary – frontend

Minimal NiceGUI frontend for the backend's `POST /api/v1/ip_address_report` endpoint.

## Run

1. Start the backend (`../backend`), it must listen on `http://127.0.0.1:8000`.
2. Start the frontend:

   ```bash
   uv sync
   uv run python -m app.app
   ```

   Run it as a module from the project root: `uv run app/app.py` would put `app/` on
   `sys.path`, so `app` would resolve to `app/app.py` instead of the package.

3. Open http://localhost:8080.

## Configuration

Environment variables (or a `.env` file), all optional:

| Variable | Default |
|---|---|
| `BACKEND_BASE_URL` | `http://127.0.0.1:8000` |
| `BACKEND_IP_ADDRESS_REPORT_ENDPOINT` | `/api/v1/ip_address_report` |
| `BACKEND_TIMEOUT_SECONDS` | `60` |

## Errors

If the summary cannot be created for any reason, the page shows only a generic
message. The cause (the backend's status and response, or the exception with its
traceback) is logged at ERROR level to the terminal the frontend runs in.

## Tests

```bash
uv run pytest
uv run pytest --cov   # fails below 100% line and branch coverage
```

`tests/` mirrors `app/`: the tests for `app/<package>/<module>.py` are in
`tests/<package>/test_<module>.py`.

The tests never call the real backend: the backend depends on rate-limited
VirusTotal and Gemini APIs.

## Documentation

```bash
uv run pdoc -d google -o docs/api app
```

This generates the HTML reference from the docstrings. Open `docs/api/index.html` to
read it. The generated files are not committed.
