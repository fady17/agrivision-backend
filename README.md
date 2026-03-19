```bash
cp .env.example .env
```

``` bash
 docker compose up -d --build
```

``` bash
docker exec agrivision_backend python scripts/init_minio.py
```


```bash
uv export --no-hashes --no-dev -o requirements.txt
```