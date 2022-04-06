#!/usr/bin/env python
"""
Here's a copy of the data structure expected by the NER labeler.
Any changes to this export routine needs to be reflected in the
JS side of the labeler. https://github.com/brandonrobertz/ner-labeler

{
  labels: [
    {
      label: "DDATE",
      description: 'Document date, e.g. "Dec 24, 2021"',
      color: "#f286ff",
    },
    {
      ...
    }
  ],
  version: VERSION,
  file_data: [
    {
      name: "Agency Name/path/to/file.pdf",
      segment: {
        index: 0,
        range: [1, 5]
      },
      has_labels: true,
      data: [{
        text: "word",
        id: 1
      },
      ...
      {
        text: "another",
        id: 99,
        label: "ALLEG"
      }]
    },
    ...
  ]
}
"""
import json

from django.core.management.base import BaseCommand
from eml_parser import eml_parser
import email
from html.parser import HTMLParser

from documents.models import Agency, Document, ProcessedDocument
from documents.pdf2text import pdf2text
from documents.util import STATUS_SCORES


VERSION = "2.0.1"
LABELS = [
  {
    "label": "DDATE",
    "description": 'Document date, e.g. "Dec 24, 2021"',
    "color": "#f286ff",
  },
  {
    "label": "IANO",
    "description": 'IA Number',
    "color": "#2df3df",
  },
  {
    "label": "OFF",
    "description": 'Begin subject officer, e.g. "Officer John Smith"',
    "color": "#1b9e77",
  },
  {
    "label": "OUT",
    "description": 'Begin outcome, e.g. "Written Reprimand"',
    "color": "#e6ab02",
  },
  {
    "label": "ALEG",
    "description": 'Begin allgation, e.g. "Misuse of property"',
    "color": "#6686e6",
  },
  {
    "label": "IDATE",
    "description": 'Incident date, e.g. "Dec 24, 2021"',
    "color": "#e7298a",
  },
]


SEGMENTABLE_STATUSES = [
    "awaiting-reading",
    "auto-extracted",
    "awaiting-extraction",
    "case-doc",
    "unchecked",
]


class Command(BaseCommand):
    help = """
    This exports auto-extractable PDF text, using their pre-segmented forms,
    for use with NER labeling (https://github.com/brandonrobertz/ner-labeler).
    """

    def add_arguments(self, parser):
        parser.add_argument('output_json', type=str)

    # NOTE: Sync'd with documents/views.py
    def agency_segmentable_pdocs(self, agency):
        return ProcessedDocument.objects.filter(
            # TODO: OR .eml and awaiting-reading OR .txt and awaiting-reading
            # and do a little processing on the .eml texts, cleaning them up a
            # little
            file__endswith=".ocr.pdf",
            document__agency=agency,
            document__status__in=SEGMENTABLE_STATUSES,
        ).order_by("-pages")

    def agency_segmentable_docs_pdocs(self, agency):
        """
        Get all the documents/processed documents ready for segmentation
        and possible OCR. NOTE: These are not sorted!

        TODO: Attach a page count to document and processed document
        and then sort that based on a DB value.
        """
        docs = Document.objects.filter(
            agency=agency, status__in=SEGMENTABLE_STATUSES
        )
        print("Total documents", docs.count())
        for document in docs:
            if document.no_new_records:
                print("Skipping new new records document")
                continue

            n_pdocs = document.processeddocument_set.count()
            # Look for Documents with no ProcessedDocument but are
            # marked awaiting-reading/etc (already OCR'd likely?)
            if not n_pdocs:
                print("Parsing single document", document)
                yield document
                continue

            # use the processed doc
            if n_pdocs == 1:
                pdoc = document.processeddocument_set.first()
                print("Parsing single processed document", pdoc)
                yield pdoc
                continue

            # get the top scoring pdocs (0 = most complete)
            best_score = 999
            top_scoring = []
            for pdoc in document.processeddocument_set.all():
                score = STATUS_SCORES[pdoc.status]
                if score < best_score:
                    best_score = score
                    top_scoring = [pdoc]
                elif score == best_score:
                    top_scoring.append(pdoc)
            
            for pdoc in top_scoring:
                print("Parsing one of many processed documents", pdoc)
                yield pdoc

    def clean_name(self, filename):
        return filename.replace(
            "agency_attachments/", ""
        ).replace(
            "/Users/brandon/Desktop/research/2020_churn_project/code/foia-pdf-processing-system/data/", ""
        )

    def handle(self, *args, **options):
        IGNORE_FILES = [
            "Issaquah Police Department/17-09679_Informal_Complaint (1).msg"
        ]

        data = {
            "labels": LABELS,
            "version": VERSION,
            "file_data": []
        }

        output_json = options["output_json"]

        agencies = Agency.objects.all()

        for agency in agencies:
            print("Parsing agency", agency)
            file_data_template = {
                "name": None,
                # "segment": {
                #     index: 0,
                #     range: [1, 5]
                # },
                # data_raw holds the raw text of the document with
                # whitespace, intending for it to be tokenized in the JS
                # side of things. the difference of tokenizing over there
                # being that it preserves whitespace unlike BERT
                # tokenization
                "data_raw": None,
                # NOTE: We're not using this here, but we can also
                # export a tokenized version like this
                "data": [
                    # {
                    #     "id": 1,
                    #     "text": "violation",
                    #     "LABEL": "ALLEG"
                    # }
                ],
            }

            for doc_or_pdoc in self.agency_segmentable_docs_pdocs(agency):
                cleaned_name = self.clean_name(doc_or_pdoc.file.name)
                print("Cleaned name", cleaned_name)

                if cleaned_name in IGNORE_FILES:
                    continue

                # TODO: convert to text using various methods based
                # on the file extension/type
                text = None
                if cleaned_name.endswith(".pdf"):
                    text = pdf2text(doc_or_pdoc.file.path)

                elif cleaned_name.endswith(".eml"):

                    class HTMLFilter(HTMLParser):
                        text = ""
                        def handle_data(self, data):
                            self.text += data

                    def html2text(data):
                        f = HTMLFilter()
                        f.feed(data)
                        return f.text

                    # doc_or_pdoc.file.seek(0)
                    msg = email.message_from_bytes(doc_or_pdoc.file.read())
                    parsed_raw = eml_parser.get_raw_body_text(msg)
                    text = parsed_raw[0][1]

                elif cleaned_name.endswith(".txt"):
                    text = doc_or_pdoc.file.read().decode("utf-8")

                # we can't handle these right now
                elif (cleaned_name.lower().endswith(".mp4") or
                      cleaned_name.lower().endswith(".mp3") or 
                      cleaned_name.lower().endswith(".m4a") or 
                      cleaned_name.lower().endswith(".wma") or 
                      cleaned_name.lower().endswith(".mov") or 
                      cleaned_name.lower().endswith(".wav")):
                    continue

                else:
                    print(f"Couldn't extract text from file: {cleaned_name}")
                    import IPython; IPython.embed(); import time; time.sleep(2)
                    # raise NotImplementedError(
                    #     f"Couldn't extract text from file: {cleaned_name}"
                    # )
                    continue

                if not hasattr(doc_or_pdoc, "incident_pgs") or not doc_or_pdoc.incident_pgs:
                    print("Converting whole doc")
                    file_data = file_data_template.copy()
                    file_data["name"] = cleaned_name
                    file_data["data_raw"] = text
                    data["file_data"].append(file_data)
                    continue

                # handle incident pages
                else:
                    for index, page_range in enumerate(doc_or_pdoc.incident_pgs):
                        print("Processing incident page", index, page_range)
                        segment_file_data = file_data_template.copy()
                        segment_file_data["name"] = cleaned_name
                        segment_file_data["segment"] = {
                            "index": index,
                            "range": page_range,
                        }
                        pdf_text = pdf2text(doc_or_pdoc.file.path, pages=page_range)
                        segment_file_data["data_raw"] = pdf_text
                        data["file_data"].append(segment_file_data)

        with open(output_json, "w") as f:
            f.write(json.dumps(data, indent=1))

        # agency_unprocessed_docs = Document.objects.filter(
        #     status__in=[
        #         "auto-extracted"
        #         "awaiting-reading",
        #         "awaiting-extraction",
        #         "case-doc",
        #         "unchecked",
        #     ],
        #     file__endswith=".pdf",
        #     # skip these, they don't have data, even if marked complete
        #     no_new_records=False,
        #     agency=agency,
        # )
