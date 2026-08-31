from django.db import models

from menus.models import Restaurant


class ImportDraft(models.Model):
    """An AI extraction waiting for review, so the review screen survives a reload."""

    STATUS_DRAFT = "draft"
    STATUS_SAVED = "saved"
    STATUS_DISCARDED = "discarded"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SAVED, "Saved"),
        (STATUS_DISCARDED, "Discarded"),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="import_drafts")
    data = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    page_count = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Import draft #{self.pk} for {self.restaurant} ({self.status})"
