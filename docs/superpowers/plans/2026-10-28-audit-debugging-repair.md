# P2P Audit, Debugging and Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit, reproduce with regression tests, patch confirmed security and integrity defects in the P2P application, and verify all checks pass without touching production credentials or modifying external services.

**Architecture:** 
- Backend: FastAPI, SQLAlchemy 2.0 Async, Pydantic v2, PostgreSQL (asyncpg), Redis, Celery.
- Frontend: React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query v5, Zustand, i18next.
- Approach: Test-Driven Development (TDD) for every backend defect; unit/integration tests with in-memory SQLite / mock AsyncSession to ensure zero external/production DB connection.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, pytest, React 19, Vite, TypeScript.

**Spec:** Local requirements, `frontend/BACKEND_API.md`, `frontend/ARCHITECTURE.md`, user prompt requirements.

## Global Constraints

- READ-ONLY regarding production secrets and services: Zero external connections to Render, PostgreSQL port 5432, Telegram API, or Redis.
- Zero credential rotation or Git history alteration in this phase.
- Preserve existing user work (`.gitignore` backup rules, `backend/.env.example` placeholders, external backup directory).
- Every bug fix must follow strict TDD: failing regression test first, minimal fix, pass verification.
- No untested code changes.

## Review Focus

1. Unauthorized WebSocket access to `/ws/slot/{slot_id}` leaking partner Telegram and allowing unauthorized slot lifecycle manipulation.
2. IDOR / lack of ownership check on `GET /slots/{slot_id}` leaking participant profiles and breaking anonymous matching.
3. Ineffective session revocation where logged-out users can still use existing access tokens and refresh tokens.
4. Concurrency race conditions in slot booking allowing point double-spending or slot double-booking.
5. Premature `mark_absent` abuse before the 15-minute grace period has passed.

---

### Task 1: Session Revocation & Logout Enforcement (BUG-03)

**Files:**
- Modify: `backend/app/core/dependencies.py`
- Modify: `backend/app/api/v1/auth.py`
- Modify: `backend/app/ws/slot_ws.py`
- Test: `backend/tests/test_auth_session.py`

**Interfaces:**
- Consumes: `User.is_logged_in` boolean flag.
- Produces: `get_current_user`, `refresh`, and `_authenticate` raising 401 / closing WebSocket when `is_logged_in is False`.

- [ ] **Step 1: Write the failing test**
Create `backend/tests/test_auth_session.py` testing that when `user.is_logged_in == False`, `get_current_user` raises `HTTPException(401)`, `refresh` raises `HTTPException(401)`, and `_authenticate` returns `None`.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_auth_session.py -v`
Expected: FAIL because `is_logged_in` is currently ignored.

- [ ] **Step 3: Implement minimal code to pass**
In `backend/app/core/dependencies.py`:
Update line 56: `if user is None or not user.is_active or not user.is_logged_in:`
In `backend/app/api/v1/auth.py`:
Update line 264: `if user is None or not user.is_active or not user.is_logged_in:`
In `backend/app/ws/slot_ws.py`:
Update line 32: `return user if user and user.is_active and user.is_logged_in else None`

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_auth_session.py -v`
Expected: PASS.

---

### Task 2: WebSocket Slot Authorization & IDOR Protection (BUG-01)

**Files:**
- Modify: `backend/app/ws/slot_ws.py`
- Test: `backend/tests/test_ws_authorization.py`

**Interfaces:**
- Consumes: `Slot.reviewer_id`, `Slot.reviewee_id`, `User.id`, `User.is_admin`.
- Produces: `slot_websocket` closing connection with 4403 if user is not a participant, and `_handle_client_event` ignoring unauthorized events.

- [ ] **Step 1: Write the failing test**
Create `backend/tests/test_ws_authorization.py` verifying that a non-participant user attempting to connect to `/ws/slot/{slot_id}` is rejected with code 4403 or denied event handling.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_ws_authorization.py -v`
Expected: FAIL because non-participants are currently connected unconditionally.

- [ ] **Step 3: Implement minimal code to pass**
In `backend/app/ws/slot_ws.py`:
In `slot_websocket`, parse `slot_id`, query `Slot` from DB, check:
`if user.id != slot.reviewer_id and user.id != slot.reviewee_id and not user.is_admin: await websocket.close(code=4403); return`
In `_handle_client_event`:
Check participant permission before processing any client event.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_ws_authorization.py -v`
Expected: PASS.

---

### Task 3: REST Slot Participant & Anonymous Matching Protection (BUG-02)

**Files:**
- Modify: `backend/app/api/v1/slots.py`
- Test: `backend/tests/test_slot_authorization.py`

**Interfaces:**
- Consumes: `Slot.reviewer_id`, `Slot.reviewee_id`, `User.id`, `User.is_admin`.
- Produces: `GET /slots/{slot_id}` raising `HTTPException(403)` when accessed by an unauthorized third party.

- [ ] **Step 1: Write the failing test**
Create `backend/tests/test_slot_authorization.py` asserting that a third-party user accessing `GET /slots/{slot_id}` receives HTTP 403 Forbidden.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_slot_authorization.py -v`
Expected: FAIL (currently returns HTTP 200).

- [ ] **Step 3: Implement minimal code to pass**
In `backend/app/api/v1/slots.py`:
In `get_slot`:
Verify `if not (slot.reviewer_id == user.id or slot.reviewee_id == user.id or user.is_admin): raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to view this slot")`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_slot_authorization.py -v`
Expected: PASS.

---

### Task 4: Slot Booking Concurrency & Row Locking (BUG-04)

**Files:**
- Modify: `backend/app/services/slot_service.py`
- Test: `backend/tests/test_booking_concurrency.py`

**Interfaces:**
- Consumes: `AsyncSession`, `Slot`, `User`, `points_service.can_book_slot`.
- Produces: Atomic lock on Slot and Reviewee, preventing double-booking and double point deduction.

- [ ] **Step 1: Write the failing test**
Create `backend/tests/test_booking_concurrency.py` simulating concurrent booking of the same slot or double-booking with 1 point.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_booking_concurrency.py -v`
Expected: FAIL without lock.

- [ ] **Step 3: Implement minimal code to pass**
In `backend/app/services/slot_service.py`:
Update `book_slot` to lock the slot row with `select(Slot).where(Slot.id == slot.id).with_for_update()` and the reviewee row with `select(User).where(User.id == reviewee.id).with_for_update()`.
Verify status and points on the locked objects.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_booking_concurrency.py -v`
Expected: PASS.

---

### Task 5: Absence Grace Period Enforcement (BUG-05)

**Files:**
- Modify: `backend/app/services/slot_service.py`
- Test: `backend/tests/test_absent_grace.py`

**Interfaces:**
- Consumes: `slot.start_time`, `ABSENT_GRACE_MINUTES = 15`.
- Produces: `mark_absent` rejecting requests before `start_time + 15m` with HTTP 400.

- [ ] **Step 1: Write the failing test**
Create `backend/tests/test_absent_grace.py` calling `mark_absent` on a slot whose start time is in the future or within the 15-minute grace period.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_absent_grace.py -v`
Expected: FAIL (currently succeeds and docks XP immediately).

- [ ] **Step 3: Implement minimal code to pass**
In `backend/app/services/slot_service.py`:
Import `timedelta`.
In `mark_absent`:
Check `if _now() < slot.start_time + timedelta(minutes=ABSENT_GRACE_MINUTES): raise HTTPException(status.HTTP_400_BAD_REQUEST, "Absent can only be marked 15 minutes after scheduled start time")`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_absent_grace.py -v`
Expected: PASS.

---

### Task 6: Admin Resolve Repeat Refund Protection (BUG-06) & User Deletion Safety (BUG-11)

**Files:**
- Modify: `backend/app/api/v1/admin.py`
- Test: `backend/tests/test_admin_fixes.py`

**Interfaces:**
- Consumes: `Slot.status`, `SlotStatus`.
- Produces: `resolve_slot` rejecting already cancelled/completed slots with HTTP 409; `delete_user` safely soft-deactivating users with foreign key relations.

- [ ] **Step 1: Write the failing test**
Create `backend/tests/test_admin_fixes.py` testing calling `resolve_slot` on an already cancelled slot, asserting HTTP 409 and no additional points awarded.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_admin_fixes.py -v`
Expected: FAIL (currently awards points again).

- [ ] **Step 3: Implement minimal code to pass**
In `backend/app/api/v1/admin.py`:
In `resolve_slot`:
Add check `if slot.status in (SlotStatus.COMPLETED.value, SlotStatus.CANCELLED.value): raise HTTPException(status.HTTP_409_CONFLICT, f"Slot cannot be resolved in its current state ({slot.status})")`.
In `delete_user`:
Check if user has slot/review dependencies; if so, soft-deactivate `user.is_active = False; user.is_logged_in = False` instead of hard deleting to preserve foreign key integrity.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_admin_fixes.py -v`
Expected: PASS.

---

### Task 7: Leaderboard Snapshot Idempotency (BUG-07) & Reminder Idempotency (BUG-08)

**Files:**
- Modify: `backend/app/tasks/leaderboard_tasks.py`
- Modify: `backend/app/tasks/slot_tasks.py`
- Modify: `backend/app/db/models/leaderboard_snapshot.py`
- Modify: `backend/app/db/models/review.py`
- Test: `backend/tests/test_tasks_idempotency.py`

**Interfaces:**
- Consumes: `LeaderboardSnapshot`, `Notification`.
- Produces: Idempotent task execution with zero duplicate snapshot rows or duplicate notifications.

- [ ] **Step 1: Write the failing test**
Create `backend/tests/test_tasks_idempotency.py` running `_monthly_snapshot` twice and asserting no duplicate rows are created.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_tasks_idempotency.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement minimal code to pass**
In `backend/app/tasks/leaderboard_tasks.py`:
Delete existing snapshot entries for `(month, category)` before inserting.
In `backend/app/db/models/leaderboard_snapshot.py`:
Add `UniqueConstraint("month", "category", "user_id", name="uq_leaderboard_month_cat_user")`.
In `backend/app/db/models/review.py`:
Add `UniqueConstraint("slot_id", "author_id", name="uq_reviews_slot_author")`.
In `backend/app/tasks/slot_tasks.py`:
Widen reminder window and check if `slot_reminder` was already sent before creating a new one.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_tasks_idempotency.py -v`
Expected: PASS.

---

### Task 8: Frontend SlotDetailPage Absent Guard (BUG-10)

**Files:**
- Modify: `frontend/src/features/slots/pages/SlotDetailPage.tsx`
- Test: `npm run lint` and `npm run build`

**Interfaces:**
- Consumes: `slot.start_time`, `slot.status`.
- Produces: Button enabled only when 15 minutes have passed since scheduled start time.

- [ ] **Step 1: Implement the guard**
In `frontend/src/features/slots/pages/SlotDetailPage.tsx`:
Add `const isTimeValidForAbsent = new Date().getTime() >= new Date(slot.start_time).getTime() + 15 * 60 * 1000;`
Update absent button disabled state: `disabled={isAbsentingSlot || !isTimeValidForAbsent}`.

- [ ] **Step 2: Verify frontend type check & build**
Run: `cd frontend && npm run lint && npm run build`
Expected: exit code 0.

---

### Task 9: Full Verification & Code Review Gate

**Files:**
- Review: `git diff --stat`, `git diff --check`
- Test: Run full backend test suite (`pytest backend/tests/ -v`)
- Test: Run frontend lint & build (`cd frontend && npm run lint && npm run build`)
- Verify: Avvalgi foydalanuvchi o'zgarishlari saqlanganini tekshirish (`.gitignore`, `backend/.env.example`, `p2p-secure-backup`).

- [ ] **Step 1: Execute all tests**
- [ ] **Step 2: Perform independent code review**
- [ ] **Step 3: Prepare final delivery report**
