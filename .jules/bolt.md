## 2024-05-24 - Avoid Re-allocating Sets in React Renders
**Learning:** Re-initializing a large `Set` inside a frequently called utility function or render loop in React degrades performance due to repeated memory allocation and hashing. This is especially relevant in this project because the React Compiler is not enabled, meaning manual memoization is required.
**Action:** Extract constant `Set` initializations to the module level. For dynamic `Set`s that depend on props or state, use `useMemo` to memoize the allocation, preventing unnecessary re-allocations on every render.
