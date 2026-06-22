## 2025-06-22 - Missing 'title' attributes on 'aria-label' buttons
**Learning:** Found several components where `button`s had `aria-label`s for screen readers but lacked native `title` tooltips for mouse/sighted users, specifically on icon-only buttons. The two attributes should often accompany each other on icon-only actions to ensure a fully accessible and clear UX.
**Action:** Always ensure that icon-only buttons include both an `aria-label` (for screen readers) and a `title` (for tooltip hover on desktop) attribute.
