from rest_framework.permissions import BasePermission

from oysloecore.sysutils.constants import UserType


class IsSuperuser(BasePermission):
    """
    Allows access only to superusers.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser
    
class IsStaffAdmin(BasePermission):
    """
    Allows access only to staff/admin members.
    """
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and (user.is_staff or user.user_type == UserType.ADMIN.value)

class IsVendor(BasePermission):
    """
    Allows access only to vendors.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == UserType.VENDOR.value

class IsRider(BasePermission):
    """
    Allows access only to riders.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == UserType.RIDER.value
    
class IsBuyer(BasePermission):
    """
    Allows access only to buyers.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == UserType.BUYER.value
    
class AnyAuthUser(BasePermission):
    """
    Allows access to any authenticated user.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated
