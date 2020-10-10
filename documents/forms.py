import os
import uuid

from django import forms
from django.conf import settings
from django.db import models

from .models import Document, ProcessedDocument


class ViewableFile(forms.ClearableFileInput):
    template_name = 'forms/widgets/clearable_file_input.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if not value:
            return context
        path = os.path.join(
            settings.MEDIA_URL, value.name
        )
        context["widget"]["iframe_path"] = path
        _, ext = os.path.splitext(value.name)
        context["widget"]["iframe_ext"] = ext
        context["widget"]["iframe_id"] = uuid.uuid4()
        return context


class ViewableSelect(forms.Select):
    template_name = 'forms/widgets/viewable_select.html'
    option_template_name = 'forms/widgets/select_option.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        doc = Document.objects.get(pk=value)
        path = os.path.join(
            settings.MEDIA_URL, doc.file.name
        )
        context["widget"]["iframe_path"] = path
        _, ext = os.path.splitext(doc.file.name)
        context["widget"]["iframe_ext"] = ext
        context["widget"]["iframe_id"] = uuid.uuid4()
        return context


class AddNewField(forms.Textarea):
    template_name = 'forms/widgets/create_csv.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        return context


class DocumentForm(forms.ModelForm):
    add_new_csv = forms.CharField(
        required=False,
        widget=AddNewField()
    )

    class Meta:
        model = Document
        fields = (
            'agency',
            'file',
            'add_new_csv',
            'status',
            'notes',
            'created_by',
            'updated_by',
        )
        readonly_fields = (
            'created_at',
            'created_by',
            'updated_at',
            'updated_by',
        )
        widgets = {
            'file': ViewableFile(),
            'add_new_csv': AddNewField(),
        }


class ProcessedDocumentForm(forms.ModelForm):
    class Meta:
        model = ProcessedDocument
        fields = (
            'file',
            'status',
            'document',
            'source_page',
            'source_sheet',
            'created_by',
            'updated_by',
        )
        readonly_fields = (
            'created_at',
            'created_by',
            'updated_at',
            'updated_by',
        )
        widgets = {
            'file': ViewableFile(),
            'document': ViewableSelect(),
        }


class ProcessedInlineDocumentForm(forms.ModelForm):
    class Meta:
        model = ProcessedDocument
        fields = (
            'status', 'file'
        )
        widgets = {
            'file': ViewableFile(),
        }
