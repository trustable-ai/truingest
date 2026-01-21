In the step Chunking the document in chunks 
using empty lines as chunk separator.

Save all the chunks on S3 as a single JSONL file
where each line is in format

{"assistant": <chunk> }

In the step Export provide a link as a signed url 
to download the resulting JSONL


