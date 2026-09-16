# Crakbit Browser Wallet Threat Model

**Scope:** v0.15/v0.16 browser wallet and public gateway. This is a security design document, not an audit report.

The Crakbit browser wallet is intended for research/public-testnet use. It is not an audited hardware wallet and must not be represented as safe custody software for real value.

## Assets to protect

- Ed25519 private wallet key material,
- encrypted local wallet vault,
- vault password,
- transaction intent before signing,
- selected network/chain ID,
- destination address, amount, fee, nonce and memo,
- integrity of the JavaScript/HTML/CSS served to the browser.

## Trust boundaries

### Browser wallet

Wallet generation and transaction signing are performed in the browser. The private key is expected to remain in browser memory and an encrypted local vault/backup rather than being submitted to the public gateway.

### Public gateway

The gateway is not a wallet custodian. It receives signed transaction objects and public addresses. A compromised gateway can censor, delay or misrepresent read-only network data, but it should not possess the wallet private key.

### Origin / hosting infrastructure

The origin that serves the wallet is highly trusted. If an attacker can replace `app.js`, inject JavaScript or alter the wallet page, the attacker can potentially steal an unlocked private key or change transaction intent before signing.

### Endpoint device and browser

The operating system, browser process, installed extensions, clipboard, screen and local user account are outside the wallet application's complete control.

## Main threats

### 1. Cross-site scripting / injected JavaScript

**Impact:** critical. Injected code running in the wallet origin can access wallet state while unlocked, alter destination/amount or exfiltrate key material.

Current mitigations:

- v0.16 gateway applies a restrictive same-origin Content-Security-Policy,
- scripts/styles are served as local static assets,
- object embedding and framing are disabled,
- same-origin opener/resource policies are set,
- API responses use no-store caching.

Remaining requirements:

- independent review of every DOM write and untrusted-value rendering path,
- keep wallet dependencies minimal and pinned,
- use reproducible/static asset hashes for release builds,
- penetration testing before production-value use.

### 2. Compromised wallet origin / release artifact

**Impact:** critical. A malicious server or compromised release can serve wallet code that steals keys.

Required production controls:

- signed/reproducible wallet releases,
- restricted deployment access,
- immutable build artifacts,
- TLS and secure-header verification,
- independent release verification,
- incident process for origin compromise.

A CSP does not protect against intentionally malicious same-origin JavaScript.

### 3. Malicious browser extension

**Impact:** critical/high. A sufficiently privileged extension may read or alter page content, intercept input, access clipboard data or observe unlocked wallet material.

Mitigation expectations:

- advise use of a clean browser profile for sensitive operations,
- keep wallet unlocked only as long as needed,
- provide hardware/external-signer support before high-value use,
- never claim browser cryptography prevents privileged endpoint compromise.

### 4. Local storage theft

The local wallet vault is encrypted with PBKDF2-SHA256-derived key material and AES-GCM. An attacker who steals the encrypted vault can perform offline password guessing.

Mitigations:

- require a strong user password,
- use a unique random salt and authenticated encryption,
- never store plaintext private key material persistently,
- provide explicit lock/forget controls,
- encourage an offline encrypted backup.

Remaining review item: calibrate PBKDF2 work factor for supported clients and consider a memory-hard KDF in a future wallet-format version after compatibility/security review.

### 5. Phishing / wrong network

A user may be tricked into using a fake Crakbit site, fake gateway or wrong network.

Required UX before production:

- prominently show chain/network identity,
- make address, amount and fee visible before signing,
- show a human-checkable transaction confirmation screen,
- publish canonical official URLs and release fingerprints,
- warn when chain ID/network differs from expected production settings.

### 6. Clipboard/address substitution

Malware can replace copied addresses.

Required UX:

- display the full recipient or a strong human-verification flow before signing,
- avoid silently signing immediately after paste,
- add address-book/contact labeling only with clear provenance and edit controls.

### 7. Gateway lies about balances/nonces/history

The public gateway can provide stale or false read data if compromised. The signed transaction itself includes chain ID, sender, recipient, amount, fee and nonce; however a false nonce can cause failed transactions or denial of service.

Future hardening:

- support multiple RPC/gateway sources,
- expose independently verifiable block/app commitments,
- allow advanced users to choose a trusted endpoint,
- use indexed explorer reconciliation against consensus/application state.

### 8. Transaction mutation in transit

The gateway cannot change a signed transaction without invalidating the Ed25519 signature because the signature covers the canonical unsigned transaction data. The user must still verify that the browser signed the intended fields before the private-key operation.

### 9. Weak randomness

Wallet creation relies on browser cryptographic randomness. Production review must verify that only `crypto.getRandomValues` / WebCrypto-backed secure randomness is used and that no insecure fallback exists.

### 10. Backup loss / forgotten password

The service cannot recover a non-custodial private key if the user loses the encrypted backup/password. This is an availability risk, not something the gateway should solve by collecting private keys.

## Wallet operating rules

1. Never send private keys or decrypted vault material to the gateway.
2. Never reuse validator, faucet, mining-reward, TLS or release-signing keys as user wallets.
3. Lock the wallet when not signing.
4. Keep an encrypted backup outside the browser profile.
5. Do not use the alpha wallet for real-value custody.
6. Do not ask users to paste private keys into support chats.

## Production review checklist

Before high-value/mainnet use:

- [ ] Independent review of browser key generation and Ed25519 encoding
- [ ] Independent review of canonical transaction signing compatibility
- [ ] Independent review of PBKDF2/AES-GCM vault format and parameters
- [ ] XSS/DOM security review
- [ ] Strict CSP verified in deployed production origin
- [ ] Dependency/build integrity review
- [ ] Transaction confirmation UX review
- [ ] Backup/import/recovery interoperability tests
- [ ] Phishing/network-identification UX
- [ ] Hardware wallet or external signer support, or a reviewed equivalent
- [ ] Web/API penetration test

Passing this checklist requires actual evidence/review; this document alone does not satisfy those gates.
