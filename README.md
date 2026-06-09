# Game Guard

Bloqueo de videojuegos por horario en Windows. Fuera del horario permitido, los juegos seleccionados se cierran automáticamente.

## Requisitos

- Windows 10/11
- [Python 3.10 o superior](https://www.python.org/downloads/) — al instalar, marca **Add python.exe to PATH**

## Instalación

1. Descarga este repositorio (Code → Download ZIP) o clónalo.
2. Abre la carpeta del proyecto.
3. Doble clic en **`install.bat`**.
4. Doble clic en **`iniciar.bat`**.

La primera vez que se abre, **el administrador** debe crear una contraseña. Esa persona configura juegos y horarios.

## Uso

- **Icono en la bandeja** (abajo a la derecha): verde = bloqueo activo, rojo = desactivado.
- **Clic derecho** en el icono → Panel de administrador (requiere contraseña del admin).
- Para **agregar un juego**: Panel → Juegos bloqueados → Agregar juego (.exe).
- Para **quitar un juego o cambiar horarios**: hace falta la contraseña del administrador.

## Horarios (ejemplo)

| Día | Configuración |
|-----|----------------|
| Viernes | Permitir jugar ✓ + Todo el día ✓ |
| Sábado | Permitir jugar ✓, Desde 14:00 Hasta 22:00 |
| Otros días | Sin marcar = no se puede jugar |

## Desactivar temporalmente

El administrador puede desactivar el bloqueo en cualquier momento desde el panel (pestaña Estado) o desde el menú de la bandeja, con contraseña.

## Desinstalar

1. Ejecuta **`desinstalar.bat`**.
2. Opcional: borra `%APPDATA%\GameGuard\`.

## Archivos del proyecto

```
game-guard/
├── install.bat          # Instalar (una vez)
├── iniciar.bat            # Iniciar la app
├── desinstalar.bat        # Quitar del inicio de Windows
├── main.py                # Entrada principal
├── requirements.txt       # Dependencias Python
├── game_guard/            # Código de la aplicación
└── README.md              # Este archivo
```

La configuración (juegos, horarios, contraseña) se guarda en:

```
%APPDATA%\GameGuard\config.json
```

No subas ese archivo a internet: contiene la configuración local de esa PC.
