# Hands-on Labs

Practical exercises that reinforce the exam objectives. Do these in a
disposable VM environment (VirtualBox/VMware with Kali Linux + a target VM).
Only test against systems you own or are explicitly authorized to test.

## Lab ideas mapped to domains

| Lab | Skill | Domain |
|-----|-------|--------|
| Capture and inspect traffic in Wireshark | Protocol analysis, TLS vs cleartext | 4 |
| Host discovery and port scan with `nmap` | Reconnaissance, service enumeration | 2, 4 |
| Hash files and verify integrity (`sha256sum`) | Integrity, cryptography | 1 |
| Symmetric vs asymmetric encryption with OpenSSL | Cryptography | 1 |
| Read and correlate auth logs (`/var/log/auth.log`) | Logging, IoC detection | 4 |
| Configure a host firewall (`ufw` / `iptables`) | Hardening | 3, 4 |
| Crack a weak password hash in a lab (`john`, `hashcat`) | Password attacks | 2 |
| Set up MFA / TOTP on a test account | IAM | 4 |

Each lab gets its own subfolder with a short write-up: goal, steps, what you
observed, and how it maps to an exam objective.
