# Feishu monitor: log-rotation false alarm

## Observed cause
The monitor emitted `no recent feishu connection in any log` every five minutes. It searched only the last 100 lines of active gateway/agent logs for the startup string `feishu connected`. That marker had rotated into agent.log.1, while the active log still contained group-message activity. The nonzero exit made cron generate failure notifications; an instruction in the prompt to notify only on real problems could not prevent this in no_agent script mode.

## Validated repair pattern
1. Identify the screenshot's exact cron job using list. Change that job's `deliver` to `local`; read it back. Leave unrelated grid alerts untouched.
2. RED: temporary logs containing group activity but no startup marker must not be classified as disconnected. A second fixture with neither marker nor activity must produce an explicit unknown result rather than a proven failure. Both tests failed against the old script.
3. GREEN: remove the last-100-lines connection-marker requirement. Activity is advisory evidence; absent evidence is unknown/nonfatal. Keep process/config checks independent. This does not implement a transport liveness probe.
4. Test both the tracked source and the deployed script. In the observed repair, two regression tests passed; deployed execution returned code 0 with empty stdout and stderr. These establish absence of the reproduced false alarm, not end-to-end Feishu delivery health.
5. Commit only the task's code/tests and push; do not include unrelated dirty backtest files. Read back cron delivery after modification.

## Boundaries
- Do not auto-change group policy/mention settings because logs are quiet.
- Local delivery suppression applies to the offending monitor, not all Feishu notifications.
- Never dump raw provider connection lines: WebSocket URLs may contain access keys/tickets. Extract counts or redact values before display.
- In no_agent cron, empty stdout means silence on success; nonzero exits may generate scheduler error messages. Routing to local is the durable channel-level boundary requested here.
