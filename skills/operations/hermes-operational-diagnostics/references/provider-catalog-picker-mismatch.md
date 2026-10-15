# Provider authentication, catalog, and picker mismatches

## Verified case and scope

In a managed Windows Desktop runtime, Nous reported `logged_in: true`. An authenticated live catalog returned both `stepfun/step-5-preview` and `stepfun/step-5-preview:free`. The runtime picker result included only the free variant, alongside its curated selection. The cached curated manifest had an older Step model. This established a catalog/picker discrepancy, not an authentication failure. It did not establish why the ordinary variant was omitted, account entitlement to inference, or a successful session switch.

## Reusable diagnostic sequence

1. Establish the active managed HERMES_HOME and installed runtime; avoid inspecting another profile or global home. Use the runtime's `auth status nous` for a non-secret status check.
2. Inspect documented API or installed function signatures before invocation. Dashboard OpenAPI can reveal `/api/model/options` with profile/refresh options and `/api/model/set` scope. An endpoint applying only to new sessions must not substitute for a current-chat switch. Respect authentication on protected endpoints; never dump or hunt tokens to bypass it.
3. Compare the authenticated live provider list against the picker result, projecting only the target provider and target IDs. Do not print entire catalogs or credentials.
4. A packaged runtime that advertises `__run-script` can execute a small diagnostic script with its own installed imports. This avoids assuming the system Python has Hermes modules. Verify this command and signatures on the installed version first.
5. Installed functions verified in this case:
   - `hermes_cli.auth.get_nous_auth_status_local()`; print only `logged_in`.
   - `resolve_nous_runtime_credentials(timeout_seconds=20)`; keep returned credentials solely in memory and never print them.
   - `fetch_nous_models(inference_base_url=credentials['base_url'], api_key=credentials['api_key'], timeout_seconds=20)`; print matching IDs only.
   - `hermes_cli.model_switch.list_authenticated_providers(current_provider='nous', for_picker=True, max_models=None)`; inspect the row with `slug == 'nous'` and matching model IDs. This may perform network/cache work; it does not switch a session.
   - `parse_model_switch_args('stepfun/step-5-preview --provider nous')` accepted the exact target and provider without global scope. This validates syntax only.
6. If handing off a slash command, label it as an unexecuted command rather than a tested switch. Read back the target session's effective provider/model or wait for its runtime notification before claiming success.

## Communication lesson

Lead with the verified distinction: 'You are logged in; the live catalog contains the model, but the picker does not list that exact variant.' Do not blame the user, suggest reauthentication without evidence, claim tier gating solely from an omission, or claim a refreshed picker has been repaired without reading it back. UI-control failure does not exhaust backend read-only diagnostic paths.
