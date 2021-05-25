from django import forms
from django.contrib import admin
from django.db import models
from django.db.models import Q
from django.utils.safestring import mark_safe

from .util import STATUS_NAMES
from .forms import ProcessedDocumentForm, DocumentForm, ProcessedInlineDocumentForm
from .models import (
    Agency, Document, ProcessedDocument, FieldCategory, SyntheticDocument
)


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
        return (('any-complete', 'Completed/Ignored', ),) + STATUS_NAMES

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value() == 'any-complete':
            return queryset.exclude(
                Q(status='complete') |
                Q(status='awaiting-cleaning') |
                Q(status='non-request') |
                Q(no_new_records=True)
            )
        elif self.value():
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
        'view_doc', 'status', 'file'
    )
    readonly_fields = (
        'view_doc',
    )
    extra = 0

    def view_doc(self, obj):
        link = f"/admin/documents/document/{obj.id}/change"
        return mark_safe(
            f'<a href="{link}" target="_blank">View</a>'
        )


class InlineSyntheticDocument(admin.TabularInline):
    model = SyntheticDocument
    extra = 0

    def view_doc(self, obj):
        link = f"/admin/documents/syntheticdocument/{obj.id}/change"
        return mark_safe(
            f'<a href="{link}" target="_blank">View</a>'
        )


@admin.register(Agency)
class AgencyAdmin(CRUDModelAdmin):
    list_display = (
        'name', 'population', 'unchecked', 'not_csv', 'dirty_csv',
        'status_done', 'total', 'pct_done', 'completed',
    )
    search_fields = ('name',)
    inlines = (
        InlineDocument,
    )

    #'complete', 'Complete'
    #'awaiting-cleaning', 'Awaiting final cleaning'
    #'awaiting-csv', 'Awaiting conversion to CSV'
    #'awaiting-reading', 'Awaiting reading/processing'
    #'awaiting-extraction', 'Awaiting extraction'
    #'non-request', 'Misc file/unrelated to response'
    #'exemption-log', 'Exemption log'
    #'unchecked', 'New/Unprocessed'

    def not_csv(self, obj):
        return obj.document_set.filter(status__in=[
            'awaiting-reading','awaiting-extraction', 'supporting-document',
            'exemption-log', 'non-request'
        ]).count()

    def dirty_csv(self, obj):
        return obj.document_set.filter(status__in=[
            'awaiting-cleaning',
        ]).count()

    def status_done(self, obj):
        return obj.document_set.filter(status__in=[
            'complete','exemption-log', 'non-request'
        ]).count()

    def pct_done(self, obj):
        n_completed = self.status_done(obj)
        n_total = self.total(obj)
        pct = int((n_completed / n_total) * 100)
        return f"{pct}%"

    def total(self, obj):
        return obj.document_set.count()

    def unchecked(self, obj):
        return obj.document_set.filter(status='unchecked').count()

    class Meta:
        verbose_name = "Agency"
        verbose_name_plural = "Agencies"


class InlineProcessedDocument(admin.TabularInline):
    model = ProcessedDocument
    fields = (
        'view_doc', 'status', 'file'
    )
    readonly_fields = (
        'view_doc',
    )
    form = ProcessedInlineDocumentForm
    ordering = ('created_at',)
    extra = 1

    def view_doc(self, obj):
        link = f"/admin/documents/processeddocument/{obj.id}/change"
        return mark_safe(
            f'<a href="{link}" target="_blank">View</a>'
        )


@admin.register(Document)
class DocumentAdmin(CRUDModelAdmin):
    list_display = (
        'view_page', 'agency', 'status', 'no_new_records', 'file',
        'agency__population',
    )
    list_filter = ('status', ExcludeListFilter, 'no_new_records', 'agency')
    list_editable = ('status',)
    search_fields = ('file',)
    inlines = (
        InlineProcessedDocument,
    )
    filter_vertical = ('related',)
    form = DocumentForm

    def view_page(self, obj):
        return 'View'
    view_page.short_description = "-"

    def agency__population(self, obj):
        if not obj or not obj.agency:
            return -1
        return obj.agency.population
    agency__population.admin_order_field  = 'agency__population'


@admin.register(ProcessedDocument)
class ProcessedDocumentAdmin(CRUDModelAdmin):
    list_display = (
        'view_page', 'file', 'status', 'source_page', 'source_sheet',
        'document__agency__population',
    )
    list_filter = ('status',)
    list_editable = ('status',)
    search_fields = ('file', 'document__file',)
    form = ProcessedDocumentForm

    def view_page(self, obj):
        return 'View Page'
    view_page.short_description = "View Detail Page"

    def document__agency__population(self, obj):
        if not obj or not obj.document or not obj.document.agency:
            return -1
        return obj.document.agency.population
    document__agency__population.admin_order_field  = 'document__agency__population'


@admin.register(SyntheticDocument)
class SyntheticDocumentAdmin(CRUDModelAdmin):
    filter_vertical = ('documents', 'processed_documents')


@admin.register(FieldCategory)
class FieldCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'fieldname', 'value',
    )
    list_filter = ('fieldname',)
    search_fields = ('fieldname', 'value',)
