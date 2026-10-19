from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import LoginSerializer, RegisterSerializer, UserProfileSerializer


class RegisterView(APIView):
    """
    POST /api/v1/auth/register/
    Public endpoint. Creates a new user account.
    """

    permission_classes = []

    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(description="Account created successfully."),
            400: OpenApiResponse(description="Validation errors."),
        },
        summary="Register a new user",
        description="Create a new user account with name, email, and password.",
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "message": "Account created successfully.",
                    "user": {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Public endpoint. Returns JWT access and refresh tokens.
    """

    permission_classes = []

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful. Returns JWT access and refresh tokens."),
            400: OpenApiResponse(description="Invalid credentials."),
        },
        summary="Login with email and password",
        description="Authenticate using email and password. Returns a JWT access token and refresh token.",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            data = serializer.validated_data
            user = data["user"]
            return Response(
                {
                    "message": "Login successful.",
                    "user": {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                    },
                    "tokens": {
                        "access": data["access"],
                        "refresh": data["refresh"],
                    },
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    """
    GET /api/v1/auth/me/
    Authenticated endpoint. Returns the current user's profile.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UserProfileSerializer},
        summary="Get current user profile",
        description="Returns the profile of the currently authenticated user.",
    )
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
