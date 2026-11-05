# ClearKo API (OCR + job queue). NOT BUILD-TESTED: the author's machine has no Docker.
# Needs an NVIDIA GPU at run time: OCR on CPU takes minutes per page (see README).
#
#   docker build -t clearko-api backend
#   docker build --build-arg WITH_UZ=1 -t clearko-api backend     # + Uzbek (NLLB, non-commercial licence)
FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04

ARG WITH_UZ=0
ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 \
    HOME=/home/app PADDLE_PDX_CACHE_HOME=/home/app/.paddlex

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-pip libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv \
    && useradd --create-home --uid 10001 app
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN pip install ".[ocr,pdf,llm,api]" \
    && pip uninstall -y paddlepaddle \
    && pip install paddlepaddle-gpu==3.3.1 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/ \
    && if [ "$WITH_UZ" = "1" ]; then \
         pip install "torch==2.7.1" --index-url https://download.pytorch.org/whl/cu126 \
         && pip install ".[uz]"; \
       fi

USER app
EXPOSE 8000
# model files are downloaded on first use; mount a volume on /home/app/.paddlex to keep them
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python3 -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
CMD ["python3", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
