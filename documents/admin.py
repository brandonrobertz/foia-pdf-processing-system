from django.contrib import admin

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
        'agency', 'status', 'file',
    )
    list_filter = ('status','agency')
    list_editable = ('status',)
    search_fields = ('file', 'current_file',)
    inlines = (
        InlineProcessedDocument,
    )

    # def details(self, obj):
    #     return mark_safe(f"<a href='{SITE_URL}/admin/app/model/{obj.pk}/change'>View Page</a>")
    # link_id.short_description = "View Detail Page"
    # link_id.allow_tags = True


@admin.register(ProcessedDocument)
class DocumentAdmin(CRUDModelAdmin):
    list_display = (
        'file', 'status', 'document',
    )
    list_filter = ('status','document__agency')
    list_editable = ('status',)
    search_fields = ('file', 'document',)


