import os
import subprocess


# Don't steal focus while PDF->Texting
os.environ["JAVA_TOOL_OPTIONS"] = "-Djava.awt.headless=true"


DOCUMENT_TEXT_PROG = lambda inp_file: [
    "java",
    "-jar",
    "../pdf_to_text_snowtide/target/PDFtoTextSnowtide-uber.jar",
    inp_file,
    "0.5"
]


def pdf2text(filepath, pages=None):
    """
    Convert a PDF, by path, to text. Optionally, only grab a subset of
    pages. Pages is a list of [start, end], zero indexed and inclusive.
    """
    args = DOCUMENT_TEXT_PROG(filepath)
    if isinstance(pages, str):
        args.append(pages)
    elif isinstance(pages, list):
        args.append("-".join([str(p) for p in pages]))

    # print("Extracting using args:", args)
    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        print("Bad return code:", result.returncode)
        print("PDF File:", filepath)
        return None

    text = result.stdout
    if isinstance(text, bytes):
        return text.decode("utf-8")
    return text
