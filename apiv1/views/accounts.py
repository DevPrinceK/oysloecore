import random
import time
from uuid import uuid4
from django.contrib.auth import login
from knox.models import AuthToken
from rest_framework import permissions, status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from apiv1.serializers import (
    LoginSerializer, UserSerializer, RegisterUserSerializer,
    ChangePasswordSerializer, ResetPasswordSerializer, VerifyOTPGetRequestSerializer,
    VerifyOTPPostRequestSerializer, LoginResponseSerializer,
    RegisterUserResponseSerializer, GenericMessageSerializer, SimpleStatusSerializer,
    UserUpdateSerializer, AdminToggleUserSerializer, AdminDeleteUserSerializer,
    RedeemReferralResponseSerializer,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import OTP, User
from apiv1.serializers import ChangePasswordSerializer, LoginSerializer, RegisterUserSerializer, ResetPasswordSerializer, UserSerializer

class LoginAPI(APIView):
    '''Login api endpoint'''
    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginSerializer

    @extend_schema(request=LoginSerializer, responses={200: LoginResponseSerializer, 401: GenericMessageSerializer}, operation_id='login')
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            print(e)
            for field in list(e.detail):
                error_message = e.detail.get(field)[0]
                field = f"{field}: " if field != "non_field_errors" else ""
                response_data = {
                    "status": "error",
                    "error_message": f"{field} {error_message}",
                    "user": None,
                    "token": None,
                }
                return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)
        else:
            user = serializer.validated_data
       
        login(request, user)

        # REMOVE THE FOLLOW COMMENTS IF YOU DON'T WANT 
        # MULTIPLE LOGINS FOR THE SAME USER
        # Delete existing token
        # AuthToken.objects.filter(user=user).delete()
        return Response({
            "user": UserSerializer(user).data,
            "token": AuthToken.objects.create(user)[1],
        })


class RegisterUserAPI(APIView):
    '''Register User api endpoint'''
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterUserSerializer

    @extend_schema(request=RegisterUserSerializer, responses={200: RegisterUserResponseSerializer, 401: GenericMessageSerializer}, operation_id='register')
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            print(e)
            for field in list(e.detail):
                error_message = e.detail.get(field)[0]
                field = f"{field}: " if field != "non_field_errors" else ""
                response_data = {
                    "status": "error",
                    "error_message": f"{field} {error_message}",
                    "user": None,
                    "token": None,
                }
                return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)
        else:
            user = serializer.save()
            user.is_active = True
            user.save()
            return Response({
                "user": UserSerializer(user).data,
                "token": AuthToken.objects.create(user)[1],
            })
        

class LogoutAPIView(APIView):
    '''Logout API endpoint'''
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SimpleStatusSerializer

    @extend_schema(responses={200: SimpleStatusSerializer}, operation_id='logout')
    def post(self, request, *args, **kwargs):
        '''Logout user'''
        request.user.auth_token.delete()
        return Response({
            "status": "success",
            "message": "User logged out successfully",
        }, status=status.HTTP_200_OK)
    

class VerifyOTPAPI(APIView):
    '''Verify OTP api endpoint'''
    permission_classes = (permissions.AllowAny,)

    # Note: GET requests should not declare a request body. Use 'parameters' to document query params.
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='phone',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description='Phone number to which the OTP will be sent.'
            )
        ],
        responses={200: GenericMessageSerializer, 400: GenericMessageSerializer, 404: GenericMessageSerializer},
        operation_id='verify_otp_get'
    )
    def get(self, request, *args, **kwargs):
        '''Use this endpoint to send OTP to the user'''
        phone = request.query_params.get('phone')
        if not phone:
            return Response({'error': 'phone number is required'}, status=status.HTTP_400_BAD_REQUEST)
        code = random.randint(1000, 9999)
        try:
            otp = OTP.objects.filter(phone=phone).first()
            if otp:
                otp.delete()
            user = User.objects.filter(phone=phone).first()
            if not user:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            otp = OTP.objects.create(phone=phone, otp=code)
            otp.send_otp_to_user()
        except Exception as e:
            return Response({'error': 'Failed to send OTP'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'message': 'OTP sent successfully'}, status=status.HTTP_200_OK)

    @extend_schema(request=VerifyOTPPostRequestSerializer, responses={200: GenericMessageSerializer, 400: GenericMessageSerializer, 404: GenericMessageSerializer}, operation_id='verify_otp_post')
    def post(self, request, *args, **kwargs):
        phone = request.data.get('phone')
        otp = request.data.get('otp')
        if not otp:
            return Response({'error': 'OTP is required'}, status=status.HTTP_400_BAD_REQUEST)
        otp = OTP.objects.filter(phone=phone, otp=otp).first()
        if not otp:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
        if otp.is_expired():
            return Response({'error': 'OTP has expired'}, status=status.HTTP_400_BAD_REQUEST)
        otp.delete()
        user = User.objects.filter(phone=phone).first()
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        user.phone_verified = True
        user.phone_verified = True
        user.save()
        return Response({'message': 'OTP verified successfully'}, status=status.HTTP_200_OK)
    

class ResetPasswordAPIView(APIView):
    '''API endpoint to reset user password'''

    permission_classes = (permissions.AllowAny,)
    serializer_class = ResetPasswordSerializer

    @extend_schema(request=ResetPasswordSerializer, responses={200: SimpleStatusSerializer, 400: GenericMessageSerializer}, operation_id='reset_password')
    def post(self, request, *args, **kwargs):
        '''Reset user password'''
        serializer = self.serializer_class(data=request.data)
        print(f"Request data: {request.data}")
        # print(f"Serializer data: {serializer.data}")
        if serializer.is_valid():
            email = serializer.data.get('email')
            user = User.objects.filter(email=email).first()
            print(f"Email: {email}")
            print(f"User: {user}")
            if not email:
                return Response({'email': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not user:
                return Response({'email': 'User not found.'}, status=status.HTTP_400_BAD_REQUEST)
            if not user.email_verified:
                print(f"Email verified: {user.email_verified}")
                return Response({'email': 'Email not verified.'}, status=status.HTTP_400_BAD_REQUEST)
            if len(serializer.data.get('new_password')) < 1:
                print(f"New password: {serializer.data.get('new_password')}")
                return Response({'new_password': 'Password is too short.'}, status=status.HTTP_400_BAD_REQUEST)
            if not serializer.data.get('new_password') == serializer.data.get('confirm_password'):
                print(f"New password: {serializer.data.get('new_password')}")
                print(f"Confirm password: {serializer.data.get('confirm_password')}")
                return Response({'new_password': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(serializer.data.get('new_password'))
            user.save()
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        print(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserProfileAPIView(APIView):
    '''Get user profile'''
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    @extend_schema(responses={200: UserSerializer}, operation_id='user_profile_get')
    def get(self, request, *args, **kwargs):
        '''Get user profile for the logged in user'''
        user = request.user
        return Response(self.serializer_class(user).data)
    
    @extend_schema(request=UserUpdateSerializer, responses={200: UserSerializer, 400: GenericMessageSerializer}, operation_id='user_profile_put')
    def put(self, request, *args, **kwargs):
        '''Update user profile for the logged in user'''
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(request=AdminToggleUserSerializer, responses={200: UserSerializer, 400: GenericMessageSerializer, 401: GenericMessageSerializer}, operation_id='user_profile_post')
    def post(self, request, *args, **kwargs):
        '''Use this to disable/enable a user account. To be used by admins only'''
        user = request.user
        if user.is_superuser:
            culprit_id = request.data.get('id')
            account_status = request.data.get('is_active')
            if user.id == culprit_id:
                return Response({'message': 'You cannot disable your own account'}, status=status.HTTP_400_BAD_REQUEST)
            if not culprit_id:
                return Response({'message': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            if not (account_status == True or account_status == False):
                print(f"Account status: {account_status}")
                return Response({'message': 'Account status is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            culprit = User.objects.filter(id=culprit_id, deleted=False).first()
            if not culprit:
                return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            culprit.is_active = account_status == True
            culprit.save()
            return Response(UserSerializer(culprit).data)
        return Response({'message': 'You are not authorized to disable this account'}, status=status.HTTP_401_UNAUTHORIZED)
    
    @extend_schema(request=AdminDeleteUserSerializer, responses={200: GenericMessageSerializer, 400: GenericMessageSerializer, 401: GenericMessageSerializer}, operation_id='user_profile_delete')
    def delete(self, request, *args, **kwargs):
        '''Delete user account. To be used by admins only'''
        user = request.user
        if user.is_superuser:
            culprit_id = request.data.get('id')
            if user.id == culprit_id:
                return Response({'message': 'You cannot delete your own account'}, status=status.HTTP_400_BAD_REQUEST)
            if not culprit_id:
                return Response({'message': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            culprit = User.objects.filter(id=culprit_id, deleted=False).first()
            if not culprit:
                return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            culprit.deleted = True
            culprit.save()
            return Response({'message': 'User account deleted successfully'})
        return Response({'message': 'You are not authorized to delete this account'}, status=status.HTTP_401_UNAUTHORIZED)
    

class ChangePasswordAPIView(APIView):
    '''API endpoint to change user password'''

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ChangePasswordSerializer

    @extend_schema(request=ChangePasswordSerializer, responses={200: SimpleStatusSerializer, 400: GenericMessageSerializer}, operation_id='change_password')
    def post(self, request, *args, **kwargs):
        '''Change user password'''
        user = request.user
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            if not user.check_password(serializer.data.get('old_password')):
                return Response({'old_password': 'Wrong password.'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.data.get('new_password'))
            user.save()
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserPreferenceAPIView(APIView):
    '''API endpoint to get and update a user's preferences'''
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    @extend_schema(responses={200: UserSerializer}, operation_id='user_preferences_get')
    def get(self, request, *args, **kwargs):
        '''Get user preferences for the logged in user'''
        user = request.user
        return Response(self.serializer_class(user).data)

    @extend_schema(request=UserUpdateSerializer, responses={200: UserSerializer, 400: GenericMessageSerializer}, operation_id='user_preferences_put')
    def put(self, request, *args, **kwargs):
        '''Update user preferences for the logged in user'''
        user = request.user
        serializer = self.serializer_class(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RedeemReferralAPIView(APIView):
    """Redeem referral points in blocks of 2,500 => Ghc 500 per block."""
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = RedeemReferralResponseSerializer

    @extend_schema(responses={200: RedeemReferralResponseSerializer, 400: GenericMessageSerializer}, operation_id='redeem_referral_points')
    def post(self, request, *args, **kwargs):
        user = request.user
        result = user.redeem_points()
        if not result:
            return Response({"message": "Not enough points to redeem."}, status=status.HTTP_400_BAD_REQUEST)
        redeemed_points, cash_amount = result
        wallet = getattr(user, 'wallet', None)
        balance = wallet.balance if wallet else 0
        data = {
            "redeemed_points": redeemed_points,
            "cash_amount": cash_amount,
            "remaining_points": user.referral_points,
            "wallet_balance": balance,
        }
        return Response(data, status=status.HTTP_200_OK)