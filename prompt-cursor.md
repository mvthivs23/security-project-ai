# Prompt inicial para Cursor · Security Tech AI con FastAPI (versión personal con OpenRouter)

> Pega en el chat de Cursor (modo Agent) todo lo que está bajo la línea. Antes, deja en la raíz del repositorio `AGENTS.md`, `.env.example`, `.cursor/rules/security-tech-ai.mdc` y `reference/security-tech-ai.html`, y adjunta en el chat `@AGENTS.md` y `@reference/security-tech-ai.html`.

---

Eres un ingeniero senior de Python y de seguridad de aplicaciones. Vamos a convertir la plantilla `reference/security-tech-ai.html` (un solo archivo HTML con toda la lógica en JavaScript) en una aplicación con **backend en Python + FastAPI**, para poder trabajar con APIs y conectar la IA a **OpenRouter**, para probar cualquier modelo de su catálogo cambiando solo una variable de entorno. Es una versión personal: solo datos inventados, nunca datos de clientes.

`AGENTS.md` es el contexto completo, el alcance y las reglas: léelo entero y respétalo. Lo más importante:


## Objetivo

1. FastAPI sirve el frontend (el HTML, CSS y JS de la referencia separados en archivos estáticos) y expone la API.
2. Las dos llamadas a la IA que hoy hace el navegador con `window.claude.use("sample")` (`undRun` y `aiRun`) pasan a endpoints del backend. Los prompts (`undPrompt`, `aiPrompt`) y las validaciones (`undValidate`, `aiValidate`) se portan a Python.
3. El modelo se cambia solo con `AI_MODEL`. **Por defecto no hay proveedor configurado y la app funciona completa solo con reglas**, igual que la referencia cuando no hay IA.
4. Las descargas que hoy usan `window.claude.use("downloads")` pasan a una descarga normal del navegador (Blob y enlace con `download`).

## Estructura esperada

```
reference/security-tech-ai.html      # referencia, no se toca
catalog/                             # JSON exportados de la referencia (controles, requisitos, preguntas) + version.json
backend/app/
  main.py                            # FastAPI: /api y archivos estáticos
  core/config.py                     # pydantic-settings, lee .env
  core/security.py                   # cabeceras, CSP, límite de cuerpo, rate limit
  ai/base.py                         # interfaz LLMProvider
  ai/openrouter_provider.py          # SDK openai apuntando a OpenRouter
  ai/prompts/                        # prompts portados de undPrompt y aiPrompt
  ai/validators.py                   # portados de undValidate y aiValidate
  sanitize/redact.py                 # portado de redact (ctx.js)
  sanitize/document.py               # portado de sanitizeDoc e INJ (upload.js)
  api/health.py  api/ai.py
  schemas/                           # modelos Pydantic de entrada y salida
backend/tests/
frontend/static/                     # index.html, css/, js/ y vendor/ (pdfmake, pdf.js)
Dockerfile  docker-compose.yml  .env.example  .gitignore  README.md
```

## Capa de IA

- Interfaz única: `LLMProvider.complete_json(system: str, user: str) -> dict`, con timeout, máximo de tokens y un reintento si la respuesta no es JSON válido.
- SDK `openai` con `base_url="https://openrouter.ai/api/v1"` fija en el código (no configurable), `api_key=OPENROUTER_API_KEY` y `chat.completions`, con el mensaje de sistema separado del mensaje del usuario.
- Si `OPENROUTER_ZDR=true` (por defecto), envía `extra_body={"provider": {"zdr": True}}` para usar solo endpoints sin retención de datos.
- Si `OPENROUTER_APP_TITLE` tiene valor, envíalo como cabecera `X-OpenRouter-Title`.
- Si `AI_JSON_MODE=true`, pide `response_format={"type": "json_object"}`; si no, extrae el primer objeto JSON del texto.
- `AI_TEMPERATURE` solo se envía si tiene valor.
- `GET /api/ai/status` muestra el modelo activo para saber con cuál estoy probando.
- Ningún nombre de modelo escrito en el código: siempre `AI_MODEL`.
- Si la configuración está incompleta, la IA queda desactivada con una advertencia en el log que no muestre secretos.
- Los errores del proveedor se devuelven al frontend como mensajes genéricos en español, sin detalles internos.

## Endpoints (solo estos)

- `GET /api/health`
- `GET /api/ai/status` → `{enabled, provider, model}`, sin claves.
- `POST /api/ai/understand` → recibe respuestas del cuestionario y contexto; devuelve lo mismo que hoy produce `undValidate`.
- `POST /api/ai/analyze` → recibe respuestas, contexto, nivel e IDs de controles del plan base; devuelve lo mismo que hoy produce `aiValidate`.

Los endpoints de IA **no aceptan prompts**, solo datos estructurados validados con Pydantic (`extra="forbid"` y largos máximos). Antes de llamar al proveedor: `redact` y `sanitize_document` sobre el contexto. Después: validación contra el esquema y contra `/catalog`, descartando lo que no exista y sin quitar nunca controles base.

En el frontend, `AI_SAMPLE` pasa a ser un pequeño cliente que llama a estos endpoints y se activa solo si `/api/ai/status` dice `enabled: true`. El resto del flujo y del diseño no cambia.

## Seguridad (no negociable)

- Ninguna clave en el navegador ni en el repositorio. `.env` en `.gitignore`.
- Rate limiting en `/api/ai/*`, límite de tamaño del cuerpo, CORS con `ALLOWED_ORIGINS`, cabeceras de seguridad y CSP sin CDN (pdfmake y pdf.js servidos desde `vendor/`).
- Logs con solo metadatos: proveedor, modelo, duración y resultado. Nunca contexto, documentos ni respuestas de la IA.
- Tests con un proveedor falso: nunca se llama a un proveedor real en los tests.
- Contenedor sin root, imagen fijada por versión, healthcheck.
- Solo datos sintéticos en pruebas y ejemplos.

## Fases (detente al final de cada una y espera mi OK)

- **Fase 1 · Base.** Proyecto FastAPI, configuración, `/api/health`, Dockerfile, docker-compose, `.gitignore`, pytest y README.
- **Fase 2 · Frontend servido por FastAPI.** Separa la referencia en archivos estáticos sin cambiar comportamiento ni diseño; copia pdfmake y pdf.js a `vendor/`; reemplaza `claude.use("downloads")`. Verifica que la app funcione igual que la referencia, sin IA.
- **Fase 3 · Capa de IA.** Proveedores, factory, `/api/ai/status`, sanitización en el servidor, prompts y validadores portados, catálogo exportado a `/catalog`, endpoints `understand` y `analyze`, cliente en el frontend y tests con proveedor falso.
- **Fase 4 · Prueba con modelos reales.** Te indico qué modelos configuro en `.env`. Verifica con datos sintéticos que el paso 3 funcione con al menos dos modelos de proveedores distintos y anota cuál falla al devolver JSON.

Al final de cada fase: tests en verde, `docker compose up` funcionando, un resumen corto, lo pendiente y los comandos para probar.

Empieza por la **Fase 1 y genera el codigo completo de todo y luego levanta con docker**.
