import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

from .util import STATUSES, STATUS_NAMES, STATUS_SCORES, document_file_path


class Agency(models.Model):
    name = models.CharField(
        max_length=300, unique=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='agencies_created',
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='agencies_updated',
    )

    class Meta:
        verbose_name = "Agency"
        verbose_name_plural = "Agencies"
        ordering = ('name',)

    def __str__(self):
        return self.name


class Document(models.Model):
    agency = models.ForeignKey(
        Agency, on_delete=models.SET_NULL,
        blank=True, null=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_NAMES,
        default=STATUS_NAMES[-1][0],
        help_text="Status of processing the response document",
    )

    file = models.FileField(
        upload_to=document_file_path,
		max_length=500,
        blank=True, null=True,
        help_text="The original file sent by the agency. This shouldn't need to be changed."
    )

    notes = models.TextField(
        null=True, blank=True,
        help_text="Any notes about this document"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='documents_created',
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='documents_updated',
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('agency','file'),
                name='unique-agency-file'
            ),
        )
        indexes = (
            models.Index(fields=('status',)),
        )
        ordering = ('file',)

    def __str__(self):
        return f"{self.file} ({self.status})"


class ProcessedDocument(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.SET_NULL,
        blank=True, null=True,
        help_text="The original document this processed version is extracted from"
    )

    file = models.FileField(
        upload_to=document_file_path,
		max_length=500,
        blank=True, null=True,
        help_text="The processed version of the original document"
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_NAMES,
        default=STATUS_NAMES[-1][0],
        help_text="Status of processing the response document",
    )

    source_page = models.CharField(
        max_length=20,
        blank=True, null=True,
        help_text="The source page(s) a CSV was created from in an original PDF"
    )

    source_sheet = models.CharField(
        max_length=300,
        blank=True, null=True,
        help_text="The source sheet a CSV was created from in an original XLS/X"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='processed_documents_created',
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='processed_documents_updated',
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('file',),
                name='unique-processed-file'
            ),
        )
        indexes = (
            models.Index(fields=('status',)),
        )
        ordering = ('file',)

    def __str__(self):
        return f"{self.file} ({self.status})"

    def save(self, *args, **kwargs):
        for status, test_fn in STATUSES.items():
            if test_fn(self.file.name):
                self.status = status
                break
        return super().save(*args, **kwargs)
