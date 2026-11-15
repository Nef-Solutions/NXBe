# Front de Overol (Streamlit) listo para un servidor. Ver DESPLIEGUE.md.
#   docker build -t overol-front .
#   docker run -p 8501:8501 -e OVEROL_API_URL=https://api.ejemplo.cl/api/ -e OVEROL_COOKIE_SECURE=1 overol-front
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # app.py no relanza Streamlit: el contenedor lo arranca directamente
    OVEROL_STREAMLIT_STARTED=1 \
    # Producción por defecto: sin cuentas de demostración en el login
    OVEROL_MODO_DEMO=0

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Sin privilegios de administrador dentro del contenedor (el front no escribe archivos)
RUN useradd --create-home --uid 10001 overol
USER overol

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4)" || exit 1

CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
