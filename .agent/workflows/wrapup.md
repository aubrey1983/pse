---
description: Comprehensive Wrap-up (Review, Fix, Clean, Test, Push)
---

1. **Expert Code Review**: Act as a senior software engineer. Scan the codebase (focusing on recently modified files) for:
   - Logic errors or potential edge cases.
   - Unhandled exceptions.
   - Inconsistencies in coding style or naming.
   - Redundant or legacy code.
   - *Note: Use `grep_search` or `view_file` to inspect code.*

2. **Fix Issues**: If any critical or moderate issues are found in Step 1, fix them immediately. 
   - If a fix is risky or ambiguous, ask the user for clarification.
   - If no issues are found, proceed.

3. **Cleanup**: 
   - Remove unused imports.
   - Remove temporary debug `print()` statements.
   - Ensure comment clarity (remove mental notes if they are no longer relevant).

4. **Retest**: 
   - Execute the main script (e.g., `python regenerate_report.py`) to ensure the build succeeds.
   - If possible/necessary, verify the output (e.g., check `report.html` was generated and looks correct).

5. **Commit & Push**:
   - Check status: `git status`
   - Stage changes: `git add .`
   - Commit: `git commit -m "Refinement: Code review cleanup and final polish"` (Customize message based on what was actually done).
   - Push: `git push`
