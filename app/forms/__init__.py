"""WTForms form classes — every HTML form in the app is defined here as code.

TEACHING NOTE: why classes instead of hand-written <form> tags?

  1. Validation runs SERVER-SIDE in one place (never trust the browser —
     anyone can edit HTML in DevTools; D315 Network and Security).
  2. Flask-WTF adds a hidden CSRF token to every form automatically, so
     another website can't trick a logged-in parent's browser into
     submitting our forms.
  3. Forgiving forms for free: on a validation error the page re-renders
     with the user's input intact plus a friendly message — nobody retypes
     a whole memory post because one field was off. That's an explicit
     elderly-first requirement in CLAUDE.md.

v2 mapping: each form class becomes a DTO with Bean Validation annotations
(@NotBlank, @Size) checked by @Valid in the controller.
"""
