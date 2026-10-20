# Windows runtime installation: verified checks and boundaries

## Scope of evidence

A Windows WSL prerequisite installation completed successfully in the observed session. The Linux environment import and Docker Engine installation did not complete before a required reboot. Do not cite this as an end-to-end validated Docker deployment or as a permanent OS compatibility matrix.

## Verified reusable techniques

- Discover the exact Windows edition/build, firmware virtualization, existing runtime commands/distributions, administrator privilege and disk space before choosing an installer. A product's desktop GUI compatibility floor is not necessarily the compatibility floor of its underlying engine; verify current official documentation separately.
- Before executing a downloaded MSI, compare its SHA256 with the official release metadata and verify `Get-AuthenticodeSignature` reports `Valid` with the expected publisher. Do not bypass either check merely because the download succeeded. Use a no-restart installer option and persist a verbose log; inspect the actual process exit code.
- For multiple Windows optional features, iterate names and call `Get-WindowsOptionalFeature -Online -FeatureName $f` separately. This parameter expects one string, not an array. Read back states using `$_.State.ToString()` so numeric enum values are not misinterpreted.
- When invoking PowerShell through Bash, a single-quoted Bash argument protects PowerShell `$variables` from shell expansion. Use native `D:/...` paths for native Windows programs when MSYS path conversion is disabled.
- Redirected WSL command output was UTF-16LE in this session. A reliable diagnostic used `subprocess.run(..., capture_output=True)` followed by `.decode('utf-16-le', errors='replace')`. Select encoding per actual output; do not apply UTF-16LE to unrelated commands.
- For multiline file hashes and image checksum lists, compare in code and assert equality before import/execution. Display both the match outcome and the operation's actual exit code.

## Honest stop and resume boundary

A feature-enablement command can report `RestartNeeded=true` even when a subsequent query says `Enabled`. Those represent configured state versus effective runtime availability. Run a real startup/import probe rather than inferring readiness. If activation needs restart, stop non-destructively, save the completed/unverified distinction and ask for a manual reboot. Do not create unattended continuation tasks or claim container verification has passed.

After restart, rediscover current state before deciding whether an import is needed. Engine readiness still requires client/server checks and a real disposable container operation; registry reachability failures must be distinguished from daemon failures. No engine-install sequence in this reference has been validated by this session.
