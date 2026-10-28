def error_body(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


MSG_GENERIC = "No se pudo completar el análisis."
MSG_TOO_LONG = "El contexto es demasiado largo; resúmelo."
MSG_INVALID_JSON = "La respuesta no vino en el formato esperado. Intenta de nuevo."
MSG_RATE_UNDERSTAND = "Demasiadas consultas seguidas; espera un momento."
MSG_RATE_ANALYZE = "Hay demasiadas consultas seguidas. Espera un momento e intenta de nuevo."
MSG_EMPTY_CONTEXT = "Escribe primero el contexto del proyecto (paso 0)."
