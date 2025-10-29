from enum import Enum


class UserType(Enum):
    '''Defines the usertypes allowed in the system'''
    BUYER = 'BUYER'
    VENDOR = 'VENDOR'
    RIDER = 'RIDER'
    ADMIN = 'ADMIN'


class ProductType(Enum):
    '''Defines the product types allowed in the system'''
    SALE = 'SALE'
    PAYLATER = 'PAYLATER'
    RENT = 'RENT'

class ProductStatus(Enum):
    '''Defines the product status allowed in the system'''
    VERIFIED = 'VERIFIED'
    ACTIVE = 'ACTIVE'
    SUSPENDED = 'SUSPENDED'
    DRAFT = 'DRAFT'
    PENDING = 'PENDING'
    REJECTED = 'REJECTED'

class UserLevelTrack(Enum):
    '''Defines the user levels allowed in the system. Default: Silver'''
    SILVER = 'SILVER'
    GOLD = 'GOLD'
    DIAMOND = 'DIAMOND'

class Regions(Enum):
    '''Defines the regions allowed in the system'''
    '''Ahafo, Ashanti, Bono East, Brong Ahafo, Central, Eastern, Greater Accra, North East, Northern, Oti, Savannah, Upper East, Upper West, Volta, Western, and Western North'''
    AHAFO = 'Ahafo'
    ASHANTI = 'Ashanti'
    BONO_EAST = 'Bono East'
    BRONG_AHAFO = 'Brong Ahafo'
    CENTRAL = 'Central'
    EASTERN = 'Eastern'
    GREATER_ACCRA = 'Greater Accra'
    NORTH_EAST = 'North East'
    NORTHERN = 'Northern'
    OTI = 'Oti'
    SAVANNAH = 'Savannah'
    UPPER_EAST = 'Upper East'
    UPPER_WEST = 'Upper West'
    VOLTA = 'Volta'
    WESTERN = 'Western'
    WESTERN_NORTH = 'Western North'
