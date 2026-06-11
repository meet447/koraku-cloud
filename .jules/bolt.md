## 2025-06-07 - Python inline set performance benefit for membership checks
Replacing an inline tuple check (e.g. `x in ("a", "b", "c")`) with an inline set (e.g. `x in {"a", "b", "c"}`) enables the Python compiler to compile the set to a `frozenset` at bytecode compilation time. This results in significantly faster `in` operations (~35-75% depending on hit vs miss) without cluttering module scope with global variables.

## 2025-06-11 - JavaScript Set initialization performance in React rendering
**Learning:** Re-initializing a large `Set` (e.g., > 40 items) inside a frequently called utility function or render loop in JavaScript/React is extremely slow compared to defining it once at module scope. This happens because JS has to allocate new memory, hash every single string, and populate the `Set` on every single function call.
**Action:** Move static `new Set([...])` definitions out of functions/components and into module-level constants to prevent re-allocation and re-hashing on every invocation.
