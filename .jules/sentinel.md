
## 2024-05-18 - [Fix SSRF/Auth Bypass in Supabase JWKS Retrieval]
**Vulnerability:** A vulnerability existed where an attacker could bypass authentication by providing a JWT signed by their own Supabase project. The `_iss_to_jwks_url` function merely verified that the issuer's hostname ended in `.supabase.co` instead of exactly matching the configured `SUPABASE_URL`.
**Learning:** Checking domain suffixes is insufficient for validating third-party identity providers (like Supabase) in multi-tenant or cloud architectures. Attackers can leverage their own instances of the identity provider to bypass authentication checks if the application blindly trusts any instance from the provider's domain.
**Prevention:** Always compare issuer hostnames exactly to the expected application configuration (e.g., `settings.supabase_url`), parsing both URLs cleanly to avoid hostname parsing bugs.
