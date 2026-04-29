import re
from decimal import Decimal

from work.models import Application


def extract_amount_from_text(value):
    """Extract first numeric amount from a string-like budget field."""
    if not value:
        return 0.0
    numbers = re.findall(r'[\d]+\.?[\d]*', str(value).replace(',', ''))
    if not numbers:
        return 0.0
    return float(numbers[0])


def get_accepted_application(help_request):
    return Application.objects.filter(
        help_request=help_request,
        applicant=help_request.selected_helper,
        status='accepted',
    ).first()


def resolve_backend_payment_amount(help_request):
    """
    Resolve amount from accepted application first, then help request budget.
    Returns Decimal('0') if no valid amount can be determined.
    """
    accepted_app = get_accepted_application(help_request)
    amount_value = 0.0

    if accepted_app and accepted_app.proposed_budget:
        amount_value = extract_amount_from_text(accepted_app.proposed_budget)

    if amount_value <= 0 and help_request.budget:
        amount_value = extract_amount_from_text(help_request.budget)

    return Decimal(str(amount_value)), accepted_app
