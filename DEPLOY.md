# Deploy на Raspberry Pi

## 1. Изпрати файловете

```bash
cd /home/nikolay/Documents/homegarden/home-water
ssh nikolay-garden@192.168.4.18 "mkdir -p ~/home-water"
scp *.py requirements.txt home-water.service example.json nikolay-garden@192.168.4.18:~/home-water/
```

## 2. Виртуална среда и инсталация

```bash
ssh nikolay-garden@192.168.4.18
cd ~/home-water

# Създаване на venv (веднъж)
python3 -m venv venv

# Активиране (всеки път преди да пуснеш controller.py)
source venv/bin/activate

# Инсталирай зависимостите
pip install aiohttp tortoise-orm RPi.GPIO
```

## 3. Автоматично стартиране (systemd)

Инсталирай service файла, за да стартира controller.py автоматично при рестарт:

```bash
sudo cp ~/home-water/home-water.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable home-water
sudo systemctl start home-water

# Проверка
sudo systemctl status home-water

# Логове на живо
journalctl -u home-water -f
```

Stop/restart:
```bash
sudo systemctl stop home-water
sudo systemctl restart home-water
```

## 4. Ръчно стартиране (за тест)

```bash
cd ~/home-water
source venv/bin/activate
python controller.py
```

Очакван output:
```
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
```

## 5. Тествай от лаптоп

```bash
export SCHEDULER_URL=http://192.168.4.18:8080
python cli.py list
python cli.py add --hour 8 --duration 3
python cli.py run --gpio 26 --duration 5
```

Или през curl:
```bash
# Създаване на задача
curl -X POST http://192.168.4.18:8080/tasks \
  -H "Content-Type: application/json" \
  -d '{"gpio_pin": 26, "hour": 8, "duration_sec": 5}'

# Списък
curl http://192.168.4.18:8080/tasks

# Лайф тест (пуска релето веднага за 3 секунди)
curl -X POST http://192.168.4.18:8080/tasks/run \
  -H "Content-Type: application/json" \
  -d '{"gpio_pin": 26, "duration_sec": 3}'
```
