from django.shortcuts import render


def claim_miles(request):
    return render(request, "miles/claim_miles.html")
