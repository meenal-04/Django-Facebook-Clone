from django.contrib.auth.models import User
from .models import Profile, Notification

def sidebar_data(request):
    if request.user.is_authenticated:
        user_profile, _ = Profile.objects.get_or_create(user=request.user)
        friends_profiles = user_profile.friends.all()
        
        # Get 5 users excluding yourself, your friends, and blocked users
        recommended_users = User.objects.exclude(id=request.user.id)\
            .exclude(profile__in=friends_profiles)\
            .exclude(profile__in=user_profile.blocked.all())[:5]
            
        # Get unread notification count
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
            
        return {
            'recommended_users': recommended_users,
            'unread_notifications': unread_count, # <-- ADDED THIS
        }
    return {}