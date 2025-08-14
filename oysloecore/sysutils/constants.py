from enum import Enum


class UserType(Enum):
    '''Defines the usertypes allowed in the system'''
    BUYER = 'BUYER'
    VENDOR = 'VENDOR'
    RIDER = 'RIDER'
    ADMIN = 'ADMIN'
