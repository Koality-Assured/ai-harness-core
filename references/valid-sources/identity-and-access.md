---
doc_kind: reference
canonical_id: valid-sources-identity-and-access
purpose: [reference, governance, research]
topics: [valid-sources, identity, iam, sso, mfa, oauth, oidc, saml, entra, okta]
advisory_only: true
---

# Authoritative Sources: Identity and Access Management

## Purpose

Defines primary, authoritative documentation portals, specifications, and RFCs for identity providers, authentication protocols, and access management.

## Primary Source Registry

### Microsoft Entra ID (Azure AD)
- **Microsoft Entra Documentation**: `https://learn.microsoft.com/en-us/entra/`
- **Microsoft Identity Platform (OAuth/OIDC)**: `https://learn.microsoft.com/en-us/entra/identity-platform/`
- **Microsoft Graph API Reference**: `https://learn.microsoft.com/en-us/graph/api/overview`
- **Trust Tier**: Tier 1 (Official Vendor Documentation)

### Okta
- **Okta Developer Portal**: `https://developer.okta.com/docs/`
- **Okta Product Documentation**: `https://help.okta.com/`
- **Trust Tier**: Tier 1 (Official Vendor Documentation)

### Internet Engineering Task Force (IETF) Standards & RFCs
- **OAuth 2.0 Authorization Framework (RFC 6749)**: `https://datatracker.ietf.org/doc/html/rfc6749`
- **OAuth 2.0 Threat Model and Security Considerations (RFC 6819)**: `https://datatracker.ietf.org/doc/html/rfc6819`
- **OAuth 2.0 Security Best Current Practice (BCP 212 / RFC 9700)**: `https://datatracker.ietf.org/doc/html/rfc9700`
- **OpenID Connect Core 1.0**: `https://openid.net/specs/openid-connect-core-1_0.html`
- **OASIS SAML 2.0 Technical Overview**: `https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-tech-overview-2.0.html`
- **Trust Tier**: Tier 1 (Standards Body / RFCs)

## Operational Usage

When designing authentication flows, SAML SSO configurations, or SCIM provisioning:
1. Always base protocol requirements on official IETF RFCs or OASIS specifications.
2. Ground identity provider configuration steps in Microsoft Entra or Okta official documentation.
3. Prohibit relying on deprecated auth mechanisms (e.g. implicit grant without PKCE) or unverified blog implementations.
