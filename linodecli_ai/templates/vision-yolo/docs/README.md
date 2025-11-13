# Vision YOLO Template

Runs the [`ultralytics/ultralytics`](https://hub.docker.com/r/ultralytics/ultralytics)
container to serve YOLO-based object detection APIs.

## Defaults

| Setting | Value |
| --- | --- |
| Base image | `linode/ubuntu22.04` |
| Region (default) | `eu-frankfurt` |
| Linode type (default) | `g6-standard-2` |
| Container image | `ultralytics/ultralytics:latest` |
| External port | `80` (forwarded to `8000`) |
| Health check | `http://<hostname>:8000/docs` |

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `YOLO_MODEL` | No | Name of the model to load (e.g. `yolov8n.pt`). |

The template sets `UVICORN_HOST=0.0.0.0` and `UVICORN_PORT=8000` inside the
container. Include additional variables in `.env` if your workload needs them.

## Usage

```bash
linode-cli ai init vision-yolo --directory vision-demo
cd vision-demo
cp .env.example .env
echo "YOLO_MODEL=yolov8s.pt" >> .env   # optional
linode-cli ai deploy --region eu-frankfurt --linode-type g6-standard-2 --wait
linode-cli ai status
```

API docs become available at `http://<hostname>/docs`. Destroy when finished:

```bash
linode-cli ai destroy --app vision-yolo --env default
```
