FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

# Copy app code
COPY . ${LAMBDA_TASK_ROOT}/

# For local dev (non-Lambda), use uvicorn
# For Lambda, handler is set via AWS config
CMD ["main.handler"]
