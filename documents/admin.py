from django import forms
from django.contrib import admin
from django.db import models

from .util import STATUS_NAMES
from .forms import ProcessedDocumentForm, DocumentForm, ProcessedInlineDocumentForm
from .models import Agency, Document, ProcessedDocument


class ExcludeListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'Exclude Statuses'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'exclude_status'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return STATUS_NAMES

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value():
            return queryset.exclude(status=self.value())
        return queryset


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
class AgencyAdmin(CRUDModelAdmin):
    list_display = (
        'name',
    )
    search_fields = ('name',)
    inlines = (
        InlineDocument,
    )

    class Meta:
        verbose_name = "Agency"
        verbose_name_plural = "Agencies"


class InlineProcessedDocument(admin.TabularInline):
    model = ProcessedDocument
    fields = (
        'status', 'file'
    )
    form = ProcessedInlineDocumentForm
    ordering = ('created_at',)
    extra = 0


@admin.register(Document)
class DocumentAdmin(CRUDModelAdmin):
    list_display = (
        'view_page', 'agency', 'status', 'file',
    )
    list_filter = ('status', ExcludeListFilter, 'agency')
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
