# Provider-route failures surfaced in Feishu

## Observed diagnostic case (2026-10-22)

A Feishu screenshot showed the generic “The model provider failed after retries” response to an ETF fill confirmation. Correlated gateway logs established:

- 11:20:00–11:20:02: the actual message reached the Feishu adapter and gateway.
- The gateway called local Magpie at `http://127.0.0.1:3425/v1` with model `auto/gpt-6.1-sol`.
- The provider returned HTTP 404, `magpie knows no model "group/auto-gpt-6-1-sol"`, repeatedly through attempt 3/3.
- The current Desktop runtime separately reported provider `custom:aicode-api-gz4399-com`, model `gpt-6.1-sol`.

This established a failed gateway model route, not failed inbound transport. The upstream error advertised alternative identifiers, but no alternative was tested and no configuration repair or end-to-end recovery was performed in this exchange. Those advertised names are not enduring configuration recommendations.

## Reusable diagnostic method

1. Read the screenshot; record the visible time and exact error, without assuming it contains the underlying cause.
2. Read active-profile logs, narrowing to that date/time, then provider exceptions/retry lines. Filter the line list before printing a bounded tail. Preserve the HTTP status, error class, model, and endpoint; remove credentials and account identifiers.
3. Correlate an actual inbound event with the failed request. Compare the failing gateway tuple with the working surface's runtime metadata, rather than assuming all surfaces share configuration.
4. Report established cause and unverified recovery separately. A generic retry notice alone cannot establish whether the cause is routing, rate limiting, authentication, or network failure.

## Follow-up (2026-10-23): model-attribution questions and a retracted misdiagnosis

After recovery, the user asked “现在是GLM在犯蠢吗” (is GLM the one being dumb now). Two lessons:

**Misdiagnosis pattern (observed, then retracted):** comparing the 11:20 failure lines with unrelated 11:38 normal-operation lines and concluding “you switched models but Feishu didn't follow”. The 11:38 lines were simply later turns on the then-current route; the config.yaml mtime (11:36) is not per-surface state, and a `switch_model` log line only proves that one surface switched in place at that moment.

**Correct pattern for “现在” questions:**

- Read the latest `conversation turn:` log line per surface — it records `model=… provider=… platform=…` for each turn — and answer from the newest one. Lead with a small current-state table, then history.
- Routing groups hide attribution: the session ran on `group/smart-split` (a Magpie routing group over glm-5.3 / deepseek-v4.1-flash / kimi-k3 / step-5-preview / gemini-4-argon etc.). Hermes logs record only the group id, so the specific member that answered a given reply cannot be identified from logs. The honest answer is “a routing group answered; member not identifiable” — do not blame or exonerate a named model without per-request evidence (e.g. the response `model` field of a direct API probe).
- Probe pattern: `curl http://127.0.0.1:3425/v1/models` lists 21 live ids, groups and models together — the stale `auto/gpt-6.1-sol` was absent, `group/smart-split` present. Use this to confirm whether an id exists before calling it stale.
- Latency caveat: a direct chat/completions probe through the routing group produced no first token within 60s, and real turns showed 57s–121s per call. Use generous timeouts for probes; one slow probe is not proof of outage.

**Recovery verification without test messages:** the user's own later messages (21:37–21:41, “你现在是什么模型” / “这么怪的吗”, DM and group) each produced an inbound event plus a successful `[Feishu] Sending response` line — end-to-end recovery evidence requiring no probe message. Prefer this whenever post-failure traffic exists.

## Transaction safety

The failing message was a trade confirmation that was later handled through Desktop. Do not resend it to validate Feishu: a retry across surfaces can duplicate a real ledger mutation. Use a harmless greeting for model-response testing and inspect the ledger before any authorized business-action retry.

## Scope

This note captures verified diagnoses and methods only. Discover current supported configuration and live model ids before remediation; do not treat the historical endpoint, aliases, routing groups, or suggested models as fixed defaults.
