# Dogfood Feedback Template

Use this template to record operator feedback after running `spl-tls-analyze`
against the dogfood dataset (`datasets/dogfood_domains.txt`).

---

## 1. Domain: [domain name]

### Was the final decision clear?
[Yes / No / Partially — explain]

### Was the recommended action specific enough?
[Yes / No — what would be more actionable?]

### Was the reason understandable?
[Yes / No — was the primary reason helpful?]

### Were limitations visible?
[Yes / No — did you see the [Limitations] section when it applied?]

### Was REVIEW overused?
[Yes / No — was too much flagged for manual review?]

### Was DENY justified?
[Yes / No / N/A — was the DENY decision appropriate?]

---

## 2. Domain: [domain name]

### Was the final decision clear?

### Was the recommended action specific enough?

### Was the reason understandable?

### Were limitations visible?

### Was REVIEW overused?

### Was DENY justified?

---

(Repeat for each domain or group of similar domains.)

---

## Overall Assessment

### Did the Markdown report help?
[Yes / No — was the executive summary useful? Were the tables clear?]

### Did the JSON output contain enough information?
[Yes / No — what field(s) were missing or unclear?]

### Was the batch summary useful?
[Yes / No — did the counts and lists help prioritize?]

### Would you trust this for local advisory use?
[Yes / No / With caveats — what would need to change?]

### What would block production use?
[List specific blockers — e.g., no SPL integration, no OCSP, no multi-IP]

### Which profile seems best?
[conservative / balanced / strict — and why?]

### Was the exit code useful?
[Yes / No — did exit code 1 (REVIEW) feel right? Did exit code 2 (DENY) clearly signal action needed?]

### Any surprising or confusing outputs?
[Describe]

### Any known false positives or false negatives?
[Describe]

### What should change before any VPS/API work?
[Describe]

### What must NOT change?
[Describe — e.g., SPL Core isolation, no production readiness claim, local-only scope]
