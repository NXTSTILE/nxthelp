# NxtHelp - Complete Architecture & Tech Stack Report

**NxtHelp** is a university-focused platform that connects students, faculty, and staff allowing them to post requests for help, securely communicate, and efficiently process peer-to-peer payments for services.

---

## 1. Core Technology Stack (The Foundation)

Your application uses a modern, battle-tested Python stack designed to be flexible and highly scalable:

*   **Backend Framework:** **Django (v4.2)**
    *   *Why it's used:* Django provides robust MVT architecture, an excellent built-in ORM for databases, automated admin interfaces, and strong built-in security features (CSRF, XSS protection).
*   **Database Engine:** 
    *   *Development:* **SQLite3** (Lightweight, file-based database for local testing).
    *   *Production:* **PostgreSQL** via `psycopg2-binary` (Robust, scalable database optimized for Railway/Cloud deployments). Connected dynamically using `dj-database-url`.
*   **Web Server / WSGI:** **Gunicorn (v21.2.0)**
    *   *Why it's used:* A production-grade Python WSGI HTTP Server that efficiently handles multiple concurrent requests to your Django app.
*   **Environment Manager:** **python-dotenv**
    *   *Why it's used:* Securely manages local environment variables out of the codebase (reading your `.env` file).

---

## 2. Frontend Technology (The Interface)

The website uses a dynamic server-side rendering approach (MVT - Model View Template):

*   **HTML Templates:** Django Templates (`*.html`).
*   **CSS Framework:** **Bootstrap 5** combined with a custom "UniConnect Dark/Neon Theme".
*   **Iconography:** FontAwesome (`<i class="fas fa-*"></i>`).
*   **Dynamic Interactions (JavaScript):** Vanilla JavaScript & AJAX (`XMLHttpRequest`/`fetch`) are used to power:
    *   Asynchronous Razorpay checkout windows.
    *   Real-time chat message fetching (`fetch_messages` view).
    *   Dynamic payment creation via `create_razorpay_order`.
*   **Static Asset Delivery:** **WhiteNoise (v6.5.0)**
    *   *Why it's used:* Intercepts requests for static files (CSS, JS, Images) and serves them ultra-fast directly from your Python web server without needing a separate CDN like AWS S3 or Nginx.

---

## 3. Third-Party APIs & Integrations

The system connects to key external providers to handle complex logic:

*   **Razorpay Payment Gateway API (v1.4.1)**
    *   *Purpose:* Handles real money transfers between users seamlessly via UPI, Cards, and NetBanking.
    *   *Flow:* The backend creates a secure `order_id`, the frontend triggers the Razorpay popup, and the backend verifies the cryptographic signature (`razorpay_signature`) to finalize the `Payment` ledger.
    *   *Keys used:* `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`.
*   **Gmail SMTP (Google Mail API)**
    *   *Purpose:* Sends necessary transactional emails (like Account Verification Links).
    *   *Flow:* Django's `smtp.EmailBackend` connects to `smtp.gmail.com` securely via TLS using your standard App Passwords.

---

## 4. Application Architecture (The Modules)

The codebase is logically split into three isolated Django "apps":

### 🔹 App 1: `accounts` (Identity & Profiles)
*   **Models:** `Profile` (Bio, skills, upi_id, profession), `EmailVerificationToken`.
*   **Features:** Handles registration, robust login/logout (with recently patched Open Redirect defenses), unique email enforcement, profile updates (which trigger reverification), and token-based email activation logic.

### 🔹 App 2: `work` (The Core Engine)
*   **Models:** `HelpRequest`, `Application`, `Category`, `Notification`, `Payment`.
*   **Features:** 
    *   Allows users to post needs (`HelpRequest`) with specific budgets and deadlines.
    *   Allows other users to bid/apply (`Application`).
    *   Poster can accept an application, moving the Request into an `in_progress` state.
    *   Generates system-wide alerts (`Notification`) for actions like received applications or finished work.
    *   Manages the Razorpay cryptographic verification and ledger system (`Payment`).

### 🔹 App 3: `chat` (Internal Messaging)
*   **Models:** `ChatMessage`
*   **Features:** Provides isolated chat rooms. Only the specific `posted_by` and `selected_helper` users can view or send messages in a room. Fetches messages dynamically via JSON APIs.

---

## 5. Deployment Setup (Railway PaaS)

The project is highly portable but currently strictly optimized for **Railway.app**:

*   **Instructions (The Builder):** `railway.toml` & `runtime.txt` inform the Nixpacks build system that this is a Python 3.11 app.
*   **Build Phase:** Railway executes `pip install -r requirements.txt` and automatically performs `python manage.py collectstatic` to bundle the website assets.
*   **The Boot Process:** Using the `Procfile`, Railway applies pending database migrations (`migrate`) and mounts the application over the internet using `gunicorn`.
*   **Scale:** Because of this architecture, your app is essentially stateless, meaning you can spin up 10 identical servers simultaneously if traffic spikes.

---

## 6. Security Posture

As a result of recent security patches, NxtHelp defends against common modern attacks:

*   **Cross-Site Request Forgery (CSRF):** Django enforces unique `<input type="hidden" name="csrfmiddlewaretoken">` logic on every single form submission.
*   **Cross-Site Scripting (XSS):** Web pages strictly auto-escape all user inputs (descriptions, chat messages).
*   **Business Logic Flaws:** Payments strictly adhere to the exact agreed-upon budget retrieved from the database—protecting helpers from being paid $0.01 by malicious requesters.
*   **Access Control (IDOR):** Chat logs, private applications, and payment windows verify ownership (`request.user == posted_by` or `request.user == selected_helper`) before executing.
*   **Email Enumeration & Open Redirect:** Forms cleanly mask authentication failures and strictly validate URLs before bouncing users to their dashboard.
