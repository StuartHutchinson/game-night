from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("e/<str:event_id>/", views.event_page, name="event"),
    path("e/<str:event_id>/join/", views.join, name="join"),
    path("e/<str:event_id>/leave/", views.leave, name="leave"),
    path("e/<str:event_id>/games/add/", views.game_add, name="game_add"),
    path("e/<str:event_id>/games/<int:copy_id>/remove/", views.game_remove, name="game_remove"),
    path("e/<str:event_id>/interest/", views.interest, name="interest"),
    path("manage/<str:admin_token>/", views.manage, name="manage"),
]
