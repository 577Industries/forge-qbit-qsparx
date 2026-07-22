#!/usr/bin/env bash
set -Eeuo pipefail

image="${1:?usage: smoke_container.sh IMAGE}"

configured_user="$(docker image inspect --format '{{.Config.User}}' "${image}")"
if [[ "${configured_user}" != "nonroot" ]]; then
  echo "Expected image user nonroot, found ${configured_user:-<empty>}" >&2
  exit 1
fi

container_id="$(docker run --detach \
  --publish 127.0.0.1::8775 \
  --health-interval 1s \
  --health-timeout 3s \
  --health-start-period 1s \
  --health-retries 10 \
  "${image}")"

cleanup() {
  docker rm --force "${container_id}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if [[ "$(docker exec "${container_id}" id -u)" == "0" ]]; then
  echo "Container process unexpectedly runs as root" >&2
  exit 1
fi

health="starting"
for _ in $(seq 1 45); do
  health="$(docker inspect --format '{{.State.Health.Status}}' "${container_id}")"
  if [[ "${health}" == "healthy" ]]; then
    break
  fi
  if [[ "${health}" == "unhealthy" ]]; then
    break
  fi
  sleep 1
done

if [[ "${health}" != "healthy" ]]; then
  docker inspect "${container_id}" >&2
  docker logs "${container_id}" >&2
  echo "Container did not become healthy; final state: ${health}" >&2
  exit 1
fi

binding="$(docker port "${container_id}" 8775/tcp)"
port="${binding##*:}"
base_url="http://127.0.0.1:${port}"

curl --fail --silent --show-error "${base_url}/openapi.json" | python3 -c \
  'import json, sys; value=json.load(sys.stdin); assert value["info"]["version"] == "0.1.1"'
curl --fail --silent --show-error "${base_url}/v1/inventory?seed=577" | python3 -c \
  'import json, sys; value=json.load(sys.stdin); assert value["seed"] == 577 and value["count"] == len(value["assets"]) > 0'

echo "Container is nonroot, healthy, and serving the v0.1.1 API."
