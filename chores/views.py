from django.shortcuts import render


def home(request):
    """Placeholder landing page; becomes a redirect to the board in a later task."""
    return render(request, "chores/home.html")
