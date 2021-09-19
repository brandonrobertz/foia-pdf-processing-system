#!/usr/bin/env python
import csv
from django.core.management.base import BaseCommand
import ftfy

from documents.models import Agency, Document, ProcessedDocument


class Command(BaseCommand):
    help = """
    Looks through all the completed/csv records and counts the number
    of rows. This is just to give an approximate number of total IA
    records we've processed.
    """

    def handle(self, *args, **options):
        # Document.objects.filter(status__in=['complete', 'awaiting-cleaning', 'awaiting-csv', 'awaiting-reading', 'awaiting-extraction', 'supporting-document', 'case-doc', 'unchecked']).count()
        n_complete = Document.objects.filter(status='complete').count()
        print(f"{n_complete} completed responsive documents")

        complete_recs = ProcessedDocument.objects.filter(
            file__endswith=".csv", status__in=[
                'complete',
                'awaiting-cleaning',
            ]
        )
        n_complete_recs = complete_recs.count()
        print(f"{n_complete_recs} CSVs built from responsive documents")
        n_csv_rows = 0
        for pdoc in complete_recs:
            with pdoc.file.open(mode='r') as f:
                try:
                    reader = csv.reader(f)
                    for row in reader:
                        n_csv_rows += 1
                except Exception as e:
                    print("While reading file:", pdoc.file.name)
                    print("ProcessedDocument:", pdoc)
                    raise e
        print(f"{n_csv_rows} total IA records processed")
