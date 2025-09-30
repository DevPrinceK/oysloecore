from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from drf_spectacular.utils import extend_schema
from apiv1.serializers import PingResponseSerializer


class PingAPI(APIView):
    '''This view is used to check if the server is up and running'''
    @extend_schema(responses={200: PingResponseSerializer}, operation_id='ping')
    def get(self, request):
        '''This method is used to check if the server is up and running'''
        return Response({'message': 'pong'}, status=status.HTTP_200_OK)
    