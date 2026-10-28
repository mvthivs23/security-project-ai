# Security Tech AI (versión personal)

Genera el plan de seguridad de un proyecto de software antes de desarrollarlo. El plan base sale de reglas fijas en el navegador. La IA, si está configurada, solo recomienda: no quita controles y nada se aplica sin confirmación.

Sin `AI_ENABLED=true` y una clave de OpenRouter, la aplicación funciona completa solo con reglas. Se usa con datos inventados o propios, nunca con datos de clientes.

## Requisitos

- Docker Engine y Docker Compose en Ubuntu o WSL, o Python 3.12 para correr los tests en el host.

## Levantar

Desde la raíz del repositorio:

```bash
docker compose up --build
```

Abre http://localhost:8000. El archivo `.env` es opcional: si no existe, la IA queda desactivada. La plantilla está en `.env.example`. No subas `.env` al repositorio.

## Tests

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
.venv/bin/pytest
```

Los tests usan un proveedor falso. No llaman a OpenRouter.

## IA con OpenRouter

En `.env`:

```bash
AI_ENABLED=true
AI_MODEL=proveedor/modelo
OPENROUTER_API_KEY=...
```

`AI_MODEL` es el slug del catálogo de OpenRouter (`proveedor/modelo`). No hay un modelo escrito en el código. Reinicia el contenedor después de cambiar `.env`. `GET /api/ai/status` muestra el modelo activo, sin la clave.

Si `AI_ENABLED=true` pero falta el modelo o la clave, la app arranca, deja la IA desactivada y escribe una advertencia en el log sin mostrar secretos.

## Endpoints

- `GET /api/health`
- `GET /api/ai/status`
- `POST /api/ai/understand`
- `POST /api/ai/analyze`

La API no acepta prompts. Recibe el cuestionario, el contexto y, en el análisis, el nivel y los ids del plan base.
