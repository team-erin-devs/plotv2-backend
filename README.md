# Django + PostgreSQL Setup

## 1. Requirements
- Install Docker Desktop (Windows/macOS): https://www.docker.com/products/docker-desktop
- On Linux:
  ```
  sudo apt update
  sudo apt install -y docker.io docker-compose
  sudo systemctl enable --now docker
  sudo usermod -aG docker $USER   # then re-login
  ```

## 2. Clone
```
git clone <repo-url>
cd <project-folder>
```

## 3. .env
Get .env from sindu or someone who has it I guess


## 4. Run
```
docker compose up --build
```

## 5. Migrate
```
docker compose exec web python manage.py migrate
```

## 6. Create Superuser
```
docker compose exec web python manage.py createsuperuser
```

## 7. Admin
Visit: http://localhost:8000/admin

## Common Commands
```
Start:  docker compose up
Stop:   docker compose down
Rebuild: docker compose up --build
Shell:  docker compose exec web bash
Reset DB: docker compose down -v && docker compose up --build
```
