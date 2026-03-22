# NxtHelp Security Audit Report

Based on a review of the provided NxtHelp Django codebase, several security vulnerabilities and logic flaws were identified. Below is a detailed breakdown of each issue along with a recommended solution.

## 1. Critical: Payment Manipulation (Business Logic Flaw)

**Location:** `work/views.py` ➔ `create_razorpay_order`

### Description
The application integrates with Razorpay for handling payments between users. However, the endpoint responsible for creating the Razorpay order (`create_razorpay_order`) directly reads the total payment amount from the client's HTTP POST request body.
```python
data = json.loads(request.body)
amount = Decimal(str(data.get('amount', 0)))
```
Because the server places absolute trust in the client-provided `amount`, an attacker (the requester) can simply modify the request to send `{ "amount": 1 }` (₹0.01). Upon paying this nominal amount, the `confirm_payment` endpoint will successfully verify the Razorpay signature and mark the entire help request as `resolved`, defrauding the helper.

### Recommendation
**Never trust client-provided prices.** The server must compute the payment amount internally before creating the Razorpay order. The backend should look up the agreed-upon price from the database—for example, the `proposed_budget` from the accepted `Application`, or the `HelpRequest` budget.

---

## 2. High: Open Redirect Vulnerability

**Location:** `accounts/views.py` ➔ `login_view`

### Description
In the custom login view, the application reads the `next` parameter from the requested URL to redirect the user after a successful login:
```python
next_url = request.GET.get('next', 'dashboard')
return redirect(next_url)
```
Because `next_url` is not validated to ensure it belongs to the same domain, an attacker could craft a malicious link such as `https://nxthelp.com/login/?next=http://evil.com`. Once the user logs in, they will be seamlessly redirected to the malicious site.

### Recommendation
Use Django's built-in `url_has_allowed_host_and_scheme` to validate that the redirect URL is safe before performing the redirection.

---

## 3. High: Lack of Email Uniqueness Enforcement

**Location:** `accounts/forms.py` ➔ `UserRegisterForm` & `ProfileUpdateForm`

### Description
Django's built-in `User` model does not enforce unique email addresses at the database level by default. Since neither the registration form nor the profile update form contains a `clean_email` validation method, multiple users can register or update their profiles to use the exact same email address. This overlap can break password resets, cause the wrong user to receive notifications, and allow users to spoof others.

### Recommendation
Add a custom `clean_email` method to both forms to explicitly enforce uniqueness:
```python
def clean_email(self):
    email = self.cleaned_data.get('email')
    query = User.objects.filter(email=email)
    if self.instance and self.instance.pk:
        query = query.exclude(pk=self.instance.pk)
    if query.exists():
        raise forms.ValidationError('An account with this email already exists.')
    return email
```

---

## 4. Medium: Unverified Email Changes

**Location:** `accounts/views.py` ➔ `edit_profile`

### Description
When a user updates their email via the `ProfileUpdateForm`, the new email is saved immediately without any verification, and the user's account remains `is_active=True`. A malicious user can take over another user's email address on the platform or bypass domain restrictions (if any).

### Recommendation
If a user changes their email address on their profile, their account status (`is_active`) should be switched to `False`, and a new verification token should be dispatched. They must re-verify the new email before they can continue to use the platform.

---

## 5. Low/Medium: Email Enumeration via Resend Verification

**Location:** `accounts/views.py` ➔ `resend_verification`

### Description
The view that handles resending the verification email yields different flash messages based on whether the provided email exists in the database.
- **Exists:** `messages.success(request, f'Verification email resent to {email}.')`
- **Does not exist:** `messages.info(request, f'If that email is registered and unverified, a new link has been sent.')`

This discrepancy allows an attacker to systematically enumerate active and inactive email addresses registered in the database by observing the notification color and message text. 

### Recommendation
Return the exact same generic string (e.g., `"If that email is registered and requires verification, a new link has been sent."`) with the exact same message level (`messages.info`) for both branches of the application logic.
