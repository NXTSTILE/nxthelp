# NxtHelp - Features and Workflows Documentation

## Introduction

NxtHelp is a comprehensive platform designed for university communities, bridging the gap between students, faculty, and staff. It allows users to post requests for help, offer their skills to assist others, communicate securely, and handle peer-to-peer payments efficiently.

This document outlines the core features of the platform and details the user workflows from start to finish.

---

## Core Features

### 1. User Identity & Profiles
*   **Account Registration & Authentication:** Secure sign-up and login process with strong defense mechanisms against common web vulnerabilities.
*   **Email Verification:** Token-based email activation to ensure that only legitimate users from the community gain access to the platform.
*   **Profile Management:** Users can maintain detailed profiles showcasing their:
    *   Bio and Profession
    *   Specific Skills (to match with potential help requests)
    *   UPI ID (for receiving payments securely)
*   **Dynamic Reverification:** Updating critical profile information automatically triggers a reverification process to maintain platform integrity.

### 2. The Help Request Engine
*   **Post Requests:** Users needing assistance can create detailed posts outlining their requirements, setting a specific budget, and defining a strict deadline.
*   **Application System:** Community members with the requisite skills can browse open requests and submit applications or bids to offer their help.
*   **Request Management:** Requesters can review incoming applications and seamlessly accept the best fit, transitioning the request into an "In Progress" status.
*   **System-Wide Notifications:** Users receive instant alerts for key actions, such as when someone applies to their request, when their application is accepted, or when work is completed.

### 3. Secure Internal Messaging
*   **Isolated Chat Rooms:** Once an application is accepted, a private, secure chat room is automatically generated exclusively for the requester (Poster) and the selected helper.
*   **Real-time Communication:** Dynamic messaging powered by JSON APIs allows users to communicate requirements, share updates, and coordinate effectively without leaving the platform.

### 4. Payments and Ledger
*   **Integrated Payment Gateway:** Built-in Razorpay integration facilitates smooth real-money transfers (via UPI, Cards, NetBanking).
*   **Cryptographic Verification:** Payments are strictly validated through cryptographic signatures, ensuring that all transactions match the agreed-upon budget and are securely recorded in the platform's ledger.
*   **Protection for Both Parties:** System logic ensures requesters pay the exact agreed amount, and helpers are guaranteed their funds without manual discrepancies.

---

## Key Workflows

### Workflow 1: User Onboarding
1.  **Sign Up:** User navigates to the registration page, enters their email, and sets a password.
2.  **Verification:** An email containing a unique verification link is sent via Gmail SMTP.
3.  **Profile Setup:** Upon clicking the link, the account is activated. The user fills out their profile (skills, UPI ID, etc.).
4.  **Dashboard Access:** The user is redirected to their dashboard, ready to either post requests or browse for work.

### Workflow 2: Requesting Assistance
1.  **Creation:** A user clicks "Create Request," detailing what they need (e.g., "Need a math tutor for calculus"), setting a budget ($20), and a deadline.
2.  **Broadcasting:** The request goes live on the platform's feed for others to see.
3.  **Reviewing Bids:** Helpers submit applications. The requester gets a notification for each new bid.
4.  **Acceptance:** The requester reviews applicant profiles and clicks "Accept" on the chosen helper. The request status changes to `in_progress`.

### Workflow 3: Execution and Collaboration
1.  **Chat Initialization:** Upon acceptance, an isolated chat room is unlocked for the requester and the helper.
2.  **Collaboration:** The two parties discuss the details, share files if necessary, and the helper begins the task.
3.  **Completion:** Once the task is finished, the helper informs the requester via chat.

### Workflow 4: Payment and Closure
1.  **Trigger Payment:** The requester initiates the payment process from the request dashboard.
2.  **Checkout:** A Razorpay popup appears. The requester completes the transaction using their preferred method (UPI/Card).
3.  **Verification:** The backend confirms the Razorpay signature and ensures the amount matches the budget.
4.  **Resolution:** The payment is logged in the system ledger, the helper is credited, and the request is marked as `completed`.
