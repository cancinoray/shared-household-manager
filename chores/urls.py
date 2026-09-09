from django.urls import path

from . import views

app_name = "chores"

urlpatterns = [
    path("", views.home, name="home"),
    path("board/", views.board, name="board"),
    path(
        "chores/<int:pk>/complete/",
        views.chore_complete,
        name="chore_complete",
    ),
]
