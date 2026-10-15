# Feishu Policy Drift — Silent Configuration Regression

## Failure mode

`.env` settings can change between gateway restarts without any visible error. The result is **partial silence**: DM still works, group chat stops responding. The user sees "hi" getting a reply in DM but "@bot hi" or plain group messages getting nothing — and assumes their own configuration is wrong.

## Key env vars that can drift

| Variable | Safe value | Effect of drift | Symptom |
|---|---|---|---|
| `FEISHU_GROUP_POLICY` | `open` | `disabled` → group messages silently dropped | Group chat dead, DM alive |
| `FEISHU_REQUIRE_MENTION` | `false` | `true` → only @-mentions trigger response | Group "hi" ignored, "@bot hi" works |

## Diagnostic procedure

When group chat stops responding but DM works:

1. **Check `.env` directly** — do not rely on the onboarding diagnosis JSON snapshot, which may be stale:
   
   grep FEISHU_GROUP_POLICY FEISHU_REQUIRE_MENTION "$HERMES_HOME/.env"

2. **Check gateway log for group activity** — if the last `feishu:group` entry is hours old while `feishu:dm` entries are recent, the policy is the likely cause:
   
   grep "feishu:group" "$HERMES_HOME/logs/gateway.log" | tail -5

3. **Check channel directory** — confirm the group channel is still registered:
   
   cat "$HERMES_HOME/channel_directory.json"

## Fix

```bash
sed -i 's/FEISHU_GROUP_POLICY=.*/FEISHU_GROUP_POLICY=open/' "$HERMES_HOME/.env"
sed -i 's/FEISHU_REQUIRE_MENTION=.*/FEISHU_REQUIRE_MENTION=false/' "$HERMES_HOME/.env"
```

Then restart the gateway. No credential rotation needed — this is a config issue, not a platform problem.

## Prevention

Deploy a periodic health check script that validates these env vars, gateway process liveness, and recent feishu log activity. See `scripts/feishu_health_check.py` for a ready-to-use implementation. Run it via cron every 5 minutes in `no_agent` mode — it stays silent when healthy and alerts only on failure.

## PID file race (related restart failure)

When restarting the gateway, a stale `gateway-runtime/gateway.pid` pointing to a dead process can cause the new instance to exit immediately:


ERROR gateway.run: PID file race lost to another gateway instance. Exiting.


**Fix:** delete the stale PID file before restart:

```bash
rm -f "$HERMES_HOME/../gateway-runtime/gateway.pid"
```

This file lives outside `HERMES_HOME` (sibling `gateway-runtime/` directory), so it survives Hermes profile switches and must be cleaned manually.
