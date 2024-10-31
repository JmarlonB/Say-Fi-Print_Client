# Say-Fi-Print_Client

#### Say-Fi-Print es una solucion que se integra con Klipper/Moonraker para interactuar de manera audible  con impresoras 3D.

## Requisitos

#### *Una SBC con Klipper y Moonraker instalados para el servidor.
#### *Sistemas operativos Windows o Linux para el cliente.
#### *Recomendamos usar claves Api de Open AI y GROQ para disfrutar de todo el potencial de esta aplicacion.

## Windows 

#### Ejecutar install.exe
#### si no tienes instalado python o vs_BuildTools presionar S e instalar manualmente.
#### Cuando termine de instalar ejecuta SFPrint en el escritorio.
#### SFPrint se se instalara en C:\program files\Say-Fi-Print 

## Linux

```shell
git clone https://github.com/JmarlonB/Say-Fi-Print_Client.git
cd Say-Fi-Print_Client
chmod +x install.sh
./install.sh

```
## Uso

#### En windows ejecutar el aceso directo en el escritorio llamado SFPrint.
#### En linux Pueden ejecutar el aceso directo con nombre SFPrint o pueden llamarlo desde el terminal escribiendo SFprint.
#### Al abrirlo por primera vez hacer clic en configurar, ahi deben de ingresar la ip o el nombre de dominio del servidor, 
#### el puerto, la api key principal, la de openai y la de groq, tambien el nombre del asistente el modelo de lenguaje y el rol que asumira el asistente.
#### ¡Y a Disfrutar!

## Consideraciones Adicionales

#### Tanto el cliente como el servidor van por defecto con una api key generica pueden asignarle la apikey de moonraker si cean una o asignarle una nueva y completamente diferente lo cual recomendamos.
#### Aqui el servidor Say-Fi-Print: https://github.com/JmarlonB/Say-Fi-Print_Server
