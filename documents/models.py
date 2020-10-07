import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

from .util import STATUS_NAMES, STATUS_SCORES, document_file_path


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
        blank=True, null=True,
        help_text="The original file sent by the agency. This shouldn't need to be changed."
    )
    current_file = models.FileField(
        upload_to=document_file_path,
        blank=True, null=True,
        help_text="The current processed version of the file."
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
        constraints = [
            models.UniqueConstraint(
                fields=('agency','file'),
                name='unique-agency-file'
            )
        ]

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
        blank=True, null=True,
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
        constraints = [
            models.UniqueConstraint(
                fields=('document','file'),
                name='unique-processed-agency-file'
            )
        ]

    def save(self, *args, **kwargs):
        if self.status == self.document.status:
            return super().save(*args, **kwargs)
        doc_status = STATUS_SCORES[self.document.status]
        is_more_processed = doc_status > STATUS_SCORES[self.status]
        if is_more_processed:
            self.document.status = self.status
            self.document.save()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.file} ({self.status})"