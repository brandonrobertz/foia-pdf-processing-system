# FOIA Records Processing System

A Django app that provides a workflow for managing FOIA response records,
converting PDF to CSV and data cleaning

This assumes you'll be using [FOIAmail](https://github.com/bettergov/foiamail)
to manage and gather responsive records (not necessary, though). Data from
FOIAmail comes across in this directory structure:

    data/
        agency_attachments/
            Agency Name One/
                request-file-1.pdf
            Another Agency Name/
                another-record-here.pdf

This project also assumes that you'll be extracting structured data (CSV
format) from PDFs, Word Documents, Excel spreadsheets, email archives using
the methods found in `extractor.template.sh`. This script has commands for
turning records from PDF, DOC/X, XLSX, EML, scanned images into CSVs.

Eventually, I'd like to pull this functionality into this application so users
can directly rotate, OCR, split, extract and clean data from PDFs/documents in
one place.
