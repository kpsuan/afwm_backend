"""
Common Custom Exceptions

Define custom exceptions for business logic errors.
"""

class AWFMException(Exception):
    """Base exception for all AWFM custom exceptions."""
    pass


class ValidationError(AWFMException):
    """Raised when validation fails."""
    pass


class PermissionDenied(AWFMException):
    """Raised when a user lacks permission for an action."""
    pass


class TeamError(AWFMException):
    """Base exception for team-related errors."""
    pass


class WitnessRestrictionError(TeamError):
    """Raised when witness role restrictions are violated."""
    pass


class InvitationError(TeamError):
    """Raised for invitation-related errors."""
    pass
