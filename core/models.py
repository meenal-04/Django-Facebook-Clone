from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    cover_photo = models.ImageField(upload_to="covers/", blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    relationship_status = models.CharField(max_length=50, blank=True)
    is_private = models.BooleanField(default=False)
    friends = models.ManyToManyField("self", blank=True)
    blocked = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="blocked_by")

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

class Post(models.Model):
    PRIVACY_CHOICES = (("public", "Public"), ("friends", "Friends Only"))
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    content = models.TextField()
    image = models.ImageField(upload_to="posts/", blank=True, null=True)
    privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default="public")
    
    music = models.CharField(max_length=200, blank=True, null=True)
    music_preview = models.URLField(blank=True, null=True) # NEW
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author.username}: {self.content[:40]}"

    def total_likes(self):
        return self.reactions.count()

class Reaction(models.Model):
    REACTION_CHOICES = [
        ('LIKE', '👍'), ('LOVE', '❤️'), ('HAHA', '😂'),
        ('WOW', '😮'), ('SAD', '😢'), ('ANGRY', '😡'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES, default='LIKE')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'post'], name='unique_user_post_reaction')]

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    likes = models.ManyToManyField(User, related_name="liked_comments", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField()
    story = models.ForeignKey('Story', on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

class FriendRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"), (STATUS_ACCEPTED, "Accepted"), (STATUS_REJECTED, "Rejected"),
    ]
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_friend_requests")
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_friend_requests")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("from_user", "to_user")
        ordering = ["-created_at"]

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    story = models.ForeignKey('Story', on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

class Report(models.Model):
    REPORT_TYPES = (('post', 'Post'), ('user', 'User'))
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports_made")
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports_received", null=True, blank=True)
    reported_post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    report_type = models.CharField(max_length=10, choices=REPORT_TYPES)
    reason = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Story(models.Model):
    MEDIA_CHOICES = (('image', 'Image'), ('video', 'Video'))
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stories")
    image = models.FileField(upload_to="stories/") # Changed to FileField to support Video
    media_type = models.CharField(max_length=10, choices=MEDIA_CHOICES, default='image') # NEW
    music = models.CharField(max_length=100, blank=True, null=True)
    music_preview = models.URLField(blank=True, null=True) # NEW
    likes = models.ManyToManyField(User, related_name="liked_stories", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_active(self):
        return self.created_at >= timezone.now() - timedelta(hours=24)

class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="views")
    viewer = models.ForeignKey(User, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'viewer')

class SavedPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_posts")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="saved_by")
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} saved {self.post.id}"