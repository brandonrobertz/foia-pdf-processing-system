import os

from cities.models import City, Subregion
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

from .util import STATUSES, STATUS_NAMES, STATUS_SCORES, document_file_path


class FieldCategory(models.Model):
    fieldname = models.CharField(
        max_length=100
    )
    value = models.CharField(
        max_length=100
    )
    # track number of uses, for sorting
    count = models.IntegerField(
        default=0
    )

    class Meta:
        verbose_name = "Field Category"
        verbose_name_plural = "Field Categories"
        ordering = ('fieldname', 'value')
        constraints = (
            models.UniqueConstraint(
                fields=('fieldname','value'),
                name='unique-field-value'
            ),
        )
        indexes = (
            models.Index(fields=('fieldname',)),
            models.Index(fields=('fieldname', 'value')),
        )

    def __str__(self):
        return f"{self.fieldname} => {self.value}"


class Agency(models.Model):
    name = models.CharField(
        max_length=300, unique=True
    )

    population = models.IntegerField(
        blank=True, null=True,
        help_text="Population of the city this agency serves (for sorting)"
    )

    completed = models.BooleanField(
        default=False
    )
    request_done = models.BooleanField(
        default=False
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

    @staticmethod
    def try_to_get_population(name):
        population = None
        city_name = name.replace(
            "Police Department", ""
        ).replace(
            "Marshals Office", ""
        ).replace(
            "Sheriff's Office", ""
        ).strip()
        city = City.objects.filter(
            region__name="Washington", name=city_name
        ).first()
        if city:
            population = city.population

        if not city and 'County' in name:
            county_name = name.replace(
                "Sheriff's Office", ""
            ).strip()
            county = Subregion.objects.filter(
                name=county_name,
                region__code='WA'
            ).first()
            if county:
                cities = county.cities.all()
                population = sum([c.population for c in cities])

        # based on approx student counts
        if not city and city_name == "Eastern Washington University":
            population =  12633
        if not city and city_name == "Western Washington University":
            population = 16142
        if not city and city_name == "University of Washington":
            population = 47571
        # typo ... :/
        if not city and city_name  == "Central Washington University Washington":
            population = 12342
        # not in cities DB for some reason
        if not population and city_name == "Sedro-Wooley":
            population = 10540
        if not population and city_name == "Bainbridge":
            population = 23025
        if not population and city_name == "Lakewood":
            population = 58163
        if not population and city_name == "Sunnyside":
            population = 15858
        # county
        if city_name == "King County":
            population = 2252782
        return population

    def save(self, *args, **kwargs):
        if not self.population:
            population = Agency.try_to_get_population(self.name)
            if population:
                self.population = population
        return super().save(*args, **kwargs)


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

    no_new_records = models.BooleanField(
        default=False,
        help_text=(
            "Check this if this document contains no new records. This "
            "shortcuts all processed document checking for completion status "
            "anb marks this document as complete (no parsing required)"
        )
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

    related = models.ManyToManyField(
        'self',
        blank=True,
        help_text="This document is related to (or part of) another document/incident"
    )

    @property
    def completed_files(self):
        """
        Find and return the most processed (furthest along in conversion to
        final format) version(s) of this original responsive document. This
        returns an array since a single responsive document (multi-table XLSX
        for example) can result in multiple final CSVs.
        """
        return filter(
            lambda x: x.status == "complete",
            self.processeddocument_set.all()
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

    def save(self, *args, **kwargs):
        if self.no_new_records:
            self.status = "complete"
        return super().save(*args, **kwargs)


class ProcessedDocument(models.Model):
    """
    A processed version of a single file. There is a one-to-one relationship
    between a processed document and a document (provided by agency). Ideally,
    a processed document should be able to stand as a direct replacement for
    the original document in all cases.
    """
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
        # for status, test_fn in STATUSES.items():
        #     if test_fn(self.file.name):
        #         self.status = status
        #         break
        return super().save(*args, **kwargs)


class SyntheticDocument(models.Model):
    """
    A file created by us! This consists of merged CSVs, etc. One or many
    processed documents and documents can be linked to this type of document.
    Typically, this will be a "finalized" version of a set of documents (e.g.
    merged installments).
    """
    file = models.FileField(
        upload_to=document_file_path,
        max_length=500,
        blank=True, null=True,
        help_text="The file that we created."
    )

    documents = models.ManyToManyField(
        Document,
        blank=True,
        help_text="The original document(s) this file was based on"
    )

    processed_documents = models.ManyToManyField(
        ProcessedDocument,
        blank=True,
        help_text="The processed document(s) this file was based on"
    )

    completed = models.BooleanField(
        default="False",
        help_text=(
            "Is this document complete? Note: If this is checked then all "
            "the documents and processed documents linked are also considered "
            "complete."
        )
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='syntheticdocuments_created',
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='syntheticdocuments_updated',
    )

    def save(self, *args, **kwargs):
        # make sure all the documents/processed documents have the same
        # agencies
        agency = None
        for doc in self.documents.all():
            if agency is None:
                agency = doc.agency
            assert agency == doc.agency
        for pdoc in self.processed_documents.all():
            if agency is None:
                agency = pdoc.document.agency
            assert agency == pdoc.document.agency
        return super().save(*args, **kwargs)

    def __str__(self):
        text = "Synthetic doc"
        if self.completed:
            text = "Completed synthetic doc"
        if self.file:
            text += f" ({self.file})"
        n_documents = self.documents.count()
        n_processed_documents = self.processed_documents.count()
        if n_documents and n_processed_documents:
            text += f" ({n_documents} documents, {n_processed_documents} processed documents)"
        elif n_documents:
            text += f" ({n_documents} documents)"
        elif n_processed_documents:
            text += f" ({n_processed_documents} processed documents)"
        else:
            text += "(no source documents)"
        return text
