import os
import requests
import random
import urllib.parse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models import Q, F
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.utils.timesince import timesince
from django.core.paginator import Paginator
from datetime import timedelta
from .models import Post, Profile, FriendRequest, Message, Comment, Notification, Report, Reaction, Story, StoryView, SavedPost
from .forms import ConnectlyPasswordChangeForm, ProfileEditForm, PostForm, CommentForm, SettingsForm

# ==========================================
# 1. AUTH & MAIN FEED
# ==========================================
def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Fakebook, {user.username}!")
            return redirect("feed")
    else:
        form = UserCreationForm()
    return render(request, "register.html", {"form": form})

# ==========================================
# 2. PROFILES & SETTINGS
# ==========================================

# 1. Update feed view to save music & preview
@login_required
def feed(request):
    user_profile, _ = Profile.objects.get_or_create(user=request.user)
    friend_users = [p.user for p in user_profile.friends.select_related("user")]
    
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.music = request.POST.get("music", "")[:200] or None
            post.music_preview = request.POST.get("music_preview", "") or None # SAVE THIS
            post.save()
            messages.success(request, "Post created successfully!")
            return redirect("feed")
        else:
            # THIS PRINTS THE ERROR TO YOUR TERMINAL IF UPLOAD FAILS
            print("POST FORM ERRORS:", form.errors) 
    else:
        form = PostForm()
        
    posts_list = Post.objects.select_related("author").prefetch_related(
        "reactions__user", "comments__author", "comments__likes", "comments__replies__author"
    ).filter(
        Q(privacy="public") | Q(privacy="friends", author__in=friend_users) | Q(author=request.user)
    ).distinct()
    
    from django.core.paginator import Paginator
    paginator = Paginator(posts_list, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    
    active_stories = Story.objects.filter(created_at__gte=timezone.now() - timedelta(hours=24)).select_related('author')
    friends_profiles = user_profile.friends.all()
    recommended_users = User.objects.exclude(id=request.user.id).exclude(profile__in=friends_profiles).exclude(profile__in=user_profile.blocked.all())[:5]
    unread_notifications = Notification.objects.filter(recipient=request.user, is_read=False).count()

    return render(request, "feed.html", {
        "posts": posts, "recommended_users": recommended_users, "active_stories": active_stories,
        "form": form, "unread_notifications": unread_notifications
    })

# 2. Update create_story to handle Video, Music & Preview
@login_required
def create_story(request):
    if request.method == "POST":
        media_file = request.FILES.get("image")
        music_name = request.POST.get("music", "")[:100]
        music_preview = request.POST.get("music_preview", "")
        
        if media_file:
            # Check file extension to set media type
            ext = media_file.name.split('.')[-1].lower()
            media_type = 'video' if ext in ['mp4', 'webm', 'mov'] else 'image'
            
            Story.objects.create(
                author=request.user, 
                image=media_file, 
                media_type=media_type,
                music=music_name or None, 
                music_preview=music_preview or None
            )
            messages.success(request, "Story added!")
    return redirect("feed")

# 3. Fix chat_room AJAX to show the story reply attachment
@login_required
def get_messages_ajax(request, username):
    other_user = get_object_or_404(User, username=username)
    messages_list = Message.objects.filter(Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user)).order_by("timestamp")
    Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)
    
    data = [{
        "sender": m.sender.username, 
        "content": m.content, 
        "is_me": m.sender == request.user, 
        "timestamp": m.timestamp.strftime("%H:%M"),
        "story_image": m.story.image.url if m.story and m.story.image else None # ADDED
    } for m in messages_list]
    return JsonResponse({"messages": data})


@login_required
def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=profile_user)
    is_own_profile = profile_user == request.user
    friendship_status, pending_request, incoming_request, is_blocked, has_blocked_me = None, None, None, False, False
    can_view_posts = True

    if not is_own_profile:
        my_profile, _ = Profile.objects.get_or_create(user=request.user)
        is_blocked = profile in my_profile.blocked.all()
        has_blocked_me = my_profile in profile.blocked.all()
        if not is_blocked and not has_blocked_me:
            if profile in my_profile.friends.all():
                friendship_status = "friends"
            else:
                pending_request = FriendRequest.objects.filter(from_user=request.user, to_user=profile_user, status=FriendRequest.STATUS_PENDING).first()
                incoming_request = FriendRequest.objects.filter(from_user=profile_user, to_user=request.user, status=FriendRequest.STATUS_PENDING).first()

    if is_blocked or has_blocked_me:
        posts = []
        friend_count = 0
        can_view_posts = False
    else:
        if profile.is_private and not is_own_profile and friendship_status != "friends":
            posts = []
            can_view_posts = False
        else:
            posts = Post.objects.filter(author=profile_user).select_related("author").prefetch_related("reactions").order_by("-created_at")
        friend_count = profile.friends.count()

    return render(request, "profile.html", {
        "profile_user": profile_user, "profile": profile, "posts": posts, "friend_count": friend_count,
        "is_own_profile": is_own_profile, "friendship_status": friendship_status, "pending_request": pending_request,
        "incoming_request": incoming_request, "is_blocked": is_blocked, "has_blocked_me": has_blocked_me,
        "can_view_posts": can_view_posts
    })

@login_required
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile_view", username=request.user.username)
    else:
        form = ProfileEditForm(instance=profile)
    return render(request, "edit_profile.html", {"form": form})

@login_required
def update_profile_pic(request):
    if request.method == "POST" and request.FILES.get('avatar'):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.avatar = request.FILES['avatar']
        profile.save()
        messages.success(request, "Profile picture updated!")
    return redirect('profile_view', username=request.user.username)

@login_required
def settings_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = SettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated.")
            return redirect("settings")
    else:
        form = SettingsForm(instance=profile)
    return render(request, "settings.html", {"form": form})

@login_required
def change_password(request):
    if request.method == "POST":
        form = ConnectlyPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully.")
            return redirect("profile_view", username=request.user.username)
    else:
        form = ConnectlyPasswordChangeForm(request.user)
    return render(request, "change_password.html", {"form": form})

# ==========================================
# 3. FRIENDS & BLOCKING
# ==========================================
@login_required
def send_friend_request(request, username):
    if request.method == "POST":
        to_user = get_object_or_404(User, username=username)
        my_profile, _ = Profile.objects.get_or_create(user=request.user)
        their_profile, _ = Profile.objects.get_or_create(user=to_user)
        
        if their_profile in my_profile.blocked.all() or my_profile in their_profile.blocked.all():
            messages.error(request, "Cannot send request. One of you has blocked the other.")
        elif their_profile in my_profile.friends.all():
            messages.info(request, "You are already friends.")
        elif not FriendRequest.objects.filter(from_user=request.user, to_user=to_user, status=FriendRequest.STATUS_PENDING).exists():
            FriendRequest.objects.create(from_user=request.user, to_user=to_user)
            Notification.objects.create(recipient=to_user, sender=request.user, notification_type='friend_request')
            messages.success(request, f"Friend request sent to {to_user.username}.")
    return redirect("profile_view", username=username)

@login_required
def accept_friend_request(request, request_id):
    if request.method == "POST":
        fr = get_object_or_404(FriendRequest, id=request_id, to_user=request.user, status=FriendRequest.STATUS_PENDING)
        with transaction.atomic():
            fr.status = FriendRequest.STATUS_ACCEPTED
            fr.save()
            my_profile, _ = Profile.objects.get_or_create(user=request.user)
            their_profile, _ = Profile.objects.get_or_create(user=fr.from_user)
            my_profile.friends.add(their_profile)
            their_profile.friends.add(my_profile)
            Notification.objects.create(recipient=fr.from_user, sender=request.user, notification_type='accept')
        messages.success(request, f"You are now friends with {fr.from_user.username}.")
    return redirect("friend_requests")

@login_required
def reject_friend_request(request, request_id):
    if request.method == "POST":
        fr = get_object_or_404(FriendRequest, id=request_id, to_user=request.user, status=FriendRequest.STATUS_PENDING)
        fr.status = FriendRequest.STATUS_REJECTED
        fr.save()
        messages.info(request, "Friend request rejected.")
    return redirect("friend_requests")

@login_required
def cancel_friend_request(request, request_id):
    if request.method == "POST":
        fr = get_object_or_404(FriendRequest, id=request_id, from_user=request.user, status=FriendRequest.STATUS_PENDING)
        fr.delete()
        messages.info(request, "Friend request cancelled.")
    return redirect("profile_view", username=request.user.username)

@login_required
def friend_requests(request):
    incoming = FriendRequest.objects.filter(to_user=request.user, status=FriendRequest.STATUS_PENDING).select_related("from_user")
    outgoing = FriendRequest.objects.filter(from_user=request.user, status=FriendRequest.STATUS_PENDING).select_related("to_user")
    return render(request, "friend_requests.html", {"incoming": incoming, "outgoing": outgoing})

@login_required
def friends_list(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=profile_user)
    friends = profile.friends.select_related("user").all()
    return render(request, "friends.html", {"profile_user": profile_user, "friends": friends})

@login_required
def block_user(request, username):
    if request.method == "POST":
        target_user = get_object_or_404(User, username=username)
        if target_user != request.user:
            my_profile, _ = Profile.objects.get_or_create(user=request.user)
            their_profile, _ = Profile.objects.get_or_create(user=target_user)
            with transaction.atomic():
                my_profile.blocked.add(their_profile)
                my_profile.friends.remove(their_profile)
                their_profile.friends.remove(my_profile)
                FriendRequest.objects.filter(Q(from_user=request.user, to_user=target_user) | Q(from_user=target_user, to_user=request.user)).delete()
            messages.success(request, f"You blocked {target_user.username}.")
    return redirect("profile_view", username=username)

@login_required
def unblock_user(request, username):
    if request.method == "POST":
        target_user = get_object_or_404(User, username=username)
        my_profile, _ = Profile.objects.get_or_create(user=request.user)
        their_profile, _ = Profile.objects.get_or_create(user=target_user)
        my_profile.blocked.remove(their_profile)
        messages.success(request, f"You unblocked {target_user.username}.")
    return redirect("profile_view", username=username)

@login_required
def unfriend_user(request, username):
    if request.method == "POST":
        target_user = get_object_or_404(User, username=username)
        if target_user != request.user:
            my_profile, _ = Profile.objects.get_or_create(user=request.user)
            their_profile, _ = Profile.objects.get_or_create(user=target_user)
            my_profile.friends.remove(their_profile)
            their_profile.friends.remove(my_profile)
            messages.success(request, f"You are no longer friends with {target_user.username}.")
    return redirect("profile_view", username=username)

# ==========================================
# 4. POSTS, REACTIONS, COMMENTS
# ==========================================
@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    if request.method == "POST":
        post.delete()
        messages.success(request, "Post deleted.")
    return redirect("feed")

@login_required
def react_to_post(request, post_id):
    if request.method == "POST":
        reaction_type = request.POST.get("reaction_type", "LIKE")
        post = get_object_or_404(Post, id=post_id)
        with transaction.atomic():
            reaction = Reaction.objects.filter(user=request.user, post=post).first()
            if reaction:
                if reaction.reaction_type == reaction_type:
                    reaction.delete()
                    action = "removed"
                else:
                    reaction.reaction_type = reaction_type
                    reaction.save()
                    action = "updated"
            else:
                Reaction.objects.create(user=request.user, post=post, reaction_type=reaction_type)
                action = "added"
                if post.author != request.user:
                    Notification.objects.create(recipient=post.author, sender=request.user, notification_type='like', post=post)

            reactions = post.reactions.all()
            total = reactions.count()
            summary = []
            for r in reactions.values('reaction_type').annotate(count=models.Count('id')).order_by('-count')[:3]:
                summary.append({'emoji': dict(Reaction.REACTION_CHOICES)[r['reaction_type']], 'count': r['count']})

            return JsonResponse({"status": "success", "action": action, "total": total, "summary": summary, "my_reaction": reaction_type if action != "removed" else None})
    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            parent_id = request.POST.get('parent_id')
            if parent_id:
                parent_comment = Comment.objects.get(id=parent_id)
                comment.parent = parent_comment
                if parent_comment.author != request.user:
                    Notification.objects.create(recipient=parent_comment.author, sender=request.user, notification_type='reply', post=post, comment=comment)
            else:
                if post.author != request.user:
                    Notification.objects.create(recipient=post.author, sender=request.user, notification_type='comment', post=post, comment=comment)
            comment.save()
            messages.success(request, "Comment added!")
    return redirect("feed")

@login_required
def like_comment(request, comment_id):
    if request.method == "POST":
        comment = get_object_or_404(Comment, id=comment_id)
        if request.user in comment.likes.all():
            comment.likes.remove(request.user)
            liked = False
        else:
            comment.likes.add(request.user)
            liked = True
            if comment.author != request.user:
                Notification.objects.create(recipient=comment.author, sender=request.user, notification_type='like', post=comment.post, comment=comment)
        return JsonResponse({"liked": liked, "total_likes": comment.likes.count()})
    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
def get_post_likers(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    reactions = Reaction.objects.filter(post=post).select_related('user')
    data = []
    for r in reactions:
        data.append({
            "username": r.user.username,
            "avatar": r.user.profile.avatar.url if r.user.profile.avatar else None,
            "initial": r.user.username[0].upper(),
            "profile_url": f"/profile/{r.user.username}/",
            "reaction": r.get_reaction_type_display()
        })
    return JsonResponse({"status": "success", "likers": data})

# ==========================================
# 5. MESSAGING
# ==========================================
@login_required
def inbox(request):
    sent = Message.objects.filter(sender=request.user).values_list('receiver', flat=True)
    received = Message.objects.filter(receiver=request.user).values_list('sender', flat=True)
    chat_partners = User.objects.filter(id__in=set(list(sent) + list(received)))
    return render(request, "inbox.html", {"chat_partners": chat_partners})

@login_required
def chat_room(request, username):
    other_user = get_object_or_404(User, username=username)
    if other_user == request.user: return redirect("inbox")
    Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)
    if request.method == "POST":
        content = request.POST.get("content")
        if content: Message.objects.create(sender=request.user, receiver=other_user, content=content)
        return redirect("chat_room", username=username)
    return render(request, "chat_room.html", {"other_user": other_user})


# ==========================================
# 6. NOTIFICATIONS, SEARCH, MODERATION
# ==========================================
@login_required
def notifications_list(request):
    notifs = Notification.objects.filter(recipient=request.user).select_related('sender', 'post', 'comment')
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, "notifications.html", {"notifications": notifs})

@login_required
def search_view(request):
    query = request.GET.get('q', '')
    users, posts = [], []
    if query:
        users = User.objects.filter(Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)).exclude(id=request.user.id)
        my_profile, _ = Profile.objects.get_or_create(user=request.user)
        friend_users = [p.user for p in my_profile.friends.all()]
        posts = Post.objects.filter(Q(content__icontains=query)).filter(Q(privacy="public") | Q(author__in=friend_users) | Q(author=request.user)).distinct()
    return render(request, "search_results.html", {"query": query, "users": users, "posts": posts})

@login_required
def report_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == "POST":
        reason = request.POST.get("reason")
        if reason:
            Report.objects.create(reporter=request.user, reported_post=post, reported_user=post.author, report_type='post', reason=reason)
            messages.success(request, "Post reported.")
    return redirect("feed")

@login_required
def report_user(request, username):
    reported_user = get_object_or_404(User, username=username)
    if request.method == "POST":
        reason = request.POST.get("reason")
        if reason:
            Report.objects.create(reporter=request.user, reported_user=reported_user, report_type='user', reason=reason)
            messages.success(request, "User reported.")
    return redirect("profile_view", username=username)

@login_required
def admin_reports(request):
    if not request.user.is_superuser: return redirect("feed")
    reports = Report.objects.filter(is_resolved=False).select_related('reporter', 'reported_user', 'reported_post')
    return render(request, "admin_reports.html", {"reports": reports})

@login_required
def resolve_report(request, report_id):
    if not request.user.is_superuser: return redirect("feed")
    report = get_object_or_404(Report, id=report_id)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "resolve":
            report.is_resolved = True
            report.save()
        elif action == "delete_post" and report.reported_post:
            report.reported_post.delete()
            report.is_resolved = True
            report.save()
    return redirect("admin_reports")

# ==========================================
# 7. STORIES & REELS & AI
# ==========================================


@login_required
def delete_story(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    if story.author == request.user:
        story.delete()
        messages.success(request, "Story deleted.")
    return redirect("feed")

@login_required
def record_story_view(request, story_id):
    if request.method == "POST":
        story = get_object_or_404(Story, id=story_id)
        if story.author != request.user:
            StoryView.objects.get_or_create(story=story, viewer=request.user)
        return JsonResponse({"status": "success"})
    return JsonResponse({"error": "Invalid"}, status=400)

@login_required
def like_story(request, story_id):
    if request.method == "POST":
        story = get_object_or_404(Story, id=story_id)
        if story.author == request.user:
            return JsonResponse({"error": "You cannot like your own story."}, status=400)
        if request.user in story.likes.all():
            story.likes.remove(request.user)
            liked = False
        else:
            story.likes.add(request.user)
            liked = True
            Notification.objects.create(recipient=story.author, sender=request.user, notification_type='story_like', story=story)
        return JsonResponse({"liked": liked, "total": story.likes.count()})
    return JsonResponse({"error": "Invalid"}, status=400)

@login_required
def reply_to_story(request, story_id):
    if request.method == "POST":
        story = get_object_or_404(Story, id=story_id)
        content = request.POST.get("content")
        if story.author != request.user and content:
            Message.objects.create(sender=request.user, receiver=story.author, content=content, story=story)
            return JsonResponse({"status": "success", "message": "Reply sent to chat!"})
        return JsonResponse({"status": "error", "message": "Cannot reply to your own story."}, status=400)
    return JsonResponse({"error": "Invalid"}, status=400)

@login_required
def get_story_viewers(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    if story.author != request.user: return JsonResponse({"error": "Unauthorized"}, status=403)
    viewers = StoryView.objects.filter(story=story).select_related('viewer').order_by('-viewed_at')
    data = []
    for view in viewers:
        data.append({
            "username": view.viewer.username,
            "avatar": view.viewer.profile.avatar.url if view.viewer.profile.avatar else None,
            "initial": view.viewer.username[0].upper(),
            "profile_url": f"/profile/{view.viewer.username}/",
            "time_ago": timesince(view.viewed_at) + " ago",
            "has_liked": view.viewer in story.likes.all() # NEW: checks if this viewer liked the story
        })
    return JsonResponse({"status": "success", "viewers": data})

@login_required
def search_music(request):
    query = request.GET.get("q", "top hits")
    try:
        response = requests.get(f"https://itunes.apple.com/search?term={query}&media=music&limit=6")
        data = response.json()
        tracks = []
        for track in data.get('results', []):
            if track.get('previewUrl'):
                tracks.append({
                    "name": track.get('trackName', 'Unknown'),
                    "artist": track.get('artistName', 'Unknown'),
                    "preview": track.get('previewUrl', ''),
                    "artwork": track.get('artworkUrl100', ''),
                })
        return JsonResponse({"tracks": tracks})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def generate_ai_caption(request):
    if request.method == "POST":
        if 'image' in request.FILES:
            image_file = request.FILES['image']
            api_key = os.getenv("HUGGINGFACE_API_KEY")

            # Remove spaces from API key if present
            if api_key:
                api_key = api_key.strip()

            if not api_key or api_key == "your_huggingface_token_here":
                # Return fallback caption if no valid API key
                thoughts = ["Sunset vibes and endless possibilities. 🌅", "Making memories that last. 📸", "Good vibes only. ✌️", "Living my best life! ✨", "Another day, another adventure. 🌟"]
                return JsonResponse({"caption": random.choice(thoughts), "source": "fallback"})

            API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base"
            headers = {"Authorization": f"Bearer {api_key}"}
            try:
                # Read image data
                image_data = image_file.read()
                response = requests.post(API_URL, headers=headers, data=image_data, timeout=20)

                # Check response status
                if response.status_code == 503:
                    # Model loading - try again or return fallback
                    return JsonResponse({"error": "AI is loading. Try again in a few seconds.", "fallback": random.choice(["Capturing the moment. 📷", "Life is beautiful. 🌸", "Today's mood. ✨"])}, status=503)

                if response.status_code != 200:
                    # API error - return fallback
                    thoughts = ["Feeling grateful today. 🙏", "Another beautiful day. ☀️", "Living in the moment. ⏳"]
                    return JsonResponse({"caption": random.choice(thoughts), "source": "fallback"})

                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    caption = result[0].get('generated_text', '')
                    if caption:
                        return JsonResponse({"caption": f"✨ {caption.capitalize()}", "source": "ai"})

                # If no valid result, return fallback
                thoughts = ["Making memories. 📸", "Good vibes only. ✌️", "Living my best life! 🌟"]
                return JsonResponse({"caption": random.choice(thoughts), "source": "fallback"})

            except requests.exceptions.Timeout:
                return JsonResponse({"error": "AI took too long to respond.", "fallback": "Perfect moment captured. 📷"}, status=503)
            except Exception as e:
                # Log error for debugging
                print(f"AI Caption Error: {str(e)}")
                thoughts = ["Feeling blessed. 🙏", "Another adventure. 🌍", "Today's vibe. ✨"]
                return JsonResponse({"caption": random.choice(thoughts), "source": "fallback"})

        # No image provided - return random caption
        thoughts = ["What's on your mind?", "Share your thoughts...", "How's your day going?", "Feeling grateful today. ✨"]
        return JsonResponse({"caption": random.choice(thoughts), "source": "random"})

    return JsonResponse({"error": "Invalid request method"}, status=400)

@login_required
def reels_view(request):
    # In a real app, you'd have a Reel model. For now, we simulate with real posts.
    posts = Post.objects.filter(image__isnull=False).select_related('author').order_by('-created_at')[:5]
    
    reels_data = []
    for post in posts:
        # If the post has a video file, use it. Otherwise, fallback to a sample video.
        video_url = post.image.url if post.image.name.lower().endswith(('.mp4', '.webm')) else "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
        
        reels_data.append({
            "url": video_url,
            "author": post.author.username,
            "caption": post.content[:50] + "...",
            "likes": post.total_likes(),
            "comments": post.comments.count()
        })
        
    if not reels_data:
        reels_data = [
            {"url": "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4", "author": "system", "caption": "Welcome to Reels! 🌌", "likes": 0, "comments": 0},
        ]

    return render(request, "reels.html", {"reels": reels_data})

@login_required
def my_posts(request):
    posts = Post.objects.filter(author=request.user).order_by("-created_at")
    return render(request, "my_posts.html", {"posts": posts})

@login_required
def save_post(request, post_id):
    if request.method == "POST":
        post = get_object_or_404(Post, id=post_id)
        SavedPost.objects.get_or_create(user=request.user, post=post)
        return JsonResponse({"status": "saved"})
    return JsonResponse({"error": "Invalid"}, status=400)

@login_required
def unsave_post(request, post_id):
    if request.method == "POST":
        post = get_object_or_404(Post, id=post_id)
        SavedPost.objects.filter(user=request.user, post=post).delete()
        return JsonResponse({"status": "unsaved"})
    return JsonResponse({"error": "Invalid"}, status=400)

@login_required
def saved_posts(request):
    saved = SavedPost.objects.filter(user=request.user).select_related('post', 'post__author')
    return render(request, "saved_posts.html", {"saved_posts": saved})