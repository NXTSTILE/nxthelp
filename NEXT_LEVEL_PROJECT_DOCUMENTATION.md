# NxtHelp Next-Level Project Documentation

This document defines how to evolve NxtHelp from a working product into a stable, maintainable, and scalable platform.

It focuses on:
- Template-heavy frontend risk reduction
- Security and reliability hardening
- Clear architecture boundaries
- Better developer velocity through testing and standards

---

## 1) Current State Snapshot

NxtHelp has strong core functionality:
- Account registration/login/profile
- Help request and application lifecycle
- Chat between request owner and helper
- Razorpay payment integration
- Notification system

Current technical pressure points:
- Very large templates (`work/payment.html`, `work/payment_receipt.html`, `work/create_request.html`)
- Extensive inline CSS/JS in templates
- Low template reuse (limited partial/component usage)
- Fat view functions in `work/views.py` mixing domain logic + response logic
- No meaningful automated tests in `accounts/tests.py`, `work/tests.py`, `chat/tests.py`

---

## 2) Why “Template-Heavy” Is a Risk

When templates become too large and self-contained, it creates:
- High change risk (small UI changes can break unrelated sections)
- Styling inconsistency (duplicate class/style blocks)
- Slow iteration (hard to locate and safely update sections)
- Hard testing (presentation and logic concerns become entangled)
- Onboarding friction for new contributors

---

## 3) Priority Weak Points and Fix Plan

### P0 (Immediate) - Stabilize Core Risks

1. Template decomposition
- Break large files into reusable partials/components:
  - `work/payment.html` -> payment summary, helper card, amount form, status blocks
  - `work/payment_receipt.html` -> receipt header, transaction panel, action footer
  - `work/create_request.html` -> form shell, sidebar, section groups
- Move shared UI snippets into `templates/components/`.

2. Asset extraction
- Move inline `<style>` and page scripts from templates into:
  - `static/css/pages/<page>.css`
  - `static/js/pages/<page>.js`
- Keep templates focused on structure and server-rendered data.

3. Template conventions
- Define one canonical pattern:
  - Base layout in `templates/base.html`
  - Per-page content in app templates
  - Repeated widgets in components
  - Minimal logic in templates (presentation-only conditions)

4. Regression safety
- Add smoke tests for critical pages:
  - dashboard, request detail, create request, payment page, payment receipt
- Add access-control tests for sensitive views (payment and chat paths).

### P1 (Next) - Improve Domain Structure

1. Service-layer extraction
- Move heavy business logic from `work/views.py` into service modules:
  - `work/services/payment_service.py`
  - `work/services/request_service.py`
  - `work/services/notification_service.py`

2. Form + validation hardening
- Centralize validation in forms/services (not ad-hoc in views).
- Use deterministic amount parsing and validation for payment flows.

3. Query optimization hygiene
- Add explicit query-shape tests or checks for key pages.
- Standardize `select_related`/`prefetch_related` patterns for list/detail views.

### P2 (Scale Readiness) - Long-Term Maintainability

1. Design system baseline
- Build reusable CSS tokens/utilities in `static/css/style.css`.
- Avoid page-specific style duplication where common components exist.

2. Frontend interaction consistency
- Unify async behavior pattern (AJAX/HTMX/fetch conventions).
- Standardize error handling and user feedback messages.

3. Observability and operations
- Add structured logging around payment lifecycle.
- Add operational playbooks for payment failure, message delays, and admin recovery.

---

## 4) Implementation Blueprint for Template Refactor

### Target directory structure

```text
templates/
  base.html
  components/
    alerts.html
    page_header.html
    card_stat.html
work/templates/work/
  payment.html
  payment_receipt.html
  create_request.html
  partials/
    payment/
      amount_form.html
      helper_card.html
      paid_state.html
    receipt/
      transaction_table.html
      receipt_actions.html
static/
  css/
    pages/
      payment.css
      payment_receipt.css
      create_request.css
  js/
    pages/
      payment.js
```

### Rules for every template
- Keep each template under ~150 lines when possible.
- Inline CSS only for emergency one-off fixes; otherwise static files.
- Page scripts loaded from static JS files.
- Use includes for repeated blocks.
- Keep business calculations out of templates.

---

## 5) Testing Strategy to Support Refactor

Minimum test coverage goals before major UI refactor merge:
- Auth/session protection tests for protected endpoints
- Role/ownership access tests (payer/payee/request owner)
- Payment flow tests:
  - order creation authorization
  - signature verification failure path
  - successful payment completion updates state
- Template render tests for key pages (200/redirect expectations)

Suggested test structure:
- `work/tests/test_payment_flow.py`
- `work/tests/test_request_views.py`
- `chat/tests/test_chat_access.py`
- `accounts/tests/test_auth_flows.py`

---

## 6) Security and Reliability Reinforcement

To move to next level, enforce these continuously:
- Server-trusted payment amounts only
- Strict authorization checks on all object-level actions
- Rate-limiting on abuse-prone endpoints
- Safe redirect checks for user-supplied URLs
- Input sanitization and validation in forms/services
- Uniform error handling (avoid leaking internals in responses)

---

## 7) 6-Week Execution Plan

### Week 1 - Standards + Safety Net
- Add coding conventions for templates, CSS, JS, and views
- Add baseline tests for critical routes and payment security
- Define refactor checklist and PR template

### Week 2 - Payment Template Refactor
- Split `payment.html` into partials/components
- Extract payment CSS/JS to static assets
- Validate no behavioral regressions using tests

### Week 3 - Receipt and Request Form Refactor
- Refactor `payment_receipt.html` and `create_request.html`
- Remove duplicated styling blocks
- Standardize alert/action components

### Week 4 - Service Layer Extraction
- Move payment/request logic from `work/views.py` into services
- Keep views thin (request parsing + response rendering only)
- Add unit tests for extracted services

### Week 5 - Performance and Query Hygiene
- Review heavy list/detail pages for query counts
- Add `select_related/prefetch_related` improvements
- Tighten pagination and filtering consistency

### Week 6 - Hardening and Release Prep
- Run security checklist end-to-end
- Document operational runbooks
- Final regression pass and release candidate sign-off

---

## 8) Definition of Done (Next-Level Standard)

A feature or refactor is complete only if:
- It follows template/component conventions
- Inline CSS/JS is minimized and justified
- Tests exist for behavior and access control
- Security checks remain intact
- Documentation is updated
- Performance is not degraded

---

## 9) Recommended Team Workflow

- Small PRs (one theme per PR: templates, services, tests, etc.)
- Every PR must include:
  - what changed
  - risk level
  - test evidence
  - rollback notes if needed
- Avoid mixing style overhauls with business-logic changes in one PR

---

## 10) Immediate Action List (Start Now)

1. Create shared template components directory and page asset folders.
2. Refactor `work/payment.html` first (highest size + complexity).
3. Add payment flow tests before and after refactor.
4. Refactor `work/payment_receipt.html` and `work/create_request.html`.
5. Extract payment and request logic from `work/views.py` into services.
6. Enforce conventions in PR review for all new code.

---

By executing this roadmap, NxtHelp will move from a template-heavy codebase to a structured, secure, and scalable project that is easier to ship and safer to evolve.
