from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("", views.feed, name="feed"),
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    
    # Profiles & Friends (edit MUST come before <str:username> or Django treats "edit" as a username)
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/<str:username>/", views.profile_view, name="profile_view"),
    path("password/change/", views.change_password, name="change_password"),
    path("friend-request/send/<str:username>/", views.send_friend_request, name="send_friend_request"),
    path("friend-request/<int:request_id>/accept/", views.accept_friend_request, name="accept_friend_request"),
    path("friend-request/<int:request_id>/reject/", views.reject_friend_request, name="reject_friend_request"),
    path("friend-request/<int:request_id>/cancel/", views.cancel_friend_request, name="cancel_friend_request"),
    path("friend-requests/", views.friend_requests, name="friend_requests"),
    path("friends/<str:username>/", views.friends_list, name="friends_list"),
    path("block/<str:username>/", views.block_user, name="block_user"),
    path("unblock/<str:username>/", views.unblock_user, name="unblock_user"),
    path("unfriend/<str:username>/", views.unfriend_user, name="unfriend_user"),
    path("settings/", views.settings_view, name="settings"),

    # Posts & Reactions & Comments
    path("post/<int:post_id>/react/", views.react_to_post, name="react_to_post"),
    path("post/<int:post_id>/comment/", views.add_comment, name="add_comment"),
    path("comment/<int:comment_id>/like/", views.like_comment, name="like_comment"),
    
    # Messaging
    path("messages/", views.inbox, name="inbox"),
    path("messages/<str:username>/", views.chat_room, name="chat_room"),
    path("api/messages/<str:username>/", views.get_messages_ajax, name="get_messages_ajax"),
    
    # Notifications & Search & Moderation
    path("notifications/", views.notifications_list, name="notifications"),
    path("search/", views.search_view, name="search"),
    path("report/post/<int:post_id>/", views.report_post, name="report_post"),
    path("report/user/<str:username>/", views.report_user, name="report_user"),
    path("moderation/reports/", views.admin_reports, name="admin_reports"),
    path("moderation/resolve/<int:report_id>/", views.resolve_report, name="resolve_report"),
    
    # Stories
    path("story/create/", views.create_story, name="create_story"),
    path("story/<int:story_id>/delete/", views.delete_story, name="delete_story"),
    path("api/search-music/", views.search_music, name="search_music"),
    path("api/post/<int:post_id>/likers/", views.get_post_likers, name="get_post_likers"),
    path("api/story/<int:story_id>/viewers/", views.get_story_viewers, name="get_story_viewers"),
    path("api/update-profile-pic/", views.update_profile_pic, name="update_profile_pic"),
    path("reels/", views.reels_view, name="reels"),

    path("story/<int:story_id>/like/", views.like_story, name="like_story"),
    path("api/generate-caption/", views.generate_ai_caption, name="generate_ai_caption"),
    path("post/<int:post_id>/delete/", views.delete_post, name="delete_post"),
    path("story/<int:story_id>/view/", views.record_story_view, name="record_story_view"),
    path("story/<int:story_id>/reply/", views.reply_to_story, name="reply_to_story"),
    path("my-posts/", views.my_posts, name="my_posts"),
    path("saved-posts/", views.saved_posts, name="saved_posts"),
    path("post/<int:post_id>/save/", views.save_post, name="save_post"),
    path("post/<int:post_id>/unsave/", views.unsave_post, name="unsave_post"),
    
]