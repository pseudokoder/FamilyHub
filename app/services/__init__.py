"""The service layer — ALL business logic lives here, not in routes.

TEACHING NOTE: this is the middle layer of the three-layer architecture
CLAUDE.md requires, and it maps 1:1 to Spring Boot:

    Flask route (app/routes/)   ->  @Controller   "translate HTTP <-> Python"
    Service     (app/services/) ->  @Service      "the actual rules of the app"
    Model       (app/models/)   ->  @Repository   "talk to the database"

WHY bother for a small app? Because routes should be boring. A route grabs
input, calls ONE service function, picks a template or redirect. Everything
interesting — hashing passwords, validating images, enforcing rules — lives
here, where it can be unit-tested without faking an HTTP request, and where
v2 can copy it into a @Service class almost line by line.
(D284 Software Engineering calls this "separation of concerns.")
"""
