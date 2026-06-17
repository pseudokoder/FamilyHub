"""ApiError — the one exception the JSON API speaks.

WHY a dedicated exception (and why it lives in the SERVICE layer, not the route
layer): services enforce the business rules — "sex must be one of M/F/X/U",
"that place doesn't exist". When a rule is broken they ``raise ApiError(...)``
with a human message + the right HTTP status, and the /api blueprint's one error
handler turns it into a clean JSON body. This keeps every route thin (no
sprawling try/except) and every error shape identical across the whole API —
which is exactly what makes the contract trustworthy for Cowork (WP3) and for v2.

It lives here (services/) rather than in routes/ so services can raise it without
importing anything from the route layer — dependencies point one way, routes →
services → models, never back (the layered-architecture rule in CLAUDE.md).

v2 mapping: a ``ResponseStatusException`` / a ``@ControllerAdvice`` exception in
Spring Boot.
"""


class ApiError(Exception):
    """A problem the caller can fix: bad input (400), not allowed (403), or not
    found (404). ``fields`` optionally names which inputs were wrong, so a form
    can highlight them."""

    def __init__(self, message, status=400, fields=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.fields = fields
