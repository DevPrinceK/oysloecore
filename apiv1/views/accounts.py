import random
import time
from uuid import uuid4
from django.contrib.auth import login
from knox.models import AuthToken
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import OTP, User
from apiv1.serializers import ChangePasswordSerializer, LoginSerializer, RegisterUserSerializer, ResetPasswordSerializer, UserSerializer

class LoginAPI(APIView):
    '''Login api endpoint'''
    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginSerializer

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

    def get(self, request, *args, **kwargs):
        '''Use this endpoint to send OTP to the user'''
        email = request.query_params.get('email')
        if not email:
            return Response({'error': 'email number is required'}, status=status.HTTP_400_BAD_REQUEST)
        code = random.randint(1000, 9999)
        try:
            otp = OTP.objects.filter(email=email).first()
            if otp:
                otp.delete()
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            otp = OTP.objects.create(email=email, otp=code)
            otp.send_otp_to_user()
        except Exception as e:
            return Response({'error': 'Failed to send OTP'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'message': 'OTP sent successfully'}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        otp = request.data.get('otp')
        if not otp:
            return Response({'error': 'OTP is required'}, status=status.HTTP_400_BAD_REQUEST)
        otp = OTP.objects.filter(email=email, otp=otp).first()
        if not otp:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
        if otp.is_expired():
            return Response({'error': 'OTP has expired'}, status=status.HTTP_400_BAD_REQUEST)
        otp.delete()
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        user.email_verified = True
        user.phone_verified = True
        user.save()
        return Response({'message': 'OTP verified successfully'}, status=status.HTTP_200_OK)
    

class ResetPasswordAPIView(APIView):
    '''API endpoint to reset user password'''

    permission_classes = (permissions.AllowAny,)
    serializer_class = ResetPasswordSerializer

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

    def get(self, request, *args, **kwargs):
        '''Get user profile for the logged in user'''
        user = request.user
        return Response(self.serializer_class(user).data)
    
    def put(self, request, *args, **kwargs):
        '''Update user profile for the logged in user'''
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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

    def get(self, request, *args, **kwargs):
        '''Get user preferences for the logged in user'''
        user = request.user
        return Response(self.serializer_class(user).data)

    def put(self, request, *args, **kwargs):
        '''Update user preferences for the logged in user'''
        user = request.user
        serializer = self.serializer_class(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)