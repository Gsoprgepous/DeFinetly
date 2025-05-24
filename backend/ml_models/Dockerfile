FROM pytorch/pytorch:2.0.1-cuda11.7

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Установка PyTorch Geometric
RUN pip install torch-scatter torch-sparse torch-cluster torch-spline-conv \
    -f https://data.pyg.org/whl/torch-2.0.1+cu117.html
RUN pip install torch-geometric

COPY . .
CMD ["python", "api/ml_server.py"]
