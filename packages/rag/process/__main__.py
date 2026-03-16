#--kind python:default
#--web true
#--param S3_HOST "$S3_HOST"
#--param S3_PORT "$S3_PORT"
#--param S3_ACCESS_KEY "$S3_ACCESS_KEY"
#--param S3_SECRET_KEY "$S3_SECRET_KEY"
#--param S3_BUCKET_DATA "$S3_BUCKET_DATA"
#--param OPENAI_API_KEY "$OPENAI_API_KEY"
#--param OPENAI_BASE_URL "$OPENAI_BASE_URL"
#--param OPENAI_MODEL "$OPENAI_MODEL"
import process
def main(args):
  return { "body": process.process(args) }
