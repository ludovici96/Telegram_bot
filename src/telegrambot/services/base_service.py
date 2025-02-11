import logging

class BaseService:
    """Base class for all services"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
