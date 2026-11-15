from django.contrib import admin
from .models import (
    Post, Profile, Message, FriendRequest, Comment, 
    Notification, Report, Reaction, Story, SavedPost
)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "location", "bio")
    filter_horizontal = ("friends", "blocked")

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "privacy", "created_at", "total_likes")
    list_filter = ("privacy", "created_at")
    search_fields = ("author__username", "content")

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "reaction_type")

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "post", "content", "created_at")

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "is_read", "timestamp")

@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "status")

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "sender", "notification_type", "is_read")

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("report_type", "reporter", "is_resolved")

@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ("author", "created_at")

@admin.register(SavedPost)
class SavedPostAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "saved_at")