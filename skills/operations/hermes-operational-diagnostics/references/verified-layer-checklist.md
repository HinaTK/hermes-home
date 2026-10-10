# Verified-layer checklist

Use one row per component and preserve evidence timestamps.

| Layer | Minimum evidence | Result vocabulary |
|---|---|---|
| Desktop UI | process list + crash event if relevant | confirmed healthy / crashed / not verified |
| Runtime/gateway | process + gateway log activity | confirmed healthy / exited / degraded |
| Channel adapter | connected/startup record | connected / disconnected / not verified |
| Inbound delivery | adapter message id + gateway inbound line | confirmed / not verified |
| Model execution | effective provider/model + request result | succeeded / route rejected / timeout |
| Outbound delivery | send line + acknowledgement if available | sent / failed / not verified |
| Memory config | provider + endpoint/account/user, secrets redacted | configured / missing / ambiguous |
| Provider health | direct health endpoint | healthy / unavailable |
| Hermes memory activation | registered + activated log lines | active / inactive / not verified |
| Functional memory | real search/read or safe round trip | passed / failed / not verified |
| Dashboard API | dashboard health endpoint/port | available / unavailable / separate from provider |
| Session persistence | context/compression/SQLite/orphan warnings | clean / degraded / at risk |

## Evidence interpretation

A complete Feishu trace is: adapter receives a message; gateway logs inbound dispatch; model request/result is recorded; gateway logs response ready; platform logs sending response. If the model request returns HTTP 400 because the effective model is unsupported by the effective provider, classify channel transport as working and response generation as failed.

For OpenViking, require all four: config points at `127.0.0.1:1933`, health returns healthy, Hermes logs registration/activation, and semantic search returns known durable context. A standalone health response is insufficient.

## Safe reporting language

- “Confirmed by log: …”
- “Current process/port check shows …”
- “Not verified because no expected traffic was observed …”
- “This proves transport, but not model completion …”
- “This proves direct provider health, but not Dashboard availability …”

Do not turn a missing observation into a durable negative claim.
