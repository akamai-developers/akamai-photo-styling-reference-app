# VLM Predictor

Vision-Language Model service for analyzing user selfies and extracting feature descriptions.

## Model

`Qwen/Qwen3-VL-8B-Instruct-FP8` — FP8 quantized, requires GPU with compute capability 8.0+.

Provides nearly identical performance to the BF16 model with reduced memory usage. Offers superior visual perception, extended context length, and enhanced multimodal reasoning.

## Files

- `predictor.py` — KServe predictor with JSON and multipart endpoints
- `Dockerfile` — Container image with CUDA-enabled PyTorch
- `requirements.txt` — Python dependencies (torch installed separately in Dockerfile)

## Building and Pushing

```bash
docker build -t <dockerhub-user>/vlm-predictor:latest .
docker push <dockerhub-user>/vlm-predictor:latest
```

The image is deployed to the LKE cluster via `k8s/vlm-deployment.yaml` and `k8s/vlm-service.yaml` in the project root.

## API

The service runs on port 8080 inside the cluster and is accessible internally at `http://vlm-service`.

### List models

```bash
kubectl run curl --rm -it --image=curlimages/curl -n photo-styling -- \
  curl -s http://vlm-service/v1/models
```

### Describe image (multipart form — recommended)

```bash
kubectl run curl --rm -it --image=curlimages/curl -n photo-styling -- \
  curl -X POST http://vlm-service/v1/models/vlm-predictor:describe \
  -F "file=@selfie.jpg"
```

With a custom prompt:

```bash
kubectl run curl --rm -it --image=curlimages/curl -n photo-styling -- \
  curl -X POST http://vlm-service/v1/models/vlm-predictor:describe \
  -F "file=@selfie.jpg" \
  -F "prompt=Describe the person's clothing and accessories"
```

### Response format

```json
{
  "predictions": [
    {
      "features": "A person with short dark hair, glasses, and a beard...",
      "raw_output": "..."
    }
  ]
}
```
