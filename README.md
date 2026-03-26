# Hacoo Bot

Bot de Telegram que monitoriza canales de Telegram en busca de ofertas de ropa y permite a los usuarios buscar productos por marca, categoría y color.

## Cómo funciona

- Un cliente de usuario **Telethon** escucha los canales de Telegram configurados en tiempo real e indexa cada nuevo post en una base de datos SQLite local.
- Un bot **python-telegram-bot** expone la interfaz de búsqueda y los comandos de administración a los usuarios.
- Ambos se ejecutan de forma concurrente en el mismo proceso.

## Credenciales necesarias

Se necesitan dos conjuntos de credenciales de Telegram:

| Credencial | Dónde obtenerla | Propósito |
|---|---|---|
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → `/newbot` | Identifica el bot |
| `API_ID` + `API_HASH` | [my.telegram.org](https://my.telegram.org) → *API development tools* | Cliente de usuario Telethon (monitorización de canales) |

> **Nota:** `API_ID` / `API_HASH` pertenecen a tu cuenta personal de Telegram, no al bot. En la primera ejecución, Telethon pedirá tu número de teléfono y un código de un solo uso. La sesión se guarda en `<SESSION_NAME>.session` para que las siguientes ejecuciones sean automáticas.

## Configuración

### 1. Clonar el repositorio

```bash
git clone <repo-url>
cd hacoo_bot
```

### 2. Crear un entorno virtual e instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar las variables de entorno

```bash
cp .env.example .env
```

Edita el archivo `.env` con tus valores:

```env
# Token del bot obtenido desde @BotFather
BOT_TOKEN=tu_token_aqui

# Credenciales de la API de Telegram desde https://my.telegram.org
API_ID=tu_api_id_aqui
API_HASH=tu_api_hash_aqui

# IDs de usuario de Telegram con acceso de administrador (separados por comas)
ADMIN_USER_IDS=123456789,987654321

# Ruta a la base de datos SQLite (se crea automáticamente)
DATABASE_PATH=data/bot.db

# Nombre del archivo de sesión de Telethon
SESSION_NAME=monitor_session
```

Para encontrar tu ID de usuario de Telegram, escríbele a [@userinfobot](https://t.me/userinfobot).

### 4. Ejecutar el bot

```bash
python main.py
```

En la **primera ejecución**, Telethon pedirá tu número de teléfono y el código de verificación enviado a tu cuenta. Después, la sesión queda guardada y no se necesita ninguna acción adicional.

## Comandos del bot

### Comandos de usuario

| Comando | Descripción |
|---|---|
| `/start` | Iniciar una búsqueda de productos (flujo guiado: marca → categoría → color) |
| `/cancel` | Cancelar la búsqueda actual |

También puedes escribir directamente el nombre de una marca sin usar `/start`.

### Comandos de administrador

Estos comandos están restringidos a los IDs de usuario listados en `ADMIN_USER_IDS`.

| Comando | Descripción |
|---|---|
| `/addchannel @username` | Añadir un canal de Telegram a la lista de monitorización |
| `/removechannel @username` | Eliminar un canal de la monitorización |
| `/channels` | Listar todos los canales monitorizados actualmente |
| `/reindex` | Volver a descargar e indexar los últimos 200 posts de cada canal monitorizado |

## Estructura del proyecto

```
hacoo_bot/
├── main.py               # Punto de entrada — arranca el bot y el monitor de forma concurrente
├── config.py             # Carga las variables de entorno
├── requirements.txt
├── .env.example
├── bot/
│   └── handlers.py       # Manejadores de comandos y conversaciones del bot
├── database/
│   ├── db.py             # Consultas asíncronas con SQLAlchemy
│   └── models.py         # Modelos ORM (Product, Channel)
└── monitor/
    ├── collector.py      # Cliente Telethon — obtiene el historial y escucha nuevos posts
    └── parser.py         # Parsea el texto de los posts en datos estructurados de producto
```

## Dependencias

| Paquete | Versión | Propósito |
|---|---|---|
| `python-telegram-bot[ext]` | ~22.7 | Interfaz del bot |
| `telethon` | ~1.37 | Cliente de usuario de Telegram para monitorizar canales |
| `sqlalchemy` | ~2.0 | ORM / acceso a base de datos |
| `aiosqlite` | ~0.20 | Driver SQLite asíncrono |
| `python-dotenv` | ~1.0 | Carga de archivos `.env` |
