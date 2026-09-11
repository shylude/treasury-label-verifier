# Domain: Threats, Vulnerabilities & Mitigations (22%)

## Exam objectives

- 2.1 Compare and contrast common threat actors and motivations
- 2.2 Explain common threat vectors and attack surfaces
- 2.3 Explain various types of vulnerabilities
- 2.4 Given a scenario, analyze indicators of malicious activity
- 2.5 Explain the purpose of mitigation techniques used to secure the enterprise

## Key concepts

- **Threat actors:** nation-state, unskilled attacker, hacktivist, insider
  threat, organized crime, shadow IT. Attributes: internal vs external,
  resources/funding, sophistication.
- **Motivations:** data exfiltration, espionage, financial gain, disruption,
  extortion, revenge, ethical (hacktivism), war.
- **Threat vectors & attack surfaces:** message-based (email, SMS, IM),
  image, file, voice call, removable media, vulnerable software (client vs
  agentless), unsupported systems, unsecure networks (wireless, wired,
  Bluetooth), open service ports, default credentials, supply chain
  (MSPs, vendors, suppliers), social engineering.
- **Social engineering:** phishing, vishing, smishing, spear phishing,
  whaling, pretexting, business email compromise, watering hole,
  impersonation, pharming, typosquatting, brand impersonation.

## Vulnerability types

- Application: memory injection, buffer overflow, race conditions (TOC/TOU),
  malicious update.
- Web: SQL injection (SQLi), cross-site scripting (XSS).
- OS-based, hardware (firmware, EOL, legacy), virtualization (VM escape,
  resource reuse), cloud-specific, supply chain, cryptographic,
  misconfiguration, mobile (jailbreaking, sideloading), zero-day.

## Indicators of malicious activity

- Malware: ransomware, trojan, worm, spyware, bloatware, virus, keylogger,
  logic bomb, rootkit.
- Attacks: DDoS (amplified, reflected), DNS attacks, on-path (MITM), credential
  replay, malicious code. Password attacks: brute force, spraying.
- Indicators: account lockout, concurrent session usage, impossible travel,
  resource consumption/inaccessibility, out-of-cycle logging, missing logs,
  published/documented, blocked content.

## Mitigation techniques

- Segmentation, access control (ACL, permissions), application allow list,
  isolation/quarantine, patching, encryption, monitoring, least privilege,
  configuration enforcement, decommissioning, hardening (endpoint protection,
  host-based firewall, HIPS, disabling ports/protocols, default password
  changes, removing unnecessary software).

## Key terms & acronyms

| Term | Meaning |
|------|---------|
| SQLi | SQL Injection |
| XSS | Cross-Site Scripting |
| MITM | Man-in-the-Middle (on-path) |
| DDoS | Distributed Denial of Service |
| RAT | Remote Access Trojan |
| TOC/TOU | Time-of-Check / Time-of-Use race condition |
| BEC | Business Email Compromise |
| EOL | End of Life |

## Notes

## Questions I got wrong

_Link to the practice-exam entry and note the correct reasoning._
