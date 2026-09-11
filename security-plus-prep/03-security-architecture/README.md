# Domain: Security Architecture (18%)

## Exam objectives

- 3.1 Compare and contrast security implications of different architecture models
- 3.2 Given a scenario, apply security principles to secure enterprise infrastructure
- 3.3 Compare and contrast concepts and strategies to protect data
- 3.4 Explain the importance of resilience and recovery in security architecture

## Key concepts

- **Architecture models:** on-premises, cloud (responsibility matrix,
  hybrid considerations, third-party vendors), IaaS/PaaS/SaaS, serverless,
  microservices, network infrastructure (physical isolation/air-gapped,
  logical segmentation, SDN), IoT, ICS/SCADA, RTOS, embedded systems,
  high availability. Trade-offs: cost, scalability, resilience,
  responsiveness, power, compute, patch availability.
- **Infrastructure considerations:** device placement, security zones,
  attack surface, connectivity, failure modes (fail-open vs fail-closed),
  device attributes (active vs passive, inline vs tap/monitor).
- **Secure devices:** firewall (WAF, NGFW, UTM), IDS/IPS, load balancer,
  proxy, sensors, jump server.
- **Secure communication/access:** VPN, IPSec (tunnel vs transport), TLS,
  SD-WAN, SASE, remote access, tunneling.
- **Selection of controls:** appropriate to the environment and data.

## Data protection

- **Data types:** regulated, trade secret, intellectual property, legal,
  financial, human/non-human readable.
- **Data classifications:** sensitive, confidential, public, restricted,
  private, critical.
- **Data states:** at rest, in transit, in use.
- **Methods:** geographic restrictions, encryption, hashing, masking,
  tokenization, obfuscation, segmentation, permission restrictions.
- **DLP:** data loss prevention. Data sovereignty.

## Resilience & recovery

- High availability (load balancing vs clustering), site considerations
  (hot, warm, cold, geographic dispersion).
- Platform diversity, multi-cloud, continuity of operations (COOP).
- Capacity planning (people, technology, infrastructure).
- Testing: tabletop exercises, failover, simulation, parallel processing.
- Backups: onsite/offsite, frequency, encryption, snapshots, recovery,
  replication, journaling. Power: generators, UPS.

## Key terms & acronyms

| Term | Meaning |
|------|---------|
| WAF | Web Application Firewall |
| NGFW | Next-Generation Firewall |
| UTM | Unified Threat Management |
| IDS/IPS | Intrusion Detection/Prevention System |
| SASE | Secure Access Service Edge |
| SD-WAN | Software-Defined Wide Area Network |
| DLP | Data Loss Prevention |
| COOP | Continuity of Operations Planning |
| UPS | Uninterruptible Power Supply |

## Notes

## Questions I got wrong

_Link to the practice-exam entry and note the correct reasoning._
