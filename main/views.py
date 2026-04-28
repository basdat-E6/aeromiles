from django.shortcuts import render


def navbar(request):
    return render(request, "base.html")
