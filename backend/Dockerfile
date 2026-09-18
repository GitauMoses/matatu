FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8123

# Binds to all interfaces inside the container — the container's own port
# mapping (see deploy/docker-compose.yml, published to 127.0.0.1 only) is
# what keeps this off the public interface, same as the systemd path.
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8123", "--access-logfile", "-", "app.main:app"]
