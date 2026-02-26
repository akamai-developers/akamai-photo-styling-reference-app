# Image Generator Predictor

Text-to-image generation service using FLUX.1-schnell.

## Model

`black-forest-labs/FLUX.1-schnell` — fast text-to-image generation (4 inference steps).

This is a gated HuggingFace model requiring an HF token.

The model requires ~24GB VRAM in bfloat16, which exceeds a single RTX 4000 Ada (20GB). The predictor uses `device_map="balanced"` to shard across 2 GPUs, and the Deployment requests 2 `nvidia.com/gpu` resources.

## Files

- `predictor.py` — KServe predictor with JSON endpoint
- `Dockerfile` — Container image with CUDA-enabled PyTorch
- `requirements.txt` — Python dependencies (torch installed separately in Dockerfile)

## Building and Pushing

```bash
docker build -t <dockerhub-user>/imagegen-predictor:latest .
docker push <dockerhub-user>/imagegen-predictor:latest
```

The image is deployed to the LKE cluster via `k8s/imagegen-deployment.yaml` and `k8s/imagegen-service.yaml` in the project root. The HuggingFace token is injected from the `hf-secret` Kubernetes Secret.

## API

The service runs on port 8080 inside the cluster and is accessible internally at `http://imagegen-service`.

### List models

```bash
kubectl run curl --rm -it --image=curlimages/curl -n photo-styling -- \
  curl -s http://imagegen-service/v1/models
```

### Generate image

```bash
kubectl run curl --rm -it --image=curlimages/curl -n photo-styling -- \
  curl -X POST http://imagegen-service/v1/models/imagegen-predictor:predict \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [{
      "prompt": "A superhero in a red cape flying over a city",
      "num_inference_steps": 4
    }]
  }'
```

Optional fields: `num_inference_steps` (default 4), `height` (default 1024), `width` (default 1024), `guidance_scale` (default 0.0).

### Response format

```json
{
  "predictions": [
    {
      "image": "<base64_encoded_png>"
    }
  ]
}
```
