## Implementation
- [x] 1.1 Remove duplicate @property decorator on time_since_posted
     【Target Object】`work/models.py`
     【Purpose】Fix the TypeError in Django templates when accessing `time_since_posted` on `HelpRequest` instances by removing the duplicate `@property` decorator that creates a property-of-a-property.
     【Method】Modify: Remove the duplicate `@property` decorator from the `time_since_posted` method in the `HelpRequest` model class.
     【Dependencies】None
     【Content】
        - Locate the `time_since_posted` method definition in the `HelpRequest` model (currently lines 105–106)
        - Remove one of the two consecutive `@property` decorators so only a single decorator remains above the method
        - Verify no other duplicate decorators exist on adjacent properties (e.g., `days_until_deadline`)
        - Confirm the fix resolves template resolution errors on `/dashboard/` and `/browse/`
