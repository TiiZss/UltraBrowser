# Ejemplos de Implementación de Mejoras

Este directorio contiene ejemplos de código para implementar las mejoras propuestas en `MEJORAS_PROPUESTAS.md`.

## Archivos Incluidos

### 1. `config_example.py`
Sistema de configuración centralizado usando dataclasses y JSON.
- Permite cargar/guardar configuración desde archivos
- Configuración anidada para Tor
- Type hints completos

### 2. `logging_example.py`
Sistema de logging profesional con:
- Niveles de log configurables
- Rotación de archivos de log
- Formato estructurado
- Soporte para consola y archivo

### 3. `exceptions_example.py`
Excepciones personalizadas para mejor manejo de errores:
- Jerarquía de excepciones
- Mensajes de error descriptivos
- Compatible con el sistema de logging

### 4. `config.json.example`
Archivo de ejemplo de configuración JSON con todas las opciones disponibles.

### 5. `user_agents.json.example`
Lista de User-Agents en formato JSON para facilitar actualizaciones.

## Cómo Usar

1. **Configuración:**
   ```python
   from config_example import BrowserConfig
   from pathlib import Path
   
   # Cargar desde archivo
   config = BrowserConfig.from_file(Path("config.json"))
   
   # O usar valores por defecto
   config = BrowserConfig()
   ```

2. **Logging:**
   ```python
   from logging_example import setup_logging, get_logger
   
   # Inicializar en main.py
   logger = setup_logging(debug_mode=True, log_file=Path("logs/app.log"))
   
   # Usar en otros módulos
   logger = get_logger()
   logger.info("Aplicación iniciada")
   ```

3. **Excepciones:**
   ```python
   from exceptions_example import TorNotRunningError
   
   try:
       # código que puede fallar
   except TorNotRunningError as e:
       logger.error(f"Tor no está disponible: {e}")
   ```

## Integración con el Código Actual

Estos ejemplos están diseñados para integrarse fácilmente con el código existente:

1. Reemplazar `print()` con `logger.info()`, `logger.debug()`, etc.
2. Reemplazar valores hardcodeados con `config.tor.socks_port`, etc.
3. Reemplazar `Exception` genéricas con excepciones específicas.

## Notas

- Estos son ejemplos de referencia. Adapta el código según tus necesidades.
- Los paths y nombres de archivos pueden ajustarse.
- Considera agregar validación adicional según sea necesario.
