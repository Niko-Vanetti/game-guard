# Program Guard

Control remoto de programas y juegos entre dos PCs con Windows. El **Cliente** corre en segundo plano; el **Admin** controla todo desde su panel.

## Características

- Enlace por **código de 6 dígitos** — solo dentro de la app
- Cliente en **bandeja del sistema** (sin ventana visible tras conectar)
- Admin ve programas en ejecución e historial de **7 días**
- Detecta juegos vs programas normales
- Bloqueo remoto de aplicaciones
- Solo el Admin puede **desconectar**

## Instalación

```bat
install.bat
```

Instala dependencias y opcionalmente inicia el Cliente con Windows.

## Uso

### Cliente (PC controlado)

```bat
iniciar.bat
```

1. Al abrir (solo la primera vez o sin conexión): genera un código o ingresa el del Admin
2. Tras conectar → **pasa automáticamente a la bandeja** (icono violeta junto al reloj)
3. Clic derecho en el icono → ver estado, código o reconectar

No hace falta copiar enlaces ni configurar router. Ambos PCs necesitan **internet**.

### Admin (PC controlador)

```bat
iniciar_admin.bat
```

1. Ingresa el código del Cliente → **Conectar**
2. Panel con estado, programas, bloqueos y desconexión

## Estructura

| Archivo | Descripción |
|---------|-------------|
| `iniciar.bat` | Cliente (bandeja) |
| `iniciar_admin.bat` | Panel Admin |
| `install.bat` | Instalación |
| `desinstalar.bat` | Quitar del inicio de Windows |

## Configuración local

`%APPDATA%\ProgramGuard\`

- `config.json` — ajustes del Cliente
- `usage.db` — historial de programas (7 días)

## Requisitos

- Windows 10/11
- Python 3.10+
- Internet en ambos dispositivos
