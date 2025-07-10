# authentication/views.py

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import LoginSerializer, RegisterSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        device_id = serializer.validated_data.get('device_id')
        
        user = authenticate(username=username, password=password)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            if device_id:
                user.device_id = device_id
                user.save()
            
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'message': 'Connexion réussie'
            })
        else:
            return Response({
                'error': 'Identifiants invalides'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token = Token.objects.create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
            'message': 'Compte créé avec succès'
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from .forms import RegisterForm

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard:home')
    else:
        form = RegisterForm()
    return render(request, 'auth/register.html', {'form': form})




# authentication/views.py (ajoute ces deux vues)
from django.shortcuts import render, redirect
from django.contrib import messages

def choose_role_view(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        if role == 'enqueteur':
            return redirect('authentication:login')
  # login normal
        elif role == 'juge':
            return redirect('analysis:report_list')  # vue existante
        elif role == 'invite':
            return redirect('authentication:guest_code')
    return render(request, 'authentication/choose_role.html')

def guest_code_view(request):
    if request.method == 'POST':
        code = request.POST.get('access_code')
        if code == 'passer1234':
            messages.success(request, 'Accès autorisé.')
            return redirect('analysis:report_list')  # redirection vers ta vue existante
        else:
            messages.error(request, 'Accès refusé : code invalide.')
    return render(request, 'authentication/guest_code.html')
