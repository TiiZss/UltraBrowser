# Auditoría de Seguridad — UltraBrowser

## Versión: 0.4.0
## Fecha última revisión: 2026-03-25
## Estado: ✅ AUDITADO Y MEJORADO

---

## Resumen Ejecutivo

UltraBrowser v0.4.0 implementa un modelo de privacidad de múltiples capas:
privacidad de red (Tor), privacidad de datos (perfil off-the-record real),
privacidad de identidad (anti-fingerprinting), y bloqueo activo de rastreadores
y anuncios. Las páginas mantienen su funcionalidad: solo se bloquean los recursos
publicitarios de terceros.

---

## Vulnerabilidades Identificadas y Estado

### 🔴 CRÍTICOS — ✅ RESUELTOS

#### 1. Perfil de navegador persistente (CORREGIDO en v0.4.0)
- **Problema anterior:** Se usaba `QWebEngineProfile.defaultProfile()` que comparte datos
  entre instancias y puede persitir datos en disco.
- **Solución:** Perfil privado real con `QWebEngineProfile("")` (nombre vacío = off-the-record).
  Este perfil nunca escribe nada en disco: sin cookies persistentes, sin caché en disco,
  sin historial, sin credenciales guardadas.
- **Estado:** ✅ Implementado

#### 2. Bloqueo de UI durante conexión Tor (CORREGIDO en v0.4.0)
- **Problema anterior:** `toggle_tor()` usaba `time.sleep()` en el hilo principal de Qt,
  congelando la interfaz durante la conexión (5–30 segundos).
- **Solución:** `TorConnectWorker(QThread)` ejecuta la conexión en un hilo separado.
  La UI permanece completamente responsiva. Señales `connection_success` / `connection_failure`
  notifican al hilo principal cuando termina.
- **Estado:** ✅ Implementado

#### 3. Bug: Duplicado en denegación de cámara (CORREGIDO en v0.4.0)
- **Problema anterior:** `handle_permission_request()` llamaba dos veces a
  `setFeaturePermission(PermissionDeniedByUser)` para la cámara (código duplicado, líneas 153–155).
- **Solución:** Código depurado — una sola llamada por rama.
- **Estado:** ✅ Corregido

#### 4. Fuga DNS (VERIFICADO)
- **Riesgo:** Consultas DNS que revelen destinos de navegación.
- **Mitigación:** Proxy SOCKS5 de Tor enruta automáticamente las consultas DNS a través de Tor.
  Sin DNS leak cuando Tor está activo.
- **Estado:** ✅ Implementado

#### 5. Log de navegación en disco (CORREGIDO en v0.4.0)
- **Problema anterior:** `log_file` apuntaba por defecto a `logs/ultrabrowser.log`,
  registrando URLs y actividad de navegación en disco.
- **Solución:** `log_file = None` por defecto. El log de archivo debe activarse
  explícitamente en `config.json` para depuración.
- **Estado:** ✅ Corregido

---

### 🟡 IMPORTANTES — ✅ RESUELTOS

#### 6. WebRTC IP Leak
- **Riesgo:** WebRTC puede exponer la IP real incluso con Tor activo.
- **Mitigación:** `WebRTCPublicInterfacesOnly = True` en los ajustes de WebEngine.
  Los plugins (que pueden usar WebRTC) están deshabilitados.
- **Estado:** ✅ Implementado

#### 7. Fingerprinting del navegador
- **Riesgo:** Los sitios pueden identificar al usuario por características del navegador.
- **Mitigaciones aplicadas:**
  - Rotación automática de User-Agent (cada 30 min por defecto)
  - Script de anti-fingerprinting inyectado vía `QWebEngineScript` en DocumentCreation:
    - WebGL vendor/renderer enmascarados (`"Intel Inc."`)
    - `navigator.plugins` y `navigator.mimeTypes` vaciados
    - `screen.colorDepth` / `screen.pixelDepth` estandarizados a 24
    - `navigator.deviceMemory` fijado a 8
    - `navigator.hardwareConcurrency` fijado a 4
    - `navigator.getBattery` deshabilitado
- **Estado:** ✅ Implementado

#### 8. Rastreadores y anuncios (NUEVO en v0.4.0)
- **Riesgo:** Los rastreadores de terceros pueden correlacionar sesiones incluso con Tor.
- **Solución:** `AdBlocker(QWebEngineUrlRequestInterceptor)` con lista de >100 dominios
  de redes publicitarias y rastreadores conocidos. Bloquea a nivel de red (antes
  de que la petición salga). No bloquea el frame principal para no romper páginas.
- **Estado:** ✅ Implementado

#### 9. Validación de URLs
- **Riesgo:** URLs maliciosas (`javascript:`, `vbscript:`).
- **Solución:** `validate_url()` bloquea esquemas peligrosos. Búsquedas sin punto
  van a DuckDuckGo automáticamente.
- **Estado:** ✅ Implementado

#### 10. Forzado de HTTPS
- **Riesgo:** Conexiones HTTP no cifradas.
- **Solución:** `force_https_redirect()` redirige HTTP → HTTPS con protección anti-loop.
  Se exceptúan hosts locales (127.x.x.x, localhost) para desarrollo.
- **Estado:** ✅ Implementado

---

### 🟢 MEJORAS — ✅ IMPLEMENTADAS

#### 11. Recursión en `load_user_agents()` (CORREGIDO en v0.4.0)
- **Problema:** Llamada recursiva confusa con path inexistente como fallback.
- **Solución:** Lista de defaults definida explícitamente dentro de la función, sin recursión.

#### 12. `bare except:` en `TorManager.__del__` (CORREGIDO en v0.4.0)
- **Problema:** `except:` sin tipo capturaba cualquier excepción silenciosamente.
- **Solución:** `except Exception: pass` con comentario explicativo.

#### 13. `get_current_ip()` incorrecto (CORREGIDO en v0.4.0)
- **Problema:** La implementación anterior hacía una conexión TCP directa al puerto SOCKS5
  y enviaba una petición HTTP raw — esto no implementa el protocolo SOCKS5 y no funciona.
- **Solución:** Renombrado a `get_exit_ip()`. Usa `requests` con proxy `socks5h://`
  si está disponible, o devuelve `None` en lugar de hacer una conexión incorrecta.

#### 14. Rotación de User-Agent automática (NUEVO en v0.4.0)
- `QTimer` que rota el User-Agent del perfil compartido cada N minutos (configurable).
- Antes: la rotación estaba configurada pero nunca se ejecutaba automáticamente.

#### 15. Robustez de `BrowserConfig.from_file()` (MEJORADO en v0.4.0)
- Filtrado de claves desconocidas del JSON para evitar errores con configuraciones
  antiguas o con campos extra.

---

## Configuración de Privacidad Activa

| Parámetro | Valor | Efecto |
|---|---|---|
| Cookies persistentes | ❌ Deshabilitadas | Sin rastreo entre sesiones |
| Caché | RAM únicamente | Sin datos en disco |
| LocalStorage | ❌ Deshabilitado | Sin persistencia JS |
| Plugins | ❌ Deshabilitados | Sin Flash, sin vectores de ataque |
| WebRTC | Solo interfaces públicas | Mitiga fuga de IP local |
| Contenido inseguro | ❌ Bloqueado | Sin mixed content |
| Esquemas peligrosos | ❌ Bloqueados | Sin javascript:, vbscript: |
| Acceso local a remoto | ❌ Bloqueado | Sin SSRF desde contenido local |
| Log en disco | ❌ Deshabilitado por defecto | Sin registro de navegación |
| Bloqueador de anuncios | ✅ Activo | Sin rastreadores de terceros |
| Anti-fingerprinting JS | ✅ Activo | Protección contra fingerprinting |
| User-Agent rotatorio | ✅ Cada 30 min | Cambio de identidad periódico |

---

## Amenazas Residuales Conocidas

1. **Fingerprinting de canvas**: No se aplica ruido aleatorio al canvas para no romper
   funcionalidad (captchas, editores de imagen). El enmascaramiento de WebGL mitiga parcialmente.

2. **Timing attacks**: La latencia de Tor puede usarse para correlacionar tráfico.
   Mitigación: fuera del alcance del navegador.

3. **Ataques de correlación Tor**: Un adversario global que controle suficientes nodos
   puede correlacionar tráfico. Mitigación: depende de la red Tor, no del navegador.

4. **Pantalla completa y resolución**: La resolución de pantalla real es visible para
   los sitios cuando se activa pantalla completa. Mitigación parcial con `colorDepth/pixelDepth`.

5. **JavaScript habilitado**: Necesario para la mayoría de sitios modernos. Deshabilitar
   JS en `config.json` si se necesita máxima privacidad a costa de funcionalidad.

---

## Lenguaje y Arquitectura

Python + PyQt6 es la elección correcta para este proyecto:
- **Multiplataforma nativo**: Windows, Linux, macOS sin código adicional por plataforma.
- **Motor Chromium**: PyQt6-WebEngine usa Chromium, el mismo motor que Chrome/Edge.
  El overhead de Python es despreciable comparado con el motor.
- **Mantenibilidad**: Código limpio, tipado, modular y documentado.
- **Tor integrado**: `stem` es la biblioteca estándar de control Tor en Python.

No se justifica cambiar de lenguaje. El rendimiento está limitado por Chromium,
no por Python.

---

## Estado Final

**✅ v0.4.0 — APTO PARA USO CON PRIVACIDAD MEJORADA**

Todos los bugs críticos corregidos. Nuevas capas de protección añadidas:
bloqueador de anuncios, anti-fingerprinting JS, perfil off-the-record real,
Tor no-bloqueante, rotación automática de User-Agent.
