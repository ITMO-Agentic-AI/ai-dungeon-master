class DungeonMasterException(Exception):
    pass


class InvalidActionException(DungeonMasterException):
    pass


class RulesViolationException(DungeonMasterException):
    pass


class StateValidationException(DungeonMasterException):
    pass
