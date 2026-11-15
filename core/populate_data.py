import os
import sys
import django
from django.utils import timezone
from django.core.files.base import ContentFile
import urllib.request
import random

# 1. Get the absolute path of the project root folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. Add the root folder to Python's search path so it can find 'config'
sys.path.append(BASE_DIR)

# 3. Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


from django.contrib.auth.models import User
from core.models import Post, Profile, Comment, FriendRequest
from django.db.models.signals import post_save

def create_dummy_data():
    print("Starting dummy data generation...")
    
    dummy_users = [
        {"username": "rahul_sharma", "first": "Rahul", "last": "Sharma", "bio": "Tech enthusiast & coder."},
        {"username": "priya_patel", "first": "Priya", "last": "Patel", "bio": "Designer. Coffee lover."},
        {"username": "arjun_singh", "first": "Arjun", "last": "Singh", "bio": "Fitness freak."},
        {"username": "sneha_rao", "first": "Sneha", "last": "Rao", "bio": "Bookworm & traveler."},
        {"username": "kiran_kumar", "first": "Kiran", "last": "Kumar", "bio": "Just here for the memes."},
    ]

    dummy_posts = [
        "Just finished a great workout! 💪",
        "Loving the new UI of this app! #Connectly",
        "Anyone up for a coffee run? ☕",
        "Just deployed my first Django project to Vercel! 🚀",
        "Weekend vibes 🌴",
    ]

    for user_data in dummy_users:
        # Create User
        if not User.objects.filter(username=user_data["username"]).exists():
            user = User.objects.create_user(
                username=user_data["username"],
                password="password123",
                email=f"{user_data['username']}@example.com",
                first_name=user_data["first"],
                last_name=user_data["last"]
            )
            
            # Update Profile Bio
            profile = user.profile
            profile.bio = user_data["bio"]
            profile.save()

            # Create a post for this user
            post = Post.objects.create(
                author=user,
                content=random.choice(dummy_posts),
                privacy="public"
            )
            print(f"Created user: {user.username}")

    print("Dummy data generation complete! You can now log in or view their posts.")
    print("Passwords for all users: password123")

if __name__ == "__main__":
    create_dummy_data()