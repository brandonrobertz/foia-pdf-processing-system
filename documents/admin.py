from django import forms
from django.contrib import admin
from django.db import models

from .forms import ProcessedDocumentForm, DocumentForm
from .models import Agency, Document, ProcessedDocument


class CRUDModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        obj.updated_by = request.user
        return super().save_model(request, obj, form, change)


class InlineDocument(admin.TabularInline):
    model = Document
    fields = (
        'status', 'file'
    )
    extra = 0


@admin.register(Agency)
class DocumentAdmin(CRUDModelAdmin):
    list_display = (
        'name',
    )
    search_fields = ('name',)
    inlines = (
        InlineDocument,
    )


class InlineProcessedDocument(admin.TabularInline):
    model = ProcessedDocument
    fields = (
        'status', 'file'
    )
    extra = 0


@admin.register(Document)
class DocumentAdmin(CRUDModelAdmin):
    list_display = (
        'view_page', 'agency', 'status', 'file',
    )
    list_filter = ('status','agency')
    list_editable = ('status',)
    search_fields = ('file', 'current_file',)
    inlines = (
        InlineProcessedDocument,
    )
    form = DocumentForm

    def view_page(self, obj):
        return 'View Page'
    view_page.short_description = "View Detail Page"


@admin.register(ProcessedDocument)
class ProcessedDocumentAdmin(CRUDModelAdmin):
    list_display = (
        'view_page', 'file', 'status', 'source_page', 'source_sheet',
    )
    list_filter = ('status','document__agency')
    list_editable = ('status',)
    search_fields = ('file', 'document',)
    form = ProcessedDocumentForm

    def view_page(self, obj):
        return 'View Page'
    view_page.short_description = "View Detail Page"
