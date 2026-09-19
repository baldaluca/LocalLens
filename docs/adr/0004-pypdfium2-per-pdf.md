# ADR 0004 — pypdfium2 for PDF rendering

Preferred over `pdf2image`/Poppler (external system binary, common failure on
Windows) and over `PyMuPDF` (AGPL-3.0 or paid). `pypdfium2` is a self-contained pip
package with prebuilt wheels for Linux/Windows and a permissive license.
