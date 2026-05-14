"""
Analytics models for A/B testing.

Uses user_id as an integer field (not a ForeignKey) since the User model
lives in the recipe service. Trust is established via the internal service key.
"""
from django.db import models


class ABTestAssignment(models.Model):
    """
    Stores the variant assignment for a user in a specific A/B test.

    Each user gets assigned to exactly one variant per test, and this
    assignment is persistent (ensures consistent experience across visits).
    """
    user_id = models.IntegerField(
        db_index=True,
        help_text="The authenticated user's ID (from recipe service)"
    )
    test_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Name of the A/B test (matches tests.json)"
    )
    variant_id = models.CharField(
        max_length=50,
        help_text="The variant ID assigned to this user"
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this assignment was created"
    )

    class Meta:
        unique_together = ['user_id', 'test_name']
        indexes = [
            models.Index(fields=['test_name', 'variant_id']),
        ]

    def __str__(self):
        return f"user_{self.user_id} -> {self.test_name}:{self.variant_id}"


class ABTestEvent(models.Model):
    """
    Records events (impressions and conversions) for A/B tests.

    Event types:
    - 'impression': User viewed a page with the test variant
    - Custom events: 'create_recipe_click', 'recipe_created', etc.
    """
    user_id = models.IntegerField(
        db_index=True,
        help_text="The user's ID (from recipe service)"
    )
    test_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Name of the A/B test"
    )
    variant_id = models.CharField(
        max_length=50,
        help_text="The variant the user was assigned to"
    )
    event_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Type of event: 'impression' or custom event name"
    )
    path = models.CharField(
        max_length=500,
        blank=True,
        help_text="URL path where the event occurred"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional event metadata"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When this event occurred"
    )

    class Meta:
        indexes = [
            models.Index(fields=['test_name', 'event_type', 'created_at']),
            models.Index(fields=['user_id', 'test_name', 'event_type']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.test_name}:{self.variant_id} @ {self.created_at}"
