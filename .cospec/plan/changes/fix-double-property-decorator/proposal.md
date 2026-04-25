# Change: Fix duplicate @property decorator causing template errors

## Rationale
The `time_since_posted` property on the `HelpRequest` model has the `@property` decorator applied twice (lines 105–106 in `work/models.py`). This creates a property-of-a-property, which causes Django’s template engine to fail when resolving `{{ req.time_since_posted }}`. The failure manifests as `TypeError: 'HelpRequest' object is not subscriptable` followed by `TypeError: 'property' object is not callable`, breaking `/dashboard/` and `/browse/`.

## Changes
- Remove the duplicate `@property` decorator on `time_since_posted` in `work/models.py`.

## Impact
- **Affected specifications**: Help request display, dashboard, browse requests, my requests, request detail.
- **Affected code**:
  - `work/models.py:105–106`: Remove duplicate `@property` decorator.
