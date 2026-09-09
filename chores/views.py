from django.http import HttpResponse


def home(request):
    """Placeholder landing page; replaced by the chore board in a later task."""
    return HttpResponse("Household Chore Rotation Tool")
