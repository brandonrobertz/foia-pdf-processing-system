#!/usr/bin/env python
import csv
import codecs

from django.core.management.base import BaseCommand
import ftfy
import tablib

from documents.models import Agency, Document, ProcessedDocument


class Command(BaseCommand):
    help = """
    Looks through all the completed/csv records and counts the number
    of rows. This is just to give an approximate number of total IA
    records we've processed.
    """

    def handle(self, *args, **options):
        # Document.objects.filter(status__in=['complete',
        # 'awaiting-cleaning', 'awaiting-csv', 'awaiting-reading',
        # 'awaiting-extraction', 'supporting-document', 'case-doc',
        # 'unchecked']).count()
        n_complete = Document.objects.filter(status='complete').count()
        print(f"{n_complete} completed responsive documents")

        complete_docs = Document.objects.filter(
            status='complete',
        )
        n_complete_docs  = complete_docs.count()
        print(f"{n_complete_docs} CSVs built from responsive documents")
        filename_headers = tablib.Dataset(headers=[
            "Processed Doc Filename", "Header Name"
        ])
        n_csv_rows = 0
        all_rows = []
        for doc in complete_docs:
            # skip these, they don't have data, even if marked complete
            if doc.no_new_records:
                continue
            for pdoc in doc.processeddocument_set.filter(status="complete"):
                if not pdoc.file:
                    print("ERROR: skipping blank Processed Doc", pdoc, "Skipping.")
                    continue
                print("pdoc.file", pdoc.file)
                # with pdoc.file.open(mode='r', encoding='utf-8-sig') as f:
                with codecs.open(pdoc.file.path, encoding='utf-8-sig') as f:
                    # If file starts with (UTF-8 BOM): 0xEFBBBF4F
                    # >>> with codecs.open('excel_output.csv', encoding='utf-8-sig') as f:
                    # ...     reader = csv.reader(f)
                    # ...     rows = [row for row in reader]
                    try:
                        csv = tablib.Dataset().load(f, format="csv")
                        n_csv_rows += len(csv)
                        print("\trows;", len(csv))
                        for h in csv.headers:
                            filename_headers.append([pdoc.file.name, h])
                        for row in csv.dict:
                            all_rows.append(row)
                    # except UnicodeDecodeError as e:
                    #     ftfy.fix_encoding()
                    except Exception as e:
                        print("While reading file:", pdoc.file.name)
                        print("ProcessedDocument:", pdoc)
                        raise e

        with open("filename_headers.csv", "w") as f:
            f.write(filename_headers.csv)

        json_data = []
        # tablib Dataset
        data = None
        for row in all_rows:
            json_data.append(row)
            # row here is a fully flattened dict with all extracted values
            if data is None:
                data = tablib.Dataset(headers=row.keys())
            # if we need to add a new column we haven't seen yet, we need to
            # re-create the whole dataset with the new row
            # this tests if any of row's keys aren't in headers
            if set(row.keys()).difference(set(data.headers)):
                for h in row.keys():
                    if h in data.headers:
                        continue
                    data.append_col([None]*len(data), header=h)
            # build a properly ordered row consisting of all headers
            # in the proper order!
            values = []
            for h in data.headers:
                values.append(row.get(h))
            data.append(values)

        with open(f"all_records.csv", "w") as f:
            f.write(data.csv)

        print(f"{n_csv_rows} total IA records processed")
