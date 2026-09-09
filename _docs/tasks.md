# Household Chore Rotation Tool — Backlog

Tasks are sized for a single session. Each is written to be picked up on its own:
it states the context it needs so you don't have to read the other tasks first.
Rough build order is top to bottom, but most tasks only need the data models
(task 2) to exist.

Stack: Django 5.1 + HTMX + server-rendered templates, SQLite, Django admin for
setup. See `_docs/plan.md` for product scope.

---

## 1. Set up project with a passing test
Goal: A cloned repo can install dependencies and run a green test suite with one command.
Description: The Django project (`config`) and app (`chores`) already exist. Add a test runner setup (pytest-django or the built-in Django runner), a single smoke test that asserts the home URL or a trivial view returns 200, and a short "Running tests" section in a README or `_docs`. Confirm `python manage.py check` and the test command both pass from a fresh virtualenv.

## 2. Core data models: Member and Chore
Goal: Persist household members and chores with the fields the rest of the app needs.
Description: Add a `Member` model (name, active flag, created timestamp) and a `Chore` model (name, frequency as a choice of `daily`/`weekly`, active flag, optional notes). Generate migrations, register both in the Django admin with sensible list displays, and write model tests covering string representation and the frequency choices.

## 3. Preset chore list as seed data
Goal: A new household can load a curated list of daily and weekly chores without typing them in.
Description: Define the preset chores (e.g. dishes, wipe counters, trash, sweep for daily; bathroom, vacuum, sheets, mop for weekly) as a fixture or data migration. Add a `load_presets` management command that creates any missing preset chores idempotently. Include a test that running it twice does not create duplicates.

## 4. Rotation model
Goal: Store a fixed, ordered rotation of members for each chore.
Description: Add a model that links a `Chore` to an ordered list of `Member`s (through model with a position/order field, or an explicit ordering table). Enforce uniqueness of position per chore. Expose it in the admin as an inline on the chore, and write tests that a rotation preserves order and rejects duplicate positions.

## 5. "Whose turn" calculation
Goal: Given a chore and a date, return which member is responsible.
Description: Write a pure function (no HTTP, no templates) that takes a chore's rotation, a reference date, and a start/anchor date, and returns the member whose turn it is for the current daily or weekly period. Handle empty rotations and single-member rotations gracefully. Cover the logic with unit tests including period rollover.

## 6. Completion records and history log
Goal: Record each time a chore is marked done, by whom and when.
Description: Add a `Completion` model (chore, member, completed_at timestamp, optional period key). Add query helpers: "was this chore completed in the current period?" and "recent completions, newest first". Register in the admin as a read-mostly list. Write tests for the helpers.

## 7. Manual swap between two people
Goal: Two members can trade an upcoming turn for one chore.
Description: Add a `Swap` model or equivalent that overrides the computed "whose turn" result for a specific chore and period, recording the two members involved and when the swap was made. Update or wrap the task 5 calculation so an active swap takes precedence. Write tests showing a swap changes the responsible member for only the targeted period.

## 8. Overdue detection
Goal: Determine whether a chore is currently overdue.
Description: Write a pure function that takes a chore's frequency and its most recent completion (or none) and returns an overdue status plus how many periods have been missed. A daily chore not done today after some cutoff is overdue; a weekly chore not done this week is overdue. Unit-test the boundaries.

## 9. Base template and layout
Goal: A shared page shell that all screens extend.
Description: Create `base.html` with a mobile-first layout, a header, a messages area, the HTMX script tag, and a block for page content. Add a minimal static CSS file and wire up static files. Add one placeholder page that extends the base so the layout is visible via `runserver`.

## 10. Chore board view
Goal: One screen showing every active chore, whose turn it is, and whether it's done this period.
Description: Add a view and template that lists active chores grouped by daily/weekly, each row showing the chore name, the responsible member (from task 5), and a done/not-done indicator (from task 6). Server-rendered only, no interactivity yet. Add a URL route and a view test asserting the chores and names appear.

## 11. Mark-a-chore-done endpoint (HTMX)
Goal: Tapping a chore's checkbox records a completion and updates just that row.
Description: Add a POST view that creates a `Completion` for the given chore in the current period and returns the re-rendered board row partial. Wire the board checkbox with `hx-post` and a targeted swap. Handle the already-completed case. Test the view creates a completion and returns the updated fragment.

## 12. Board auto-refresh via polling
Goal: The board reflects other people's changes without a manual reload.
Description: Extract the board's chore list into a partial and add an HTMX polling trigger (e.g. every 10 seconds) that re-fetches and swaps it. Ensure in-progress interactions aren't disrupted by the refresh. Add a view test for the partial endpoint.

## 13. Overdue nudge on the board
Goal: Overdue chores are visually called out on the board.
Description: Use the task 8 detection to mark overdue chores in the board view context, and style those rows (color, an icon, or a banner count at the top). No new models. Add a view test that a chore with no recent completion renders with the overdue treatment.

## 14. History log view
Goal: A browsable list of who did what, when.
Description: Add a view and template showing recent `Completion` records newest-first, with chore name, member, and timestamp, plus simple optional filtering by member or chore. Paginate or cap the list. Add a URL route and a view test.

## 15. Swap UI on the board
Goal: Members can initiate a swap from the board without using the admin.
Description: Add a small form (modal or inline) on a chore row that lets the user pick the other member and submit a swap for the current period, using the task 7 model. Re-render the affected row on success. Test that submitting the form creates a swap and updates the responsible member shown.

## 16. Setup / onboarding screen
Goal: A first-run screen to add members and choose chores without the admin.
Description: Add a view with two simple forms: add/remove household members, and select which preset chores (task 3) are active for this household. On save, redirect to the board. Add view tests for creating members and toggling chores.

## 17. Current-member picker
Goal: The app knows who is using it so completions are attributed correctly.
Description: Add a lightweight session-based "I am ___" picker (a dropdown of active members stored in the session) shown in the header, and use it as the default member for completions and swaps. No passwords. Test that the selected member is used when marking a chore done.

## 18. Shared household login gate
Goal: The app is not open to the public internet.
Description: Add a single shared-password gate (one env-configured password, a login form, session flag, and middleware or a decorator that redirects unauthenticated requests). Exempt the login route and static files. Test that protected views redirect when locked and pass when unlocked.

## 19. Deployment configuration
Goal: The project can be deployed with production-safe settings.
Description: Move `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` to environment variables with safe defaults, add WhiteNoise for static file serving, add a `Procfile` or `Dockerfile` and a pinned `requirements.txt`, and document the deploy steps for a single-process host (Fly.io or Railway) with a persistent volume for SQLite. Verify `manage.py check --deploy` reports no critical issues.
