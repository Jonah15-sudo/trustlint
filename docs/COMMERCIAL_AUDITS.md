# Commercial TLS Audit Reports

`spl-tls-analyze` is an open-source TLS risk analysis tool for developers, DevOps teams, small SaaS companies, and web agencies that need fast, structured visibility into TLS and certificate risks.

The CLI is free and open source.
Commercial audit reports are available for teams that want a clear, client-ready review of their domains without building their own TLS monitoring workflow.

## What This Service Provides

A commercial TLS audit report gives you a practical review of your public HTTPS domains, including:

* Certificate validity and expiry risk
* Expired or invalid certificate detection
* Hostname mismatch detection
* Revoked certificate checks where OCSP data is available
* Deprecated TLS protocol detection
* Weak or risky TLS configuration indicators
* Wildcard certificate visibility
* OCSP stapling availability
* Structured ALLOW / REVIEW / DENY decisions
* Prioritized remediation guidance

This is designed to help teams quickly answer:

> "Which domains are safe, which need review, and which require immediate action?"

## Who It Is For

### Web Agencies

If you manage websites for multiple clients, TLS issues can damage trust quickly. A white-label TLS audit report can be sent to your clients as a value-added security review.

Good fit for:

* Web design agencies
* WordPress agencies
* Shopify / Webflow / custom site agencies
* Freelancers managing client domains
* Managed hosting providers

### SaaS Teams

Small SaaS teams often have multiple public endpoints:

* Main website
* App domain
* API domain
* Documentation domain
* Status page
* Customer-facing subdomains

A TLS audit helps catch certificate and configuration issues before they become outages or customer-facing trust problems.

### DevOps and Security Consultants

Consultants can use the report as a lightweight TLS assessment deliverable for clients, internal reviews, or pre-launch checks.

## What You Receive

Each audit includes:

1. **Executive Summary**
   A non-technical overview of the overall TLS risk posture.

2. **Domain-by-Domain Results**
   Each domain is classified as ALLOW, REVIEW, or DENY.

3. **Risk Breakdown**
   Findings are grouped by severity and category.

4. **Prioritized Fix List**
   The most important issues are listed first.

5. **Technical Evidence**
   TLS version, certificate expiry, classification, and decision reasoning.

6. **Remediation Guidance**
   Clear next steps for developers, hosting teams, or clients.

7. **Optional White-Label Formatting**
   For agencies that want to send the report under their own brand.

## Example Use Cases

* Pre-launch TLS review before a website or SaaS release
* Monthly TLS health checks for client domains
* Security add-on for web agency retainers
* CI/CD guardrail validation
* Certificate expiry and trust-risk review
* Lightweight external TLS posture assessment

## Introductory Pricing

Pricing depends on the number of domains, reporting depth, and whether white-label formatting is required.

| Package            | Best For                         | Includes                              | Starting Price |
| ------------------ | -------------------------------- | ------------------------------------- | -------------: |
| Starter Audit      | Small websites and solo founders | Up to 10 domains, summary report      |            $49 |
| Growth Audit       | SaaS teams and freelancers       | Up to 50 domains, detailed report     |           $149 |
| Agency Audit       | Web agencies                     | Up to 150 domains, white-label report |           $299 |
| Monthly Monitoring | Agencies and recurring checks    | Monthly report, change tracking       | From $99/month |
| Custom Review      | Larger or complex environments   | Custom scope and remediation support  |   Custom quote |

Prices are introductory and may change as the service evolves.

## Important Scope Note

This is a TLS risk assessment and CI guardrail service.
It is not a complete penetration test, compliance certification, or full security audit.

The report focuses on externally visible TLS and certificate configuration signals. It does not test application vulnerabilities, authentication logic, backend security, source code, cloud permissions, or internal infrastructure.

## Responsible Use

Audits are only performed for domains you own, manage, or are authorized to test.

By requesting an audit, you confirm that you have permission to scan the submitted domains.

## Request an Audit

To request a commercial TLS audit report:

* Open a GitHub issue using the "Audit Request" template, or
* Email: [binsalemadam.lang@gmail.com](mailto:binsalemadam.lang@gmail.com)

Please include:

* Number of domains
* Whether this is for your company or client work
* Whether you need white-label formatting
* Preferred report format: Markdown, PDF, or both
* Any deadline or launch date

## Why Use This Instead of a Manual Check?

Manual TLS checks are easy to forget, hard to repeat, and difficult to package for clients.

`spl-tls-analyze` produces structured, repeatable results that can be turned into a clear report, used in CI/CD, or repeated as a monthly review.

The goal is simple:

> Catch TLS and certificate risks before your users, clients, or customers do.
