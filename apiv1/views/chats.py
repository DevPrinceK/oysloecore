from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from apiv1.models import ChatRoom


class GetChatroomIdAPI(APIView):
    '''API to get or create a chatroom between two users'''
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        '''
        Get the chatroom ID between the current user and 
        the other user if it exists, else create one
        '''
        current_user = request.user
        other_user_email = request.query_params.get('email')
        try:
            other_user = User.objects.get(email=other_user_email)
            # get the chatroom where both users are members
            chatroom = ChatRoom.objects.filter(members__in=[current_user, other_user]).first()
            if chatroom:
                return Response({"chatroom_id": chatroom.room_id}, status=status.HTTP_200_OK)
            else:
                # create a new chatroom if it doesn't exist
                chatroom = ChatRoom.objects.create(members=[current_user, other_user])
                return Response({"chatroom_id": chatroom.room_id}, status=status.HTTP_200_OK)
        except User.DoesNotExist:

            return Response({"error": "User not found", "message": "Cannot find user with the provided email."}, status=status.HTTP_404_NOT_FOUND)