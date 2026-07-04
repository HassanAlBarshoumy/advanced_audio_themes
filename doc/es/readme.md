# Temas de Audio Avanzados (Advanced Audio Themes)

Este complemento proporciona una experiencia de audio inmersiva para los usuarios del lector de pantalla NVDA mediante la reproducción de sonidos para diversos eventos de la interfaz de usuario. Permite la creación, instalación y personalización de temas de audio, mejorando la retroalimentación auditiva de la interfaz.

## Características

- **Efectos de audio:** Reproduce sonidos para eventos de la interfaz, como enfocar controles, navegar por listas y más.
- **Audio 3D:** Utiliza Steam Audio para proporcionar audio posicional 3D, ofreciendo una sensación de la ubicación de los controles en la pantalla.
- **DSP de audio avanzado:** Procesamiento de audio en tiempo real que incluye aumento de graves (Bass Boost), puerta de ruido (Noise Gate), recorte de silencios, normalización inteligente de volumen y envolventes suaves.
- **Atenuación de audio (Ducking):** Reduce automáticamente el volumen del tema de audio cuando NVDA habla para garantizar la claridad de la voz.
- **Reverberación:** Añade efectos de reverberación al audio para una experiencia más inmersiva.
- **Temas personalizables:** Permite a los usuarios crear, instalar y cambiar entre diferentes temas de audio.
- **Audio Themes Studio V2:** Una herramienta integrada para crear nuevos temas de audio o editar los existentes directamente desde el micrófono o arrastrando y soltando archivos.
- **Formatos de audio extendidos:** Soporte integrado de FFmpeg para MP3, FLAC, OGG, M4A y más.
- **Sonidos de escritura avanzados:** Simula la escritura en un teclado físico con posicionamiento de audio espacial, ajustes dinámicos de volumen según la velocidad y asignación inteligente de teclas especiales (Intro, Retroceso, Espacio, Mayús, Ctrl, Alt).
- **Escritura contextual:** Opción para restringir los sonidos de escritura solo a campos de texto editables.
- **Barras de progreso inteligentes:** Cambio de tono dinámico para las barras de progreso (tono más agudo = mayor porcentaje).
- **Detección del primer/último elemento:** Reproduce un sonido de "tope" específico al llegar al límite de una lista o menú.
- **Baliza / Sonar de audio:** Suelta una baliza de audio espacial en cualquier ubicación de la pantalla y navega alrededor para escuchar ecos de sonar en tiempo real que te guían en relación con la baliza.
- **Navegación avanzada:** Motores SentenceNav y BrowserNav integrados para una navegación fluida por texto y web sin conflictos con las teclas de flecha.
- **Capa de navegación:** Pulsa NVDA+Win+N para entrar en un modo de navegación rápida donde las flechas se mueven por frases, párrafos u otros elementos sin mantener presionados los modificadores.
- **Tienda de temas en la nube:** Descarga, previsualiza e instala temas creados por la comunidad directamente desde el Audio Themes Studio.
- **Perfiles específicos de aplicaciones:** Cambia automáticamente a un tema de audio y paquete de sonidos de escritura específicos según la aplicación activa.

- **Sonidos del Estado del Sistema (System Status Sounds):** Reproduce señales de audio para eventos a nivel del sistema, como cambios en la energía de CA, estado de la batería, conexión de dispositivos USB y conectividad de red.

## Desarrollo y Créditos

El desarrollo y la consolidación de este complemento comenzaron a principios de mayo (específicamente el 3 de mayo de 2026) exclusivamente por **Hassan AlBarshoumy**.

Toda la refactorización del código, consolidaciones estructurales e integraciones de la interfaz gráfica (incluido el Audio Themes Studio V2 y los diálogos de configuración unificados) se realizaron para garantizar la máxima estabilidad y compatibilidad con NVDA 2026.1+.

**Desarrollador Principal y Consolidador:**
* Hassan AlBarshoumy

**Créditos y Agradecimientos:**
Este complemento se ha beneficiado enormemente de la fusión y el desarrollo de proyectos de código abierto anteriores en la comunidad de NVDA. Un agradecimiento especial a los desarrolladores originales:
* **Ahmed Sami:** Desarrollador original del complemento navSounds (Navigation Sound Effects) y por sus contribuciones.
* **Musharraf Omer:** Desarrollador original del complemento Audio Themes 3D.
* **Tony Malykh:** Desarrollador original de los complementos Earcons and Speech Rules, BrowserNav, SentenceNav y TextNav.
* **Austin Hicks & Bryan Smart:** Desarrolladores originales del complemento Unspoken.

**Contacto y Actualizaciones:** [https://t.me/HassanAlBarshoumy](https://t.me/HassanAlBarshoumy)

## Instalación

1. Descargue la última versión del complemento desde el canal oficial de Hassan.
2. Abra el archivo `.nvda-addon` descargado.
3. NVDA le pedirá que confirme la instalación. Elija "Sí".
4. Reinicie NVDA para completar la instalación.

## Cómo usar

### Activar/Desactivar Temas de Audio

Puede activar o desactivar la función de temas de audio en la configuración de NVDA:

1. Abra el menú de NVDA (NVDA+N).
2. Vaya a "Preferencias" -> "Opciones".
3. En el cuadro de diálogo de opciones, seleccione la categoría "Temas de Audio".
4. Marque o desmarque la casilla "Activar temas de audio".

### Selección y gestión de temas

- **Acerca de un tema:** Haga clic en el botón "Acerca de" para ver información sobre el tema seleccionado.

### Descripción general de las pestañas de configuración

El panel de configuración de Temas de Audio Avanzados contiene varias pestañas para personalizar cada aspecto de la experiencia de audio. A continuación, se detalla cada opción disponible:

#### 1. Pestaña General
- **Activar temas de audio:** Interruptor principal para encender o apagar el motor de temas de audio.
- **Seleccionar tema:** Menú desplegable para elegir el tema de audio activo de los instalados.
- **Acerca de / Eliminar / Añadir nuevo:** Gestiona tus temas. Puedes instalar temas nuevos desde archivos `.atp` o `.zip`.
- **Tienda de Temas:** Abre la tienda integrada para descargar temas creados por la comunidad.
- **Theme Studio:** Abre el estudio para editar o remezclar el tema actualmente seleccionado.
- **Vista previa:** Reproduce una secuencia de sonidos de muestra del tema activo.
- **Reproducir sonidos en modo 3D:** Activa el procesamiento de audio espacial.
- **Anunciar roles:** Alterna si NVDA habla los roles de los controles (como "botón", "enlace").
- **Anunciar roles durante lectura continua:** Alterna la pronunciación de roles durante la lectura continua. Puedes usar el botón "Seleccionar roles..." para especificar exactamente qué roles hablar.
- **Usar el volumen del sintetizador de voz:** Vincula el volumen del tema al volumen de la voz de NVDA. Desactívalo para usar el control deslizante manual.
- **Atenuación de audio (Ducking):** Reduce el volumen del audio de fondo cuando NVDA habla. Puedes elegir qué categorías de sonido se atenuarán y establecer el porcentaje de volumen atenuado.
- **Comportamientos alternativos:** Define qué sucede cuando falta un sonido para un rol específico o un primer/último elemento (por ejemplo, reproducir silencio, un sonido personalizado o el primer sonido disponible).
- **Sonidos de estado suprimen el sonido del rol:** Si un elemento tiene un sonido de estado (p. ej., casilla verificada), evitará que se reproduzca el sonido del rol para evitar la saturación auditiva.
- **Lista negra de aplicaciones:** Una lista de ejecutables de aplicaciones separada por comas donde los temas de audio deben desactivarse por completo. También puedes personalizar qué categorías de sonido específicas se suprimen en estas aplicaciones.
- **Sonidos de escritura:** Habilita sonidos de máquina de escribir o teclado mecánico. Las opciones incluyen escritura espacial (simulando posiciones de teclado físico), asignación espacial inteligente, restricción de sonidos a cuadros de edición, selección de paquetes de sonidos y ajuste de volumen.
- **Gestión de configuración:** Busca actualizaciones, incluye versiones beta y Exporta/Importa toda tu configuración (incluyendo temas, reglas y sonidos) a un único archivo `.atcfg`.

#### 2. Pestaña Motor de Audio
- **Normalización inteligente de volumen:** Ajusta dinámicamente sonidos silenciosos y fuertes a un nivel constante.
- **Envolvente suave:** Aplica micro desvanecimientos (fade-ins y fade-outs) para evitar chasquidos o clics en el audio.
- **Panoramización 3D suave:** Crea un efecto de deslizamiento cuando los objetos se mueven por la pantalla en lugar de saltar instantáneamente.
- **Caché en RAM:** Carga los sonidos en la memoria para una reproducción sin latencia.
- **Recortar silencio:** Elimina automáticamente las pausas silenciosas al principio y al final de los archivos de audio en función de un umbral personalizable.
- **Puerta de ruido (Noise Gate):** Elimina el silbido de fondo de bajo nivel de temas de audio mal grabados. Incluye controles para Umbral (Threshold), Ataque (Attack) y Liberación (Release).
- **Aumento de graves (Bass Boost):** Mejora las bajas frecuencias para dar a los sonidos más impacto. Incluye controles de Ganancia y frecuencia de Corte.
- **Modo de salida de audio:** Alterna entre audio espacial 3D completo (Estéreo) y centrado (Mono).
- **Audio espacial de barra de progreso:** Elige si las barras de progreso se panoramizan de izquierda a derecha en función de su porcentaje o de su ubicación física en la pantalla. También incluye un interruptor para elevar el tono a medida que aumenta el progreso.

#### 3. Pestaña Reverberación
Simula la acústica ambiental para hacer que los sonidos parezcan reproducidos en una sala física.
- **Activar reverberación:** Interruptor principal para efectos ambientales.
- **Tamaño de la sala:** Ajusta el tamaño percibido de la sala virtual.
- **Amortiguación (Damping):** Controla la rapidez con la que se absorben las frecuencias altas.
- **Nivel Húmedo / Seco (Wet / Dry):** Equilibra la cantidad de reverberación procesada frente al sonido limpio original.
- **Ancho (Width):** Ajusta la propagación estéreo de la cola de reverberación.

#### 4. Pestaña Formatos de Audio
- **Usar FFmpeg:** Activa el soporte para formatos de audio comprimidos como MP3, FLAC, M4A y OGG.
- **Estado de FFmpeg:** Muestra si FFmpeg está instalado. Si no, se proporciona un botón para descargarlo y extraerlo automáticamente (~12MB).

#### 5. Pestaña Earcons y Reglas de Voz
Un potente motor de reglas para la pronunciación fonética y sonidos de estado personalizados.
- **Lista de reglas:** Muestra todas las reglas activas filtradas por categoría (Rol, Estado, Texto, Carácter, etc.).
- **Editor de reglas:** Al añadir o editar una regla, puedes definir:
  - **Patrón / Valor:** El patrón Regex, rol o estado a coincidir.
  - **Tipo de acción:** Elige reproducir un Wave integrado, un archivo WAV personalizado, un pitido, ajustar la prosodia (tono/velocidad), reemplazar texto o no hacer nada.
  - **Acción de voz:** Decide si NVDA debe mantener el texto original, editar el texto hablado o ser silenciado por completo cuando la regla coincida.
  - **Ajustes de audio:** Control de volumen, desplazamientos de recorte de inicio/fin (en milisegundos), tono/duración para pitidos.
  - **Filtros:** Restringe la regla a aplicaciones específicas, títulos de ventanas o URLs de sitios web (soporta Regex).
- **Operaciones por lotes:** Exportar/Importar diccionarios de reglas, activar/desactivar todas las reglas o probar reglas directamente desde la interfaz.

#### 6. Pestaña Varios
Configuración avanzada para módulos de navegación.
- **Navegación por frases (Alt+Flechas):** Ajusta el volumen de los timbres en los límites de los párrafos, alterna los anuncios de formato, configura la omisión de referencias de Wikipedia, ajusta la reconstrucción de frases entre párrafos y define caracteres personalizados de separación de frases/cláusulas.
- **Navegación de texto (Alt+Shift+Flechas):** Ajusta el volumen de crujido y configura los comportamientos de los timbres al final del texto.
- **Navegación avanzada en el navegador (BrowserNav):** Ajusta los volúmenes de crujidos y pitidos durante la navegación de QuickSearch, y el volumen del timbre para omitir el desorden (Skip Clutter).
- **Capa de navegación (NVDA+Win+N):** Configura el tiempo de espera para salida automática, sonidos de acciones de capa, teclas de paso (pass-through) y activa o desactiva modos de navegación específicos.

#### 7. Pestaña Orden de Voz
- **Formato de anuncio global:** Cambia la forma en que NVDA lee los elementos globalmente (p. ej., Predeterminado: Nombre -> Rol -> Estado, o Estado -> Rol -> Nombre).
- **Personalización por rol:** Usa el cuadro de búsqueda para encontrar roles específicos (como Casilla de verificación o Enlace) y asígnales un formato de anuncio único.

#### 8. Pestaña Perfiles de Aplicación
- Cambia automáticamente las experiencias de audio según la aplicación activa.
- **Añadir perfil:** Introduce el ejecutable de una aplicación (p. ej., `chrome.exe`) y asigna un Tema de Audio y/o Paquete de Sonidos de Escritura específico que se activará instantáneamente cuando cambies a esa aplicación.

#### 9. Pestaña Búsqueda rápida y Marcadores
- Gestiona reglas de navegación específicas de dominio para la navegación web.
- Asigna teclas (como J o K) para saltar rápidamente a elementos específicos (QuickJump), omitir automáticamente menús desordenados (SkipClutter) o ejecutar scripts de Python personalizados en sitios web específicos.

#### 10. Pestaña Primer/Último Elemento
- **Activar detección de primer/último elemento:** Reproduce un sonido de tope único cuando llegas a la parte superior o inferior de una lista, menú o vista de árbol.
- **Alcance de detección:** Aplica esto universalmente a todos los roles, o selectivamente a roles específicos (usando el botón "Seleccionar roles").
- **Comportamiento para elementos individuales:** Decide si los elementos que son el único elemento en una lista deben tratarse como el primero, el último o ser ignorados por completo.

### Uso del Audio Themes Studio V2

El Audio Themes Studio te permite crear y editar temas de audio. Para abrir el estudio:

1. Abra el menú de NVDA (NVDA+N).
2. Seleccione "Audio Themes Studio".

En el estudio, puedes:

- **Crear un nuevo tema de audio:** Te guiará a través del proceso de creación de un nuevo tema desde cero.
- **Personalizar un tema de audio existente:** Selecciona esta opción para modificar los sonidos de un tema instalado.
- **Grabar desde el micrófono:** ¡Ahora puedes grabar de forma nativa tu voz o cualquier sonido directamente desde tu micrófono para asignarlo a un evento de la interfaz!
- **Arrastrar y soltar:** Puedes arrastrar y soltar archivos de audio directamente en la ventana del Estudio para asignarlos rápidamente.
- **Tienda de temas en la nube:** Explora, previsualiza y descarga temas creados por la comunidad directamente desde el Estudio, sin necesidad de navegadores externos.

### Exportar tu Tema

Después de crear o editar un tema, puedes exportarlo como un archivo `.atp` para compartirlo con otros. Encontrarás la opción de exportación en la pantalla de edición.

## Reglas Avanzadas y Puntuación Fonética

Los Earcons (Iconos auditivos) y Reglas de Voz permiten que NVDA reproduzca earcons así como otros efectos de voz, como cambios de prosodia.

### Uso
1. Asegúrate de que el complemento esté habilitado. Pulsa NVDA+Alt+P para alternarlo.
2. Las reglas se pueden configurar mediante un cuadro de diálogo en el menú de opciones de NVDA.
3. Por defecto, tendrás un conjunto de reglas de audio predefinidas.
4. Las reglas se guardan en un archivo llamado `earconsAndSpeechRules.json` en tu directorio de configuración de usuario de NVDA.

### Detallismo del Estado (State Verbosity)
El complemento incluye una función que te permite silenciar y ocultar la voz o los sonidos para estados que puedan causar molestias constantes (por ejemplo, los estados "expandido" o "no seleccionado").
Para utilizar esta función:
1. Ve a la configuración de Reglas de Voz y edita el estado que deseas silenciar.
2. Marca la opción etiquetada **"Suprimir el desorden de estado" (Suppress state clutter)**.
3. Ahora puedes usar el atajo rápido para alternar el nivel de detalle cuando lo desees.
* Puedes alternar esta opción ya sea mediante el atajo de la capa **(NVDA+Shift+A y luego s)** o mediante el atajo directo **(NVDA+Alt+[)**.
* Cuando reduzcas el detallismo, cualquier estado para el que hayas habilitado esta opción será silenciado. Cuando vuelvas a aumentar el detallismo, el complemento volverá a leer todos los estados con normalidad.

## Funciones Avanzadas y Secretos

En este complemento están integradas una serie de funciones muy avanzadas que podrían no ser obvias a simple vista:

### 1. Capa de Navegación
- **Atajo:** `NVDA+Win+N`
- **Descripción:** Una vez que entras en esta capa, ya no necesitas mantener presionado `Alt`, `Shift` ni ninguna tecla modificadora para navegar. ¡Puedes usar solo las teclas de flecha!
- **Cómo usar:**
  - Usa las flechas Izquierda/Derecha para recorrer **27 modos de navegación diferentes** (Carácter, Palabra, Línea, Frase, Párrafo, Encabezado, Enlace, Botón, Campo de edición, Tabla, etc.).
  - Usa las flechas Arriba/Abajo para saltar al elemento anterior/siguiente según el modo actual.
  - Pulsa `C` para copiar el elemento actual al portapapeles.
  - Pulsa `S` para deletrear el elemento actual.
  - Pulsa `R` para leer todo a partir del elemento actual.
  - Pulsa `Escape` para salir de la capa.

### 2. Sonar de Audio
- **Atajo:** `NVDA+Alt+R` (o `NVDA+Shift+A` y luego `r`)
- **Descripción:** Una función increíble que barre toda la ventana activa, recopila todos los controles en su interior (botones, listas, textos) y reproduce rápidamente sus sonidos asociados de izquierda a derecha en el espacio 3D. ¡Esto te da una "imagen" sónica del diseño de la ventana y de lo poblada que está!

### 3. Baliza de Audio (Beacon)
- **Atajo:** `NVDA+Shift+B` (o `NVDA+Shift+A` y luego `a`)
- **Descripción:** Puedes "soltar" una baliza de audio en la ubicación actual del objeto navegador. Esto es útil para marcar un objeto y rastrearlo contextualmente durante un barrido de Sonar de Audio.

### 4. Capa de Comandos de Temas de Audio
- **Atajo:** `NVDA+Shift+A`
- **Descripción:** En lugar de memorizar docenas de atajos, entra en esta capa y pulsa una sola tecla para ejecutar un comando:
  - `t` : Activar/desactivar Temas de Audio.
  - `p` : Alternar Earcons y Reglas de Voz.
  - `n` y `b` : Tema Siguiente/Anterior.
  - `Flecha Arriba` y `Flecha Abajo` : Aumentar/Disminuir el volumen del tema.
  - `s` : Alternar Detallismo del Estado.
  - `o` : Cambiar rápidamente el Orden de Voz (p. ej., Nombre y luego Rol, o Rol y luego Nombre).
  - `c` : Leer el nivel de encabezado actual.
  - `y` : Recorrer los temas.
  - `i` : Recorrer los sonidos de escritura.
  - `u` : Activar/desactivar sonidos de escritura.
  - `h` : Ayuda.

### 5. Informes de Objetos 3D
- **Atajo:** `NVDA+Tab`
- **Descripción:** Informa sobre el objeto actual bajo el cursor, pero mapea perfectamente sus coordenadas de audio espacial 3D para que puedas escuchar su ubicación física exacta en tu pantalla en relación con el centro.

### 6. Integración en la Bandeja del Sistema (System Tray)
- **Descripción:** El complemento inyecta opciones de acceso rápido directamente en el menú de la bandeja del sistema de NVDA. Puedes hacer clic derecho en el icono de NVDA junto al reloj en tu barra de tareas para acceder al instante al "Audio Themes Studio" o activar y desactivar los temas sin necesidad de abrir el diálogo completo de preferencias.

### 7. Sonidos del Estado del Sistema (System Status Sounds)
- **Descripción:** Reproduce señales de audio para eventos a nivel del sistema, como la conexión/desconexión de dispositivos USB, cambios en la energía de CA, estado de la batería, conectividad de red y suspensión/reactivación del sistema. Todos los eventos se supervisan a través de las notificaciones nativas de Windows (sin sondeo).
- **Eventos:**
  - **Energía de CA conectada/desconectada:** Reproduce un sonido cuando conectas o desconectas el cable de alimentación de tu portátil.
  - **Batería baja/crítica/llena:** Reproduce alertas basadas en umbrales cuando el nivel de la batería cae por debajo de porcentajes configurables o cuando está completamente cargada.
  - **Dispositivo USB conectado/desconectado:** Detecta la conexión o eliminación de cualquier dispositivo USB (teclados, ratones, memorias USB, etc.).
  - **Montaje/desmontaje de volumen de almacenamiento:** Detecta la asignación de letras de unidad para unidades flash, discos duros externos y tarjetas SD.
  - **Red conectada/desconectada:** Comprueba el estado de la conectividad en intervalos configurables y reproduce un sonido al cambiar de estado.
  - **Reactivación/suspensión del sistema:** Reproduce sonidos cuando el equipo sale del modo de suspensión o entra en él.
- **Sonidos personalizados:** Coloca archivos `.wav` en la carpeta de tu tema con estos nombres:
  `sys_ac_plug.wav`, `sys_ac_unplug.wav`, `sys_battery_low.wav`, `sys_battery_critical.wav`, `sys_battery_full.wav`, `sys_usb_plug.wav`, `sys_usb_unplug.wav`, `sys_volume_plug.wav`, `sys_volume_unplug.wav`, `sys_network_connect.wav`, `sys_network_disconnect.wav`, `sys_wake.wav`, `sys_sleep.wav`
- **Configuración:** Abre la Configuración de NVDA -> Temas de Audio Avanzados -> pestaña "Estado del Sistema" para activar/desactivar eventos individuales, ajustar el volumen y establecer los umbrales de la batería.

## Atajos de Teclado

| Tecla | Acción |
| --- | ------ |
| **NVDA+Alt+N** | Activar/desactivar Temas de Audio. Pulsa dos veces rápido para alternar los sonidos de escritura. |
| **NVDA+Alt+T** | Recorrer los Temas de Audio disponibles. |
| **NVDA+Alt+Y** | Recorrer los paquetes de sonidos de escritura disponibles. |
| **NVDA+Alt+K** | Activar/desactivar sonidos de escritura. |
| **NVDA+Alt+R** | Sonar de audio: Barre la ventana activa para crear un mapa de audio de sus elementos. |
| **NVDA+Shift+B** | Soltar/Quitar una Baliza de Audio en el objeto navegador actual. |
| **NVDA+Shift+A** | Entrar en la Capa de Comandos de Temas de Audio (pulsa esto, luego: h para ayuda, t para alternar, p para reglas, n/b para tema siguiente/anterior, flechas arriba/abajo para volumen, y/i/u para recorrer/alternar temas/escritura, a/r para baliza/sonar, s para detallismo, c para encabezado, o para orden). |
| **NVDA+Alt+P** | Alternar el complemento de Earcons y Reglas de Voz. |
| **NVDA+Alt+[** | Alternar el modo de información concisa de estado (Detallismo del Estado). |
| **NVDA+H** | Leer el nivel de encabezado actual. |
| **NVDA+Tab** | Informar sobre el objeto bajo el cursor con coordenadas de audio 3D completas. |
| **NVDA+Alt+S** | Leer la frase actual (SentenceNav). |
| **Alt+Flechas** | Navegación avanzada por frases. |
| **Alt+Win+Flechas** | Navegación avanzada por cláusulas. |
| **Alt+Shift+Flechas** | Navegación avanzada por párrafos. |
| **NVDA+Alt+Flechas** | Navegación Web avanzada (BrowserNav). |
| **NVDA+Win+N** | Alternar la Capa de Navegación (navegación rápida sin modificadores). |

## Compatibility & Requirements
- **NVDA Version:** Requires NVDA 2024.1.0 or later.
- **Last Tested NVDA Version:** 2026.1.0
- **Operating System:** Windows 10 or Windows 11.

## Source Code & Repository
You can view the source code, report issues, or contribute to the project on GitHub:
[Advanced Audio Themes Repository](https://github.com/HassanAlBarshoumy/advanced_audio_themes)

## Change Log

### Version 9.32
- **Sonidos de estado del sistema: Added a completely new module to monitor and play sounds for system-level events (USB plug/unplug, AC power changes, battery status, network connectivity, and system wake/sleep) using native Windows notifications for zero lag.
- **Audio DSP Enhancements:** Completely rewrote the Bass Boost (Low-shelf filter) and Noise Gate algorithms to support correct attack/release times and improved sound quality. Added a full UI in the settings panel to control these DSP effects.
- **3D Spatial Audio Fixes:** Resolved an issue causing lag in 3D audio playback for progress bars.

### Version 9.30 - 9.31
- **Universal First/Last Item Detection:** Added support for first/last item detection for *all* NVDA roles, instead of just lists and menus.
- **Advanced Detection Modes:** Introduced 3 detection modes (smart, strict, any_sibling) with multi-hop traversal to guarantee accurate detection of the first and last elements even in complex web layouts.

### Version 9.27 - 9.28
- **Role vs State Sounds Priority:** Fixed an issue where state sounds (like "checked") were wrongly suppressing role sounds (like "checkbox").
- **Fallback Behaviors:** Added custom fallback settings for first/last item sounds, allowing users to select custom sounds or bypass missing roles.
- **Heading Support:** Added support for Heading levels 7, 8, and 9.

### Version 9.23 - 9.26
- **Sentence Navigation Fixes:** Fixed a bug causing NVDA to endlessly repeat sentences when reading Arabic text in VirtualBuffers.
- **NVDA 2026.2 Compatibility:** Migrated to the new `NVDAHelper.localLib.generateBeep` API to resolve deprecation warnings and ensure stability on future NVDA versions.
- **Auto-Update Fix:** Resolved a critical freeze in NVDA during the auto-update download process.

## Novedades

### Versión 9.32
- **Sonidos de estado del sistema:** Nuevo motor de monitorización para batería, USB, red y energía.
- **Mejoras DSP:** Filtros de Bass Boost y Noise Gate completamente reescritos para evitar chasquidos.
- **Audio 3D:** Solución de retrasos en barras de progreso.

### Versión 9.30 - 9.31
- **Identificación Universal:** Detección de primer/último elemento para todos los roles.

### Versión 9.27 - 9.28
- **Sonidos alternativos:** Opciones de sonidos de reserva añadidos.
- **Encabezados:** Soporte para niveles de encabezado 7, 8 y 9.

### Versión 9.23 - 9.26
- **Correcciones:** Solución de repetición de frases y compatibilidad con NVDA 2026.2.

## Traductores
- **Español:** Hassan AlBarshoumy, Luis Carlos González Morales
- **Italiano:** Christian Cantelmi, Ciro Cantelmi
- **Ruso:** Valentin Kupriyanov
- **Chino:** Cary-rowen, Jerry
- **Alemán:** René L

