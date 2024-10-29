#!/bin/bash

# install.sh - Script de instalación para Say-Fi-Print

# Función para detectar el gestor de paquetes
detect_package_manager() {
    if command -v apt-get >/dev/null 2>&1; then
        echo "apt"
    elif command -v dnf >/dev/null 2>&1; then
        echo "dnf"
    elif command -v pacman >/dev/null 2>&1; then
        echo "pacman"
    else
        echo "unsupported"
    fi
}

# Función para instalar ffmpeg según el gestor de paquetes
install_ffmpeg() {
    PM=$(detect_package_manager)
    echo "Detectado gestor de paquetes: $PM"

    case "$PM" in
        apt)
            sudo apt update
            sudo apt install -y ffmpeg python3-venv
            ;;
        dnf)
            sudo dnf install -y ffmpeg python3-venv
            ;;
        pacman)
            sudo pacman -Sy --noconfirm ffmpeg python-virtualenv
            ;;
        *)
            echo "Gestor de paquetes no soportado. Por favor, instala ffmpeg manualmente."
            exit 1
            ;;
    esac
}

# Instalar ffmpeg
install_ffmpeg

# Definir directorio de instalación
INSTALL_DIR="/opt/Say-Fi-Print"

# Crear el directorio si no existe y mover el contenido
echo "Moviendo archivos a $INSTALL_DIR..."
sudo mkdir -p "$INSTALL_DIR"
sudo cp -r ./* "$INSTALL_DIR"
sudo chown -R $USER:$USER "$INSTALL_DIR"

# Navegar al directorio de instalación
cd "$INSTALL_DIR" || { echo "No se pudo acceder a $INSTALL_DIR"; exit 1; }

# Crear entorno virtual Python llamado sfprint
echo "Creando entorno virtual 'sfprint'..."
python3 -m venv sfprint

# Activar el entorno virtual e instalar requerimientos
echo "Instalando dependencias desde requirements.txt..."
source sfprint/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install --upgrade --force-reinstall websocket-client
deactivate

# Crear un archivo .env con valores predeterminados si no existe
if [ ! -f ".env" ]; then
    echo "Creando archivo .env con valores predeterminados..."
    cat << EOF > .env
SERVER_URL=domain.local
PORT=80
API_KEY=1234abcd-5678-efgh-9101-ijklmnopqrst
OPENAI_API_KEY=
GROQ_API_KEY=
ASSISTANT=Angie
MODELO=gpt-4o-mini
EOF
    echo ".env creado. Por favor, edítalo para agregar las claves API necesarias."
else
    echo ".env ya existe. Asegúrate de que las variables necesarias estén definidas."
fi

# Crear un enlace simbólico para ejecutar Transcriber_Ui.py con el entorno virtual
echo "Creando comando 'SFprint'..."
sudo bash -c "cat > /usr/local/bin/SFprint << EOF
#!/bin/bash
cd "/opt/Say-Fi-Print"
source \"sfprint/bin/activate\"
nohup python \"Transcriber_Ui.py\" \"\$@\" &
EOF"
sudo chmod +x /usr/local/bin/SFprint

# Crear archivo de escritorio para el icono
echo "Creando acceso directo en el menú de aplicaciones..."
DESKTOP_FILE="/usr/share/applications/sfprint.desktop"
sudo bash -c "cat > $DESKTOP_FILE << EOF
[Desktop Entry]
Name=SFPrint
Exec=SFprint
Icon=$INSTALL_DIR/static/gif.png
Type=Application
Categories=Utility;Application;
EOF"

# Asegurar permisos del icono
sudo chmod 644 $DESKTOP_FILE

echo "Instalación completada exitosamente."
echo "Puedes ejecutar la aplicación usando el comando 'SFprint' o desde el menú de aplicaciones."
echo "Si aún no has editado el archivo .env, hazlo ahora para proporcionar las claves API necesarias."
