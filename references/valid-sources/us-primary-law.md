---
doc_kind: reference
canonical_id: valid-sources-us-primary-law
purpose: [reference]
topics: [valid-sources, us-law, federal]
advisory_only: true
---

# Authoritative sources: United States primary law

## Purpose

Tier 1 publishers for federal primary law. State, DC, and territorial hosts are Tier 1 only when that jurisdiction's page in `references/us-law/states/` marks them `official-primary` after an HTTP check. This page does not pre-approve every state domain.

Checked from this workstation on 2026-10-07 unless noted.

## Federal publishers

| Publisher | URL | HTTP | Use |
| --- | --- | --- | --- |
| GovInfo USC | `https://www.govinfo.gov/app/collection/uscode` | 200 | Working United States Code publisher for this capture |
| Office of the Law Revision Counsel | `https://uscode.house.gov/` | 200 maintenance page | Issuing office. The body was a House.gov maintenance notice, not the Code. Do not cite this URL as a fetched title list. |
| GovInfo public laws | `https://www.govinfo.gov/app/collection/plaw` | 200 | Enacted bills as public laws |
| eCFR | `https://www.ecfr.gov/` | 200 | Current federal regulations |
| GovInfo CFR | `https://www.govinfo.gov/app/collection/cfr` | 200 | Annual CFR editions |
| Federal Register | `https://www.federalregister.gov/` | 200 | Daily register, including executive orders |
| Executive orders index | `https://www.federalregister.gov/presidential-documents/executive-orders` | 200 | Executive order collection |
| National Archives | `https://www.archives.gov/founding-docs/constitution` | 200 | Constitution text |
| Supreme Court opinions | `https://www.supremecourt.gov/opinions/opinions.aspx` | 200 | Stable opinions index |
| Slip opinions, October Term path `25` | `https://www.supremecourt.gov/opinions/slipopinion/25` | 200 | Term-specific slip path, not a permanent title |
| U.S. Courts rules | `https://www.uscourts.gov/forms-rules/current-rules-practice-procedure` | 200 | Federal rules of practice |
| PACER | `https://pacer.uscourts.gov/` | 200 | Official federal dockets. Fee-based. Do not scrape. |
| OLC | `https://www.justice.gov/olc` | 200 | Executive legal advice. Not a statute and not a holding. |
| Sentencing Commission | `https://www.ussc.gov/guidelines` | 200 | Federal sentencing guidelines |
| Bureau of Indian Affairs | `https://www.bia.gov/` | 200 | Federal agency. Not a tribal code. |

## Unofficial or blocked

| Host | Result on 2026-10-07 | Rank |
| --- | --- | --- |
| Cornell LII `https://www.law.cornell.edu/uscode/text` | HTTP 200 | Unofficial reading copy of the USC. Does not outrank GovInfo. |
| Congress.gov `https://www.congress.gov/` | HTTP 403 from this workstation | Official Library of Congress bill system, but this capture did not verify a 200. Use GovInfo public laws for enacted text until a fetch succeeds. |

## State extension

Do not add a state domain to `catalogs/authoritative-domains.json` until `references/us-law/catalogs/states/<postal>.json` records an HTTP status for it. The legal router reads the state page, not this federal list, for state law.

## Trust tier

Tier 1 in [`catalogs/authoritative-domains.json`](./catalogs/authoritative-domains.json) under category `us-primary-law`. `uscode.house.gov` stays on that list as the issuing office. This capture's working Code text is GovInfo, because the OLRC host returned a maintenance page. Cornell LII is omitted from that allowlist on purpose.
