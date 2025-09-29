from enum import Enum


class UserType(Enum):
    '''Defines the usertypes allowed in the system'''
    BUYER = 'BUYER'
    VENDOR = 'VENDOR'
    RIDER = 'RIDER'
    ADMIN = 'ADMIN'


class UserLevelTrack(Enum):
    '''Defines the user levels allowed in the system. Default: Silver'''
    SILVER = 'SILVER'
    GOLD = 'GOLD'
    DIAMOND = 'DIAMOND'