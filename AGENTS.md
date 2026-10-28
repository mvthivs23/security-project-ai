# Security Tech AI (versión personal) · Contexto del proyecto

Este documento es el contexto completo del proyecto. Léelo antes de cualquier tarea y respétalo siempre.


## Qué es el proyecto

Security Tech AI genera el **plan de seguridad** de un proyecto de software antes de desarrollarlo (automatizaciones n8n, apps con LLM, RAG, agentes, APIs, scripts, apps web sin IA). Esta es mi **versión personal**, para practicar y probar distintos modelos a través de OpenRouter. Se usa solo con datos inventados o propios, **nunca con datos de clientes**.

El plan se calcula con **reglas fijas** orientadas al OWASP AI Exchange, con el AISVS (o el ASVS si el proyecto no tiene IA) como criterio de cumplimiento, más OWASP Top 10, Top 10 LLM, Top 10 Agentic, API Top 10, CI/CD Top 10, Cheat Sheet Series y la Ley 21.719. Una IA **opcional** entiende el contexto, detecta riesgos y recomienda controles adicionales.

**Principio central:** el plan base calculado por reglas siempre se aplica. La IA solo recomienda: nunca quita controles y nada se aplica sin confirmación de una persona. **Sin IA configurada, la app funciona completa solo con reglas.**

## Referencia

`reference/security-tech-ai.html` es la versión actual y funcional, en un solo archivo. Es la **fuente de verdad** del flujo, la lógica, los textos y el diseño. No la modifiques. La nueva app debe comportarse y verse igual, salvo lo que este documento cambia.

Flujo de 4 pasos:

1. **Cuestionario:** secciones A a D.
2. **Contexto:** texto libre guiado por las respuestas, más la subida de un documento (PDF, .docx, TXT, MD) que se lee en el navegador y se sanitiza contra prompt injection indirecto.
3. **Análisis IA:** lo que entendió la IA, riesgos detectados, amenazas del AI Exchange y riesgos OWASP que cubre el plan.
4. **Plan final:** resumen, controles por fase con estado (Pendiente, En proceso, Completado, Fuera de alcance), recomendaciones de la IA dentro de su fase (Incluir / Descartar) y exportación (PDF, CSV para Monday, Markdown).

En la referencia, la IA se llama desde el navegador en dos puntos: `undRun()` (entender el contexto, prompt `undPrompt`, validación `undValidate`) y `aiRun()` (riesgos y recomendaciones, prompt `aiPrompt`, validación `aiValidate`). Ambos usan `window.claude.use("sample")`, que **solo existe donde hoy está publicada** y debe reemplazarse. Las descargas usan `window.claude.use("downloads")`, que también se reemplaza.

## Lo que se construye (alcance)

1. **Backend en Python con FastAPI** que sirve el frontend y expone la API.
2. **Frontend:** el HTML, CSS y JS de la referencia separados en archivos estáticos y servidos por FastAPI. Sin React ni frameworks: se mantiene el mismo código, salvo lo necesario para llamar a la API.
3. **Capa de IA en el backend, con proveedor intercambiable por variables de entorno:** un único proveedor, **OpenRouter**, con el que se elige cualquier modelo de su catálogo (Anthropic, OpenAI, Google, Meta, Mistral, DeepSeek, etc.) cambiando solo `AI_MODEL`. Por defecto **no hay proveedor configurado** y la app funciona sin IA.
4. **Docker** para levantar el entorno local.

Fases posteriores, **solo cuando yo las pida**: motor de reglas portado a Python con pruebas de paridad, base de datos con listado de proyectos y avance, inicio de sesión, Jira y despliegue en AWS.

## Stack

- Python 3.12, FastAPI, Uvicorn, Pydantic v2 y pydantic-settings, httpx, pytest.
- SDK oficial `openai` apuntando a OpenRouter (`https://openrouter.ai/api/v1`), que es compatible con la API de OpenAI.
- Frontend estático: HTML, CSS y JavaScript de la referencia. pdfmake 0.2.10 y pdf.js 3.11.174 copiados en `frontend/static/vendor/` (sin CDN).
- Docker y Docker Compose en Ubuntu/WSL con Docker Engine (sin Docker Desktop).

No cambies ni agregues tecnologías sin preguntarme.

## Configuración de IA (variables de entorno)

| Variable | Uso |
|---|---|
| `AI_ENABLED` | `false` = sin IA (valor por defecto). `true` = usa OpenRouter. |
| `AI_MODEL` | Slug del modelo en OpenRouter, con formato `proveedor/modelo` (catálogo en openrouter.ai/models). Sin valor por defecto en el código. |
| `OPENROUTER_API_KEY` | Clave de OpenRouter. |
| `AI_TIMEOUT_SECONDS` | Tiempo máximo por llamada (por defecto 60). |
| `AI_MAX_OUTPUT_TOKENS` | Máximo de tokens de salida (por defecto 4000). |
| `AI_TEMPERATURE` | Opcional. Si está vacío, no se envía. |
| `AI_JSON_MODE` | `true` pide `response_format` JSON (solo para modelos que lo soportan). Si es `false`, el JSON se extrae del texto. |
| `OPENROUTER_ZDR` | `true` (por defecto) envía `provider: {"zdr": true}`: solo se usan endpoints con política de cero retención de datos. |
| `OPENROUTER_APP_TITLE` | Opcional, se envía como cabecera `X-OpenRouter-Title`. |
| `AI_RATE_LIMIT_PER_MINUTE` | Límite de llamadas de IA por IP (por defecto 10). |
| `ALLOWED_ORIGINS` | Orígenes permitidos para CORS. |

Si `AI_ENABLED=true` pero falta `AI_MODEL` o la clave, la app arranca, registra una advertencia sin mostrar secretos y trata la IA como desactivada.

## Reglas técnicas

- **Solo se llama a `https://openrouter.ai/api/v1`**, fijo en el código; no se permite cambiar la URL base por configuración.
- **Ninguna clave llega al navegador.** El frontend solo llama a `/api/...`; el backend llama a OpenRouter.
- **La API no es un proxy abierto de LLM.** Los endpoints reciben datos estructurados (respuestas, contexto, nivel, IDs de controles), nunca un prompt. Los prompts viven en el backend (`backend/app/ai/prompts/`), portados de `undPrompt` y `aiPrompt`.
- **Anonimización y sanitización también en el servidor**, aunque el navegador ya lo haga: portar `redact` (de `ctx.js`) y `sanitizeDoc` con sus patrones `INJ` (de `upload.js`), con tests.
- **La salida de la IA es un dato no confiable:** portar `undValidate` y `aiValidate`. Se valida con Pydantic, se descartan IDs que no existan en el catálogo y nunca se quitan controles base.
- El catálogo necesario para validar (IDs de controles, requisitos AISVS y ASVS, preguntas) se exporta de la referencia a JSON en `/catalog`, no se escribe a mano en el código.
- Validación estricta de entrada (Pydantic con `extra="forbid"` y largos máximos), límite de tamaño del cuerpo, rate limiting en los endpoints de IA, cabeceras de seguridad y CSP sin CDN externos.
- Logs sin el texto del contexto, sin documentos y sin respuestas de la IA; solo metadatos (proveedor, modelo, duración, resultado).
- Tests sin llamadas reales a proveedores: se usa un proveedor falso.
- Contenedor sin root, imagen base fijada por versión y healthcheck.
- Sin secretos en el repo: `.env.example` con valores vacíos y `.env` en `.gitignore`.
- Solo datos sintéticos en pruebas y ejemplos. Nunca datos reales de clientes.
- Código e identificadores en inglés; textos de la interfaz y documentación en español de Chile.
