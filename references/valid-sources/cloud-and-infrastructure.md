---
doc_kind: reference
canonical_id: valid-sources-cloud-and-infrastructure
purpose: [reference, governance, research]
topics: [valid-sources, cloud, aws, azure, gcp, cloudflare, infrastructure]
advisory_only: true
---

# Authoritative Sources: Cloud and Infrastructure

## Purpose

Defines primary, authoritative documentation portals and API registries for major cloud providers and infrastructure tooling.

## Primary Source Registry

### Amazon Web Services (AWS)
- **Official Documentation Portal**: `https://docs.aws.amazon.com/`
- **AWS CLI Command Reference**: `https://awscli.amazonaws.com/v2/documentation/api/latest/index.html`
- **AWS Architecture Center**: `https://aws.amazon.com/architecture/`
- **AWS Security Bulletins**: `https://aws.amazon.com/security/security-bulletins/`
- **Trust Tier**: Tier 1 (Official Vendor Documentation)

### Microsoft Azure
- **Official Documentation Portal**: `https://learn.microsoft.com/en-us/azure/`
- **Azure CLI Reference**: `https://learn.microsoft.com/en-us/cli/azure/`
- **Azure REST API Specifications**: `https://github.com/Azure/azure-rest-api-specs`
- **Azure Architecture Center**: `https://learn.microsoft.com/en-us/azure/architecture/`
- **Trust Tier**: Tier 1 (Official Vendor Documentation)

### Google Cloud Platform (GCP)
- **Official Documentation Portal**: `https://cloud.google.com/docs`
- **Google Cloud CLI (gcloud) Reference**: `https://cloud.google.com/sdk/gcloud/reference`
- **Google Cloud Architecture Center**: `https://cloud.google.com/architecture`
- **Trust Tier**: Tier 1 (Official Vendor Documentation)

### Cloudflare
- **Official Documentation Portal**: `https://developers.cloudflare.com/`
- **Cloudflare API Documentation**: `https://developers.cloudflare.com/api/`
- **Trust Tier**: Tier 1 (Official Vendor Documentation)

### Infrastructure as Code & Orchestration
- **HashiCorp Terraform / OpenTofu**: `https://developer.hashicorp.com/terraform/docs` / `https://opentofu.org/docs/`
- **Kubernetes Official Documentation**: `https://kubernetes.io/docs/`
- **CNCF Projects Documentation**: `https://www.cncf.io/projects/`
- **Trust Tier**: Tier 1 (Official Project Documentation)

## Operational Usage

When researching cloud configurations, IAM policies, or IaC templates:
1. Always query the official vendor documentation portal first.
2. Cross-check API versions and parameters against official CLI reference manuals.
3. Prohibit referencing unofficial forum tutorials or third-party blog aggregators for normative configurations.
