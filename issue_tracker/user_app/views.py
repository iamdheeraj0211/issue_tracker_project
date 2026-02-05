from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.viewsets import ViewSet

from django.contrib.auth import authenticate, login
from rest_framework import status
from rest_framework.response import Response  
from rest_framework.permissions import AllowAny    

class UserViewSet(ViewSet):
    permission_classes = [AllowAny]
    def signup(self,request):
        username = request.data.get('username')
        # email = request.data.get('email')
        password = request.data.get('password')
        # print(request.data)
        if not username or not password :
            return Response(
                {"error": "Please provide username and password"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already taken"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.create_user(
                username=username,
                password=password
            )
            return Response(
                {"message": "User created successfully", "user_id": user.id}, 
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def signin(self,request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password :
            return Response(
                {"error": "Please provide username and password"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        user = authenticate(request, username=username, password=password)
        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {"message": "User signed in successfully",
                'token': token.key},    
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Invalid username or password"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
