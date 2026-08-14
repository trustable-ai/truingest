# TruIngest — Document Ingestion Pipeline

Turn a PDF into clean, chunked training data, one visible step at a time.

Upload a document and walk it through extraction, cleaning, chunking and export.
Each stage is an accordion section you can open to see exactly what came out of
it before deciding to run the next one — nothing happens in a black box.

![TruIngest](screenshot.png)

## The pipeline

Add a document, then work down the five steps.

**Upload** — pick a PDF. Anything else is refused. The file is previewed in place
so you can confirm you grabbed the right one.

**Extract** — the PDF is sent through a Tika server, which pulls out its text.
The extracted text appears in the accordion, and both the original PDF and the
text are kept in object storage.

**Clean** — the extracted text is tidied up: page numbers (lines containing
nothing but a number) are dropped, `Figure 12`-style caption lines are removed,
table-of-contents lines trailing off into dot leaders and a page number are
stripped, and stray non-printable characters go. Runs of blank lines collapse to
one, so paragraph boundaries survive. Output is UTF-8, and shown in full.

**Chunk** — the cleaned text is split into chunks on blank lines, one chunk per
paragraph. You see each chunk separately, and the count. The set is saved as a
JSONL file.

**Export** — generates a download link for the result.

Steps run in order, and each one needs the previous one's output. Re-running an
earlier step clears everything after it, so you never end up looking at chunks
that belong to text you have since re-cleaned. Every step reports success or
failure as it happens, with the reason when something goes wrong.

## How it is put together

A React and TypeScript single-page app (Vite, Tailwind CSS, shadcn/ui) over
Python actions on Apache OpenServerless:

| Endpoint | Does |
|---|---|
| `POST /api/my/rag/ingest` | store the PDF, extract its text with Tika, store the text |
| `POST /api/my/rag/clean` | apply the cleaning rules, return UTF-8 text |
| `POST /api/my/rag/chunk` | split on blank lines, save the chunks as JSONL |
| `POST /api/my/rag/download` | produce a download URL for a stored file |

**S3** holds everything the pipeline produces — the uploaded PDF, the extracted
text, the chunk file and the exports. Download links are public URLs when a
public S3 endpoint is configured, otherwise signed URLs valid for an hour. Text
extraction talks to a **Tika** service running in the cluster.

Two further actions go beyond what the interface currently calls: `rag/process`
and `rag/export` send chunks to an OpenAI-compatible model (OpenAI or a local
Ollama) and turn each one into a question-and-answer pair, producing a JSONL
conversation file suitable for fine-tuning. The pipeline's Export button uses the
simpler download path today.

The repository also carries the platform's starter examples under
`packages/hello/` (echo, SQL, Redis, S3, streaming, LLM, vector DB) and a chat
action under `packages/v1/`. They are not part of the ingestion flow.

## Getting started

```bash
npm install
npm run dev
```

The backend needs S3 configured and a reachable Tika service; the Q&A actions
additionally need an OpenAI-compatible endpoint. Add a document from the home
page and start with Upload.
