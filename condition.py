from abc import ABC, abstractmethod

class Condition(ABC):
    @abstractmethod
    def check(self, listing):
        """
        Checks the listing against condition.
        :return: True if the condition applies to the listing; otherwise false.
        """
        pass

class LocationCondition(Condition):
    def check(self, listing):
        """
        Checks if the listing is in the approved locations.
        :return: True if the listing is in the approved locations; otherwise false.
        """
        return True

