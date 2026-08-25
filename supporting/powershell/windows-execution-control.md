---
doc_kind: supporting
canonical_id: windows-execution-control
purpose: [process]
topics: [windows, onboarding, powershell]
rag_keywords: [smart-app-control, sac, code-integrity, 3077, 3076, citool, execution-control]
---

# Windows execution-control preflight

Read-only checks for Windows [Smart App Control](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/overview) (SAC) when a required CLI fails to start. Agents run these commands; they do not change SAC, the registry, or Code Integrity policy.

SAC blocks malware, potentially unwanted apps, and unknown unsigned binaries. It allows binaries Microsoft’s app intelligence service predicts are safe, or binaries signed by a CA in the [Microsoft Trusted Root Program](https://learn.microsoft.com/en-us/security/trusted-root-program/). There is no per-app SAC allow-list ([Microsoft Support FAQ](https://support.microsoft.com/windows/smart-app-control-frequently-asked-questions-285ea03d-fa88-4d56-882e-6698afdb7003)).

## MUST NOT

- Do not turn SAC **Off** in Windows Security as the onboarding fix. A workstation that already shows Off is a local fact, not the recommended posture.
- Do not write `VerifiedAndReputablePolicyState` or follow the WinRE/registry test procedure. Microsoft documents that path as [testing-only](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/test-your-app-with-smart-app-control) and notes it can weaken protection.
- Do not dump Code Integrity hashes, policy XML, or full event records. Keep **event ID + file path** only.

## 1. Report SAC mode

Windows 11: **Settings → Privacy & security → Windows Security → App & browser control → Smart App Control**. **On** is enforcement, **Evaluation** is evaluation, **Off** is not running ([overview FAQ](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/overview)).

Read-only registry (same DWORD Microsoft documents for App Control; **get only**):

```powershell
Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy' `
  -Name VerifiedAndReputablePolicyState -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty VerifiedAndReputablePolicyState
```

| Value | Mode |
| --- | --- |
| `0` | Off |
| `1` | Enforcement |
| `2` | Evaluation |

Source: [Application Control for Windows](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/appcontrol). If the value is missing, SAC is not discoverable this way; use Settings.

Optional, elevated only: `citool.exe -lp` (Windows 11 22H2+). Evaluation: Friendly Name `VerifiedAndReputableDesktopEvaluation` and Is Currently Enforced `true`. Enforcement: Friendly Name `VerifiedAndReputableDesktop` and Is Currently Enforced `true` ([test with SAC](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/test-your-app-with-smart-app-control)). If `citool` returns `0x80070005`, skip it. Do not wait on “Press Enter to Continue.”

## 2. If a binary failed, capture the block

Run this only when a tool failed to start or Windows reported an untrusted/blocked app. SAC writes to **Event Viewer → Applications and Services Logs → Microsoft → Windows → CodeIntegrity → Operational**. Event **3076** is evaluation (would have been blocked). Event **3077** is enforcement (was blocked). Details: [App Control event IDs](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/operations/event-id-explanations) and [checking event logs](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/test-your-app-with-smart-app-control).

```powershell
Get-WinEvent -FilterHashtable @{
  LogName = 'Microsoft-Windows-CodeIntegrity/Operational'
  Id      = 3076, 3077
} -MaxEvents 20 -ErrorAction SilentlyContinue | ForEach-Object {
  $xml = [xml]$_.ToXml()
  [pscustomobject]@{
    EventId  = $_.Id
    FilePath = ($xml.Event.EventData.Data | Where-Object Name -eq 'File Name').InnerText
  }
}
```

Record the **EventId** and **FilePath** for the failing executable. The log names the blocked file, not why an installer wizard failed.

## 3. Recovery (keep SAC as-is)

1. **Signed distribution** — Reinstall from the vendor’s signed package (python.org, Node.js, Git for Windows, and the same pattern for other required tools). Unsigned copies in user-local bin directories are the usual miss.
2. **Host-bundled runtime** — Prefer the interpreter or CLI that shipped with the agent host or the vendor installer already on `PATH` ([`../workstation-onboarding.md`](../workstation-onboarding.md)), not an unsigned sidecar `.exe`.
3. **Enterprise allow** — On managed devices, IT can ship an [App Control for Business](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/appcontrol) policy that matches SAC and also trusts line-of-business apps. That is the allow path. SAC itself cannot whitelist one file.

Developers publishing tools: sign with a certificate from a Trusted Root CA ([code signing](https://learn.microsoft.com/en-us/windows-hardware/drivers/install/introduction-to-code-signing)).
