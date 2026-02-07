import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_anonymous_user = models.BooleanField(default=True)
    email = models.EmailField(blank=True, null=True, unique=True)

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        if self.email:
            return self.email
        return f"anon-{str(self.id)[:8]}"


class DeviceSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_id = models.UUIDField(unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    platform = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_device_session"

    def __str__(self):
        return f"{self.device_id} ({self.user})"
