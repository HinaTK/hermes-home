# Isolated unittest for research backends

Use when the suite would otherwise hit AKShare, Eastmoney, Sina, or similar.

## Env

- `PYTHONPATH` = repo root **and** `backend/`
- `AH_HOURLY_REFRESH=0`
- `PYTHONDONTWRITEBYTECODE=1`

## Socket patch

Allow loopback only. A total `connect` block breaks FastAPI `TestClient` on Windows (`socketpair`).

```python
original = socket.socket.connect
def local_only(sock, address):
    if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1", "localhost"):
        return original(sock, address)
    raise RuntimeError("audit: external network disabled")
```

## Mock reports

If `generate_report()` still calls ETF/sector collectors in mock mode, skip or stub that section. Mock is not offline until those collectors are gated.

## Do not claim

Killed `unittest discover` after real upstream retries is not a green suite.
