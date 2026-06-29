# Real-World Audit Dataset — v0.1.0b0

**Generated:** 2026-06-03
**File:** `datasets/real_world_audit_domains.txt`
**Total domains:** 100

## Composition

| Category | Count | Examples |
|----------|:-----:|----------|
| Major Public Websites | 12 | google.com, youtube.com, facebook.com, wikipedia.org, reddit.com, twitter.com, linkedin.com, apple.com, microsoft.com, instagram.com, whatsapp.com, cloudflare.com |
| Cloud Providers | 8 | aws.amazon.com, azure.microsoft.com, console.cloud.google.com, digitalocean.com, heroku.com, netlify.com, vercel.com, github.com |
| Government Sites | 8 | whitehouse.gov, fbi.gov, nasa.gov, nih.gov, state.gov, uscis.gov, gsa.gov, data.gov |
| Universities | 10 | mit.edu, stanford.edu, harvard.edu, berkeley.edu, ox.ac.uk, cam.ac.uk, caltech.edu, cmu.edu, princeton.edu, yale.edu |
| News Sites | 10 | cnn.com, nytimes.com, bbc.com, reuters.com, bloomberg.com, theguardian.com, washingtonpost.com, wsj.com, npr.org |
| E-Commerce | 8 | amazon.com, ebay.com, etsy.com, shopify.com, bestbuy.com, walmart.com, alibaba.com, target.com |
| Open-Source Projects | 8 | gitlab.com, python.org, npmjs.com, docker.com, kubernetes.io, rust-lang.org, nodejs.org, apache.org |
| Technology Companies | 10 | stackoverflow.com, adobe.com, oracle.com, ibm.com, salesforce.com, atlassian.com, datadoghq.com, newrelic.com, mongodb.com, elastic.co |
| Small Independent Sites | 10 | news.ycombinator.com, lobste.rs, tilde.club, suckless.org, danluu.com, stroustrup.com, motherfuckingwebsite.com, txti.es, neocities.org |
| TLS Edge Cases | 8 | expired.badssl.com, self-signed.badssl.com, untrusted-root.badssl.com, revoked.badssl.com, dh2048.badssl.com, tls-v1-2.badssl.com, rc4.badssl.com, wrong.host.badssl.com |
| Miscellaneous High-Profile | 8 | paypal.com, dropbox.com, spotify.com, netflix.com, slack.com, zoom.us, notion.so, figma.com |

## Selection Criteria

- **Geographic diversity:** Mostly US-based but includes UK (.uk), global services
- **Sector diversity:** Government, education, commerce, media, technology, open-source
- **Scale diversity:** Global top-10 sites to small personal/independent sites
- **TLS diversity:** Including known-poor and known-misconfigured domains via badssl.com

## Bias Warning

- **US-centric:** Majority of domains are US-based or US-targeting
- **English-language:** No non-English domains
- **Well-maintained bias:** Most major sites maintain modern TLS; the dataset skews toward good TLS hygiene
- **Edge case limitation:** Only 8 known edge cases (badssl.com); no real-world misconfigured production domains were deliberately included

## Known TLS Edge Cases

| Domain | Expected Behavior |
|--------|-------------------|
| expired.badssl.com | EXPIRED_CERT → DENY/REVIEW |
| self-signed.badssl.com | SELF_SIGNED_CERT → DENY/REVIEW |
| untrusted-root.badssl.com | UNTRUSTED_CHAIN → DENY/REVIEW |
| revoked.badssl.com | UNTRUSTED_CHAIN or UNKNOWN → depends on CRL/OCSP support |
| dh2048.badssl.com | Depends on client cipher support |
| tls-v1-2.badssl.com | VALID_TLS (acceptable) |
| rc4.badssl.com | Depends on client cipher support |
| wrong.host.badssl.com | WRONG_HOST_CERT → DENY/REVIEW |
