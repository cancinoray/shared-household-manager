from django.urls import path

from . import views

app_name = "chores"

urlpatterns = [
    path("", views.home, name="home"),
    path("board/", views.board, name="board"),
]
