The home page shows an ingestion page with an accordion to:

- upload a  document
- extract
- cleaning
- chunking
- export

You can expand the accordion to see the document and a button for cleaning, chunking, processing and downloading

Clicking upload uploads a pdf document.
Expanding the accordion you see a preview of it.

Clicking on export it will invoke the tika server 
on the uploaded document  available on tika.minipos.me to convert in text, show the exporte text in the accordion.

Clicking on cleaning will clean the document
invoking rag/clean and shows the cleaned document
in the accordion

Clicking on chunking will process the cleaned document
invoking rag/chunk and shows the chunked document
as a sequence of different chunks

Clicking on export will generate a signed url allowing
to download the result.

You can repeat the steps and if you execute a precedent steip it will clean all the successive steps



