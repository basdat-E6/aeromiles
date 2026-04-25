from django.shortcuts import render

def navbar(request):
    return render(request, "base.html")

def register(request):
    return render(request, "register.html")

def login(request):
    return render(request, "login.html")