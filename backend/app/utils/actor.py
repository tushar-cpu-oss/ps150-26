"""Authenticated actor recorded in chain of custody. Always derived from the verified JWT user."""


class Actor(str):
    """A str (the user's display name) that also carries the authenticated user id."""
    user_id: str = None

    def __new__(cls, name: str, user_id: str = None):
        obj = super().__new__(cls, name)
        obj.user_id = user_id
        return obj
