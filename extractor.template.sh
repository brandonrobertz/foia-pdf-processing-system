#!/bin/bash

set -e

# Encrypted PDF (required for OCR)
qpdf --decrypt "${BASENAME}.pdf" "${BASENAME}.decrypted.pdf"

# OCR
# --rotate-pages-threshold 0 --rotate-pages
${OCRMYPDF} --tesseract-oem 1 --tesseract-pagesegmode 12 "${BASENAME}.pdf" "${BASENAME}.ocr.pdf"

# XLS/X
for FILE in *.xls*; do
    ${TOCSV} "${FILE}"
done

# DOC/X -> PDF
for FILE in *.doc*; do
    soffice --convert-to pdf ${FILE}
done

# Tables from DOCX
find ./ -iname '*.docx' -not -iname '._*' -exec ${DOCX2CSV} --format csv --sizefilter 0 {} \;

# MSG -> EML -> extract attachments
find -iname '*.msg' -exec ${MSG2EML} "{}" \;
${EXTACHMENT} -p ./ -o ./

BASENAME=2012_Log
java -jar ${TABULA_JAR} -f CSV --pages all -t -c  "${BASENAME}.pdf" > "${BASENAME}.csv"

BASENAME=2010_Log
java -jar ${TABULA_JAR} -f CSV --pages all -l -c  "${BASENAME}.pdf" > "${BASENAME}-p6.csv"
