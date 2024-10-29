::[Bat To Exe Converter]
::
::YAwzoRdxOk+EWAnk
::fBw5plQjdG8=
::YAwzuBVtJxjWCl3EqQJgSA==
::ZR4luwNxJguZRRnk
::Yhs/ulQjdF+5
::cxAkpRVqdFKZSDk=
::cBs/ulQjdF+5
::ZR41oxFsdFKZSDk=
::eBoioBt6dFKZSDk=
::cRo6pxp7LAbNWATEpCI=
::egkzugNsPRvcWATEpCI=
::dAsiuh18IRvcCxnZtBJQ
::cRYluBh/LU+EWAnk
::YxY4rhs+aU+JeA==
::cxY6rQJ7JhzQF1fEqQJQ
::ZQ05rAF9IBncCkqN+0xwdVs0
::ZQ05rAF9IAHYFVzEqQJQ
::eg0/rx1wNQPfEVWB+kM9LVsJDGQ=
::fBEirQZwNQPfEVWB+kM9LVsJDGQ=
::cRolqwZ3JBvQF1fEqQJQ
::dhA7uBVwLU+EWDk=
::YQ03rBFzNR3SWATElA==
::dhAmsQZ3MwfNWATElA==
::ZQ0/vhVqMQ3MEVWAtB9wSA==
::Zg8zqx1/OA3MEVWAtB9wSA==
::dhA7pRFwIByZRRnk
::Zh4grVQjdDWDJGqF7Q8WIVZkXg2MKFezCKYI6eT3oe+fpy0=
::YB416Ek+ZW8=
::
::
::978f952a14a936cc963da21a135fa983
@echo off
setlocal EnableDelayedExpansion
REM ================================================
REM Instalador de Say-Fi-Print para Windows
REM ================================================

REM 1. Verificar si se está ejecutando como administrador
echo Verificando permisos de administrador...
openfiles >nul 2>&1
if %errorlevel% NEQ 0 (
    echo.
    echo =============================================
    echo Por favor, ejecuta este script como Administrador.
    echo =============================================
    echo.
    pause
    exit /b
)
echo Permisos de administrador verificados.

REM 2. Crear la carpeta C:\Program Files\Say-Fi-Print si no existe
echo.
echo Creando carpeta C:\Program Files\Say-Fi-Print si no existe...
if not exist "C:\Program Files\Say-Fi-Print" (
    mkdir "C:\Program Files\Say-Fi-Print"
    if %errorlevel% NEQ 0 (
        echo.
        echo [Error] No se pudo crear la carpeta C:\Program Files\Say-Fi-Print.
        echo Verifica los permisos y vuelve a intentarlo.
        echo.
        pause
        exit /b
    )
    echo Carpeta creada exitosamente.
) else (
    echo La carpeta ya existe.
)

REM 3. Crear un archivo de exclusión para xcopy
echo.
echo Creando archivo de exclusión para xcopy...
echo install.bat>excluir.txt
echo install.exe>>excluir.txt
echo sfprint\>>excluir.txt
echo Exclusión creada: install.bat, install.exe, sfprint\
echo Archivo de exclusión creado.

REM 4. Copiar todos los archivos y carpetas desde el directorio actual a la carpeta de destino, excluyendo los archivos especificados
echo.
echo Copiando archivos a C:\Program Files\Say-Fi-Print...
xcopy /E /I /Y "%~dp0*" "C:\Program Files\Say-Fi-Print" /EXCLUDE:excluir.txt

REM Verificar si xcopy tuvo éxito
if %errorlevel% NEQ 0 (
    echo.
    echo [Error] Falló la copia de archivos a C:\Program Files\Say-Fi-Print.
    echo Verifica que los archivos existen y tienes los permisos necesarios.
    echo.
    del excluir.txt
    pause
    exit /b
)
echo Archivos copiados exitosamente.

REM 5. Eliminar el archivo de exclusión
echo.
echo Eliminando archivo de exclusión...
del excluir.txt
echo Archivo de exclusión eliminado.

REM 6. Crear el archivo .env en el directorio de instalación
echo.
echo Creando archivo .env en C:\Program Files\Say-Fi-Print...
(
    echo SERVER_URL=domain.local
    echo PORT=80
    echo API_KEY=1234abcd-5678-efgh-9101-ijklmnopqrst
    echo OPENAI_API_KEY=
    echo GROQ_API_KEY=
    echo ASSISTANT=Angie
    echo MODELO=gpt-4o-mini
) > "C:\Program Files\Say-Fi-Print\.env"

REM Verificar si el archivo .env se creó correctamente
if exist "C:\Program Files\Say-Fi-Print\.env" (
    echo Archivo .env creado exitosamente.
) else (
    echo.
    echo [Error] No se pudo crear el archivo .env.
    echo Verifica los permisos y vuelve a intentarlo.
    echo.
    pause
    exit /b
)

REM 7. Moverse a la carpeta creada
echo.
echo Cambiando al directorio C:\Program Files\Say-Fi-Print...
cd /d "C:\Program Files\Say-Fi-Print"
if %errorlevel% NEQ 0 (
    echo.
    echo [Error] No se pudo cambiar al directorio C:\Program Files\Say-Fi-Print.
    echo.
    pause
    exit /b
)
echo Cambio de directorio exitoso.

REM 8. Informar al usuario sobre los instaladores manuales
echo.
echo ===========================================================
echo Los instaladores de Visual Studio Build Tools y Python han sido copiados a "C:\Program Files\Say-Fi-Print".
echo.
echo Por favor, instala estos componentes manualmente ejecutando:
echo 1. vs_BuildTools.exe
echo 2. python-3.12.7-amd64.exe
echo.
echo Puedes elegir instalarlos ahora o más tarde según tu conveniencia.
echo ===========================================================
echo.

REM Opcional: Preguntar al usuario si desea ejecutar los instaladores ahora
set /p choice=¿Deseas ejecutar los instaladores ahora? (S/N): 

if /I "%choice%"=="S" (
    REM Verificar si vs_BuildTools.exe existe
    if exist "C:\Program Files\Say-Fi-Print\vs_BuildTools.exe" (
        echo.
        echo Ejecutando vs_BuildTools.exe...
        start "" /wait "C:\Program Files\Say-Fi-Print\vs_BuildTools.exe" --wait --norestart --add Microsoft.VisualStudio.Workload.VCTools
        if %errorlevel% NEQ 0 (
            echo.
            echo [Error] Falló la ejecución de vs_BuildTools.exe.
            echo Verifica el instalador y vuelve a intentarlo.
            echo.
            pause
            exit /b
        )
        echo vs_BuildTools.exe ejecutado exitosamente.
    ) else (
        echo.
        echo [Error] No se encontró vs_BuildTools.exe en "C:\Program Files\Say-Fi-Print".
        echo Asegúrate de que el archivo está presente.
        echo.
    )

    REM Verificar si python-3.12.7-amd64.exe existe
    if exist "C:\Program Files\Say-Fi-Print\python-3.12.7-amd64.exe" (
        echo.
        echo Ejecutando python-3.12.7-amd64.exe...
        start "" /wait "C:\Program Files\Say-Fi-Print\python-3.12.7-amd64.exe" InstallAllUsers=1 PrependPath=1 Include_test=0
        if %errorlevel% NEQ 0 (
            echo.
            echo [Error] Falló la ejecución de python-3.12.7-amd64.exe.
            echo Verifica el instalador y vuelve a intentarlo.
            echo.
            pause
            exit /b
        )
        echo python-3.12.7-amd64.exe ejecutado exitosamente.
    ) else (
        echo.
        echo [Error] No se encontró python-3.12.7-amd64.exe en "C:\Program Files\Say-Fi-Print".
        echo Asegúrate de que el archivo está presente.
        echo.
    )
) else (
    echo Puedes ejecutar los instaladores más tarde desde "C:\Program Files\Say-Fi-Print".
)

REM 9. Mover la carpeta ffmpeg a C:\
echo.
echo Moviendo carpeta ffmpeg a C:\...
if exist "ffmpeg" (
    xcopy /E /I /Y "ffmpeg" "C:\ffmpeg"
    if %errorlevel% NEQ 0 (
        echo.
        echo [Error] Falló la copia de ffmpeg a C:\ffmpeg.
        echo Verifica que la carpeta ffmpeg existe y tienes los permisos necesarios.
        echo.
    ) else (
        echo ffmpeg copiado exitosamente a C:\ffmpeg.
    )
) else (
    echo.
    echo [Advertencia] La carpeta ffmpeg no se encontró en el directorio de instalación.
    echo.
)

REM 10. Crear variables de entorno para ffmpeg
echo.
echo Configurando variables de entorno para ffmpeg...
REM Verificar si C:\ffmpeg\bin ya está en PATH
echo %PATH% | findstr /I /C:"C:\ffmpeg\bin" >nul
if %errorlevel% NEQ 0 (
    setx /M PATH "%PATH%;C:\ffmpeg\bin"
    if %errorlevel% NEQ 0 (
        echo.
        echo [Error] No se pudo actualizar la variable PATH.
        echo Verifica los permisos y vuelve a intentarlo.
        echo.
    ) else (
        echo.
        echo Se ha añadido "C:\ffmpeg\bin" al PATH del sistema.
        echo Puede ser necesario reiniciar el equipo para que los cambios surtan efecto.
        echo.
    )
) else (
    echo.
    echo "C:\ffmpeg\bin" ya está presente en el PATH del sistema.
    echo.
)

REM 11. Crear entorno virtual Python con nombre sfprint
echo.
echo Verificando si el entorno virtual "sfprint" ya existe...
if exist "sfprint" (
    echo La carpeta del entorno virtual "sfprint" ya existe.
) else (
    echo Creando entorno virtual "sfprint"...
    python -m venv sfprint
    if %errorlevel% NEQ 0 (
        echo.
        echo [Error] No se pudo crear el entorno virtual "sfprint".
        echo Asegúrate de que Python está instalado correctamente.
        echo.
        pause
        exit /b
    ) else (
        echo Entorno virtual "sfprint" creado exitosamente.
    )
)

REM 12. Activar el entorno virtual
echo.
echo Activando el entorno virtual "sfprint"...
call sfprint\Scripts\activate.bat
if %errorlevel% NEQ 0 (
    echo.
    echo [Error] No se pudo activar el entorno virtual "sfprint".
    echo.
    pause
    exit /b
)
echo Entorno virtual "sfprint" activado.

REM 13. Instalar requerimientos desde requirements.txt
echo.
echo Verificando la existencia de "requirements.txt"...
if exist "requirements.txt" (
    echo Instalando dependencias desde requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% NEQ 0 (
        echo.
        echo [Error] Falló la instalación de dependencias.
        echo Verifica el archivo requirements.txt y tu conexión a Internet.
        echo.
    ) else (
        echo Dependencias instaladas exitosamente.
    )
) else (
    echo.
    echo [Error] No se encontró "requirements.txt".
    echo.
)

REM 14. Desactivar el entorno virtual
echo.
echo Desactivando el entorno virtual "sfprint"...
call sfprint\Scripts\deactivate.bat
if %errorlevel% NEQ 0 (
    echo.
    echo [Error] No se pudo desactivar el entorno virtual "sfprint".
    echo.
    pause
    exit /b
)
echo Entorno virtual "sfprint" desactivado.

REM 15. Crear acceso directo de SFPrint.exe en el escritorio
echo.
echo Verificando la existencia de SFPrint.exe...
if exist "C:\Program Files\Say-Fi-Print\SFPrint.exe" (
    echo Creando acceso directo en el escritorio...

    REM Escribir el script de PowerShell en un archivo temporal en %TEMP%
    (
        echo try ^{
        echo     $s = New-Object -COMObject WScript.Shell
        echo     $desktop = [Environment]::GetFolderPath^('Desktop'^)
        echo     $shortcut = $s.CreateShortcut^("$desktop\SFPrint.lnk"^)
        echo     $shortcut.TargetPath = 'C:\Program Files\Say-Fi-Print\SFPrint.exe'
        echo     $shortcut.WorkingDirectory = 'C:\Program Files\Say-Fi-Print'
        echo     $shortcut.IconLocation = 'C:\Program Files\Say-Fi-Print\SFPrint.exe'
        echo     $shortcut.Save^(^)
        echo     exit 0
        echo ^} catch ^{
        echo     Write-Error $_.Exception.Message
        echo     exit 1
        echo ^}
    ) > "%TEMP%\temp_create_shortcut.ps1"

    REM Verificar que el archivo temporal se creó
    if exist "%TEMP%\temp_create_shortcut.ps1" (
        REM Ejecutar el script de PowerShell
        powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\temp_create_shortcut.ps1"

        REM Comprobar si el script se ejecutó correctamente
        if %errorlevel% NEQ 0 (
            echo.
            echo [Error] No se pudo crear el acceso directo en el escritorio.
            echo Revisa los permisos y la existencia de SFPrint.exe.
            echo.
        ) else (
            echo Acceso directo creado exitosamente en el escritorio.
        )

        REM Eliminar el archivo temporal
        del "%TEMP%\temp_create_shortcut.ps1"

    ) else (
        echo.
        echo [Error] No se pudo crear el archivo temporal para PowerShell.
        echo.
    )

) else (
    echo.
    echo [Error] No se encontró SFPrint.exe en "C:\Program Files\Say-Fi-Print".
    echo No se pudo crear el acceso directo.
    echo.
)

echo.
echo ============================================
echo Instalación completada con éxito.
echo ============================================
echo.
pause
