from django.shortcuts import render

def navbar(request):
    return render(request, "navbar.html")