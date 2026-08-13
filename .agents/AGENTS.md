# Agent Rules for PollLocator Project

## 🧪 Mandatory Pre-Commit & Verification Rule

Before completing any task, pushing changes, or modifying endpoints in `resources/routes.py`, `app.py`, or `database/models.py`:

1. **Mandatory Test Engine Execution**:
   - You MUST run the test engine using the `pollSurvey` virtual environment:
     ```powershell
     & "E:\Poll App\PollLocator\pollSurvey\Scripts\python.exe" test_engine.py
     ```
2. **Success Criteria**:
   - All tests (online mode, offline mode, upsert/idempotency, material info, AND Transformer updates verifying attached Pole integrity) MUST pass cleanly (`OK`).
   - The test teardown MUST successfully clean up all generated test seed data from MongoDB Atlas.
3. **Zero Failure Policy**:
   - Do NOT mark a backend task as complete or commit/push code if any test fails. Debug and fix the root cause first.
