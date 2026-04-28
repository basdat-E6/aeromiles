from django.shortcuts import render


def register(request):
    return render(request, "authentication/register.html")


def login(request):
    return render(request, "authentication/login.html")
