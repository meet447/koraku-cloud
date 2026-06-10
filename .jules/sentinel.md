
## 2024-05-18 - [Fix SSRF/Auth Bypass in Supabase JWKS Retrieval]
**Vulnerability:** A vulnerability existed where an attacker could bypass authentication by providing a JWT signed by their own Supabase project. The `_iss_to_jwks_url` function merely verified that the issuer's hostname ended in `.supabase.co` instead of exactly matching the configured `SUPABASE_URL`.
**Learning:** Checking domain suffixes is insufficient for validating third-party identity providers (like Supabase) in multi-tenant or cloud architectures. Attackers can leverage their own instances of the identity provider to bypass authentication checks if the application blindly trusts any instance from the provider's domain.
**Prevention:** Always compare issuer hostnames exactly to the expected application configuration (e.g., `settings.supabase_url`), parsing both URLs cleanly to avoid hostname parsing bugs.

## 2024-06-10 - Arbitrary File Write via Symlink Target Resolution Bypass
**Vulnerability:** Path boundary validation `_resolve_host_path` allowed writing files outside the designated workspace using symlinks inside the workspace. The code validated the directory of the path using `os.path.dirname(fpath)` when `parent_for_new_file` was True, incorrectly bypassing the boundary check for the symlinked filename itself.
**Learning:** Checking only the parent directory boundary is insufficient for writes because the target file name itself can be an existing symlink that resolves to a restricted external path.
**Prevention:** Always validate the boundaries of the fully resolved path string (`os.path.realpath`) of the final destination file, not just the parent directory, regardless of whether the file currently exists or is being created.
