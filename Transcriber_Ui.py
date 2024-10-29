# Transcriber_Ui.py

import tkinter as tk
from tkinter import messagebox, Toplevel, Text, Scrollbar
from PIL import Image, ImageTk, ImageOps, ImageDraw, ImageFilter
import os
import threading
import time
from transcriber import Transcriber  # Asegúrate de tener este módulo
import re
from pathlib import Path
from dotenv import dotenv_values
import websocket
import json
import queue
import requests  # Para enviar archivos al servidor y descargar audio
from tts import TTS  # Asegúrate de tener este módulo

class TranscriberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sci-Fi-Print")
        self.root.configure(bg="#1A1A1A")

        self.tts = TTS()  # Instanciar el TTS en el cliente
        self.transcriber = Transcriber()
        self.state = "escuchando"

        # Cargar variables de entorno
        dotenv_path = Path('.') / '.env'
        self.env_vars = dotenv_values(dotenv_path)
        self.SERVER_URL = self.env_vars.get("SERVER_URL", "raspi.local")
        self.API_KEY = self.env_vars.get("API_KEY")
        if not self.SERVER_URL:
            messagebox.showwarning("Advertencia", "SERVER_URL no está definida en el archivo .env. Usando valor predeterminado 'raspi.local'.")
        
        if not self.API_KEY:
            messagebox.showwarning("Advertencia", "API_KEY no está definida en el archivo .env. Algunas funcionalidades estarán deshabilitadas.")
        
        self.notification_queue = queue.Queue()

        # Bandera para controlar actualizaciones programáticas del volumen
        self.updating_volume_from_server = False
        # Bandera para controlar actualizaciones programáticas de 'saytts'
        self.updating_saytts_from_server = False

        # Frame central que contiene la imagen o GIF
        self.frame_central = tk.Frame(self.root, bg="#1A1A1A")
        self.frame_central.pack(expand=True)

        # Etiqueta para mostrar la imagen o GIF
        self.label_media = tk.Label(self.frame_central, bg="#1A1A1A")
        self.label_media.pack(expand=True)

        # Ruta de la imagen inicial
        self.image_path = "static/gif0.png"
        self.is_playing_animation = False
        self.current_image_size = (400, 400)  # Tamaño inicial común para imagen y animación
        self.crop_percentage = 0.65  # Porcentaje del tamaño original para el recorte cuadrado
        self.circular_crop_percentage = 0.70  # Porcentaje del tamaño recortado para el recorte circular
        self.set_image(self.image_path)

        # Etiqueta para mostrar el estado actual (Escuchando, Grabando, Ejecutando)
        self.label_estado = tk.Label(self.root, text="Escuchando...", fg="white", bg="#1A1A1A", font=("Helvetica", 12))
        self.label_estado.pack(pady=2)

        self.label_notify = tk.Label(self.root, text=" ", fg="white", bg="#1A1A1A", font=("Helvetica", 12), wraplength=400, justify='left', width=50)
        self.label_notify.pack(pady=1)

        # Frame para controles adicionales
        self.controls_frame = tk.Frame(self.root, bg="#1A1A1A")
        self.controls_frame.pack(pady=5)

        # Botón para configurar
        self.button_config = tk.Button(self.controls_frame, text="Configuración", command=self.configurar, bg="#333333", fg="white", font=("Helvetica", 12))
        self.button_config.pack(side="top", padx=10, pady=20)

        self.label_Vol = tk.Label(self.controls_frame, text="Volumen:", fg="white", bg="#1A1A1A", font=("Helvetica", 12), wraplength=400, justify='left', width=50)
        self.label_Vol.pack(padx=1, pady=1)

        # Deslizador de volumen sin el argumento 'command'
        self.volume_slider = tk.Scale(self.controls_frame, label='', from_=0, to=100, orient='horizontal', bg="#1A1A1A", fg="white", length=200, width=10)
        self.volume_slider.set(100)  # Volumen inicial al 100%
        self.volume_slider.pack(side="top", padx=10, pady=1)
        # Enlazar el evento '<ButtonRelease-1>' al deslizador de volumen
        self.volume_slider.bind("<ButtonRelease-1>", self.change_volume)

        # Checkbox para controlar 'sayllm'
        self.sayllm_var = tk.BooleanVar(value=False)
        self.checkbox_sayllm = tk.Checkbutton(self.controls_frame, text="Notificaciones con IA", variable=self.sayllm_var, command=self.change_sayllm, bg="#1A1A1A", fg="white", font=("Helvetica", 12), selectcolor="#1A1A1A")
        self.checkbox_sayllm.pack(padx=10, pady=10)

        # Checkbox para controlar 'saytts'
        self.saytts_var = tk.BooleanVar(value=False)
        self.checkbox_saytts = tk.Checkbutton(self.controls_frame, text="Sintetizar voz en el cliente", variable=self.saytts_var, command=self.change_saytts, bg="#1A1A1A", fg="white", font=("Helvetica", 12), selectcolor="#1A1A1A")
        self.checkbox_saytts.pack(padx=10, pady=10)

        # Cerrar aplicación completamente al cerrar la ventana
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Configuración del WebSocket solo si SERVER_URL y API_KEY están definidas
        if self.SERVER_URL and self.API_KEY:
            self.ws_url = f"ws://{self.SERVER_URL}:6996/ws"
            self.ws = None
            self.ws_thread = threading.Thread(target=self.connect_to_server_ws, daemon=True)
            self.ws_thread.start()
        else:
            self.ws_url = None
            self.ws = None
            print("WebSocket deshabilitado debido a la falta de SERVER_URL o API_KEY.")

        # Hilo para ejecutar el transcriptor
        self.thread = threading.Thread(target=self.run_transcriber, daemon=True)
        self.thread.start()

    def connect_to_server_ws(self):
        """Conecta al servidor WebSocket y maneja la comunicación."""
        while True:
            try:
                self.ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_open=self.on_server_open,
                    on_message=self.on_server_message,
                    on_error=self.on_server_error,
                    on_close=self.on_server_close
                )
                self.ws.run_forever()
            except Exception as e:
                print(f"Excepción en connect_to_server_ws: {e}")
            print("Conexión WebSocket con el servidor cerrada. Reintentando en 5 segundos...")
            time.sleep(5)

    def on_server_open(self, ws):
        print("Conexión WebSocket con el servidor establecida")
        # Solicitar el volumen actual
        self.request_volume()
        # Solicitar el valor actual de 'sayllm'
        self.request_sayllm()
        # Solicitar el valor actual de 'saytts'
        self.request_saytts()
        # No enviar 'set_saytts' al servidor al iniciar

    def on_server_message(self, ws, message):
        # Manejar mensajes entrantes del servidor
        try:
            data = json.loads(message)
            if 'volume' in data:
                volume_level = data['volume']
                self.updating_volume_from_server = True  # Bandera activada antes de actualizar el deslizador
                self.volume_slider.set(volume_level)
                self.updating_volume_from_server = False  # Desactivar la bandera después de actualizar
                print(f"Volumen actual establecido a {volume_level}%")
            if 'sayllm' in data:
                sayllm_value = data['sayllm']
                self.sayllm_var.set(sayllm_value)
                print(f"El valor actual de 'sayllm' es {sayllm_value}")
            if 'saytts' in data:
                saytts_value = data['saytts']
                self.updating_saytts_from_server = True
                self.saytts_var.set(saytts_value)
                self.updating_saytts_from_server = False
                print(f"El valor actual de 'saytts' es {saytts_value}")
            if 'message' in data:
                # Mostrar el mensaje recibido
                self.state = "ejecutando"
                self.label_estado.config(text="Ejecutando...")
                self.play_animation("static/images_executing")
                message = data.get('message', '')

                self.label_notify.config(text=message)

                #self.root.after(15000, lambda: self.label_notify.config(text=" "))
                self.root.after(1500, lambda: self.reset_to_listening())

                # Si 'saytts' está activado en el cliente, sintetizar y reproducir el audio localmente
                if self.saytts_var.get() and message:
                    self.state = "ejecutando"
                    self.label_estado.config(text="Ejecutando...")
                    self.play_animation("static/images_executing")

                    self.tts.speak(message)

                    self.root.after(1500, lambda: self.reset_to_listening())


            if 'error' in data:
                print(f"Error del servidor: {data['error']}")
        except Exception as e:
            print(f"Error al procesar mensaje del servidor: {e}")

    def on_server_error(self, ws, error):
        print(f"Error en WebSocket con el servidor: {error}")

    def on_server_close(self, ws, close_status_code, close_msg):
        print("Conexión WebSocket con el servidor cerrada")

    def request_volume(self):
        if self.ws and self.ws.sock and self.ws.sock.connected:
            payload = {
                "API_KEY": self.API_KEY,
                "action": "get_volume"
            }
            self.ws.send(json.dumps(payload))
            print("Solicitud de volumen actual enviada al servidor")

    def request_sayllm(self):
        if self.ws and self.ws.sock and self.ws.sock.connected:
            payload = {
                "API_KEY": self.API_KEY,
                "action": "get_sayllm"
            }
            self.ws.send(json.dumps(payload))
            print("Solicitud del valor actual de 'sayllm' enviada al servidor")

    def request_saytts(self):
        if self.ws and self.ws.sock and self.ws.sock.connected:
            payload = {
                "API_KEY": self.API_KEY,
                "action": "get_saytts"
            }
            self.ws.send(json.dumps(payload))
            print("Solicitud del valor actual de 'saytts' enviada al servidor")

    def change_volume(self, event):
        if self.updating_volume_from_server:
            return  # No enviar actualización al servidor si estamos actualizando desde el servidor
        try:
            volume_level = int(self.volume_slider.get())
            # Enviar mensaje al servidor vía WebSocket
            if self.ws and self.ws.sock and self.ws.sock.connected:
                payload = {
                    "API_KEY": self.API_KEY,
                    "action": "set_volume",
                    "volume": volume_level
                }
                self.ws.send(json.dumps(payload))
                print(f"Volumen ajustado a {volume_level}%")
            else:
                print("No hay conexión WebSocket con el servidor. El volumen no se pudo ajustar.")
        except Exception as e:
            print(f"Excepción al cambiar el volumen: {e}")

    def change_sayllm(self):
        if not self.API_KEY:
            messagebox.showwarning("Advertencia", "API_KEY no está definida. No se puede cambiar 'sayllm'.")
            self.sayllm_var.set(False)
            return

        try:
            sayllm_value = self.sayllm_var.get()
            print(f"Cambiando 'sayllm' a {sayllm_value}")  # Agregar log
            # Enviar mensaje al servidor vía WebSocket
            if self.ws and self.ws.sock and self.ws.sock.connected:
                payload = {
                    "API_KEY": self.API_KEY,
                    "action": "set_sayllm",
                    "sayllm": sayllm_value
                }
                self.ws.send(json.dumps(payload))
                print(f"El valor de 'sayllm' ha sido establecido a {sayllm_value}")
            else:
                print("No hay conexión WebSocket con el servidor. 'sayllm' no se pudo ajustar.")
        except Exception as e:
            print(f"Excepción al cambiar 'sayllm': {e}")

    def change_saytts(self):
        if not self.API_KEY:
            messagebox.showwarning("Advertencia", "API_KEY no está definida. No se puede cambiar 'saytts'.")
            self.saytts_var.set(False)
            return

        if self.updating_saytts_from_server:
            return  # Evitar enviar actualización al servidor si viene del servidor
        try:
            saytts_value = self.saytts_var.get()
            print(f"Cambiando 'saytts' a {saytts_value}")  # Agregar log
            # Enviar mensaje al servidor vía WebSocket
            if self.ws and self.ws.sock and self.ws.sock.connected:
                payload = {
                    "API_KEY": self.API_KEY,
                    "action": "set_saytts",
                    "saytts": saytts_value
                }
                self.ws.send(json.dumps(payload))
                print(f"El valor de síntesis de voz ha sido establecido a {saytts_value}")
            else:
                print("No hay conexión WebSocket con el servidor. 'saytts' no se pudo ajustar.")
        except Exception as e:
            print(f"Excepción al cambiar 'saytts': {e}")

    def set_image(self, image_path):
        if not self.is_playing_animation:
            self.update_media(image_path)

    def update_media(self, image_path):
        try:
            image = Image.open(image_path)
            # Recortar y redimensionar la imagen o animación con las mismas propiedades
            crop_width = int(image.width * self.crop_percentage)
            crop_height = int(image.height * self.crop_percentage)
            left = (image.width - crop_width) / 2
            top = (image.height - crop_height) / 2
            right = (image.width + crop_width) / 2
            bottom = (image.height + crop_height) / 2
            image = image.crop((left, top, right, bottom))
            
            width, height = self.current_image_size
            if width <= 100 or height <= 100:
                width, height = 100, 100
            
            image = image.resize((width, height), Image.LANCZOS)
            
            mask = Image.new('L', (width, height), 0)
            draw = ImageDraw.Draw(mask)
            circle_diameter = int(min(width, height) * self.circular_crop_percentage)
            offset = (width - circle_diameter) // 2
            draw.ellipse((offset, offset, width - offset, height - offset), fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(35))
            
            image = ImageOps.fit(image, mask.size, centering=(0.5, 0.5))
            image.putalpha(mask)
            
            self.image_tk = ImageTk.PhotoImage(image)
            self.label_media.configure(image=self.image_tk)
            self.label_media.image = self.image_tk
        except Exception as e:
            print(f"Error al actualizar la imagen: {e}")

    def play_animation(self, folder_path):
        self.is_playing_animation = True
        self.image_files = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))])
        self.current_frame = 0
        self.stop_animation()
        self.update_animation()

    def update_animation(self):
        if self.image_files:
            image_path = self.image_files[self.current_frame]
            self.update_media(image_path)
            self.current_frame = (self.current_frame + 1) % len(self.image_files)
            self.animation_id = self.root.after(100, self.update_animation)  # Aproximadamente 10 FPS

    def stop_animation(self):
        if hasattr(self, 'animation_id') and self.animation_id:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None
        self.is_playing_animation = False

    def run_transcriber(self):
        self.label_notify.config(text=" ")
        while True:
            self.state = "escuchando"
            self.stop_animation()
            self.set_image("static/gif0.png")
            self.label_estado.config(text="Escuchando...")
            text_after_keyword = self.transcriber.listen_for_keyword()

            if text_after_keyword is not None:
                self.state = "grabando"
                self.label_estado.config(text="Grabando...")
                self.play_animation("static/images_recording")
                command = self.transcriber.listen_for_command()
                self.label_notify.config(text=f"Comando: {command}")
                if command:
                    print(f"Comando recibido: {command}")
                    data = {"text": command}
                else:
                    self.reset_to_listening()
                    self.label_notify.config(text=" ")
                    self.transcriber.playsound('sounds/stop_sound.mp3')
                    continue

                self.state = "ejecutando"
                self.label_estado.config(text="Ejecutando...")
                self.play_animation("static/images_executing")
                self.transcriber.playsound('sounds/stop_sound.mp3')
                self.send_message_to_server(data)
                self.root.after(15000, lambda: self.label_notify.config(text=" "))
                self.root.after(1500, lambda: self.reset_to_listening())

    def send_message_to_server(self, data):
        """Envía un mensaje al servidor a través del WebSocket."""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            try:
                payload = {
                    "API_KEY": self.API_KEY,
                    "action": "process_text",
                    "text": data["text"]
                }
                self.ws.send(json.dumps(payload))
                print(f"Mensaje enviado al servidor: {data['text']}")
            except Exception as e:
                print(f"Error al enviar mensaje al servidor: {e}")
        else:
            print("No hay conexión WebSocket con el servidor. El mensaje no se pudo enviar.")

    def reset_to_listening(self):
        self.stop_animation()
        self.set_image("static/gif0.png")
        self.label_estado.config(text="Escuchando...")

    def play_audio_from_url(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                # Guardar el archivo de audio temporalmente
                audio_file = 'temp_audio.mp3'
                with open(audio_file, 'wb') as f:
                    f.write(response.content)
                # Reproducir el audio
                self.transcriber.playsound(audio_file)
                # Eliminar el archivo temporal
                os.remove(audio_file)
            else:
                print(f"Error al descargar el audio: {response.status_code}")
        except Exception as e:
            print(f"Error al reproducir el audio: {e}")

    def configurar(self):
        dotenv_path = Path('.') / '.env'
        rol_path = Path('.') / 'rol.txt'

        if not dotenv_path.exists():
            messagebox.showerror("Error", "No se encontró el archivo .env")
            return

        # Leer el archivo .env
        with open(dotenv_path, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()

        self.env_vars = {}
        self.env_lines = env_lines  # Guardar para uso posterior

        # Parsear las líneas y extraer las variables
        current_key = None
        current_value_lines = []
        for line in env_lines:
            line = line.rstrip('\n')
            if not line.strip() or line.strip().startswith('#'):
                continue  # Saltar líneas vacías y comentarios
            if '=' in line:
                if current_key:
                    self.env_vars[current_key] = '\n'.join(current_value_lines).rstrip('\n')
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Manejar valores que empiezan con comillas triples
                if value.startswith('"""'):
                    value = value[3:]
                    if value.endswith('"""'):
                        value = value[:-3]
                        current_value_lines = [value]
                        self.env_vars[key] = '\n'.join(current_value_lines)
                        current_key = None
                        current_value_lines = []
                    else:
                        current_value_lines = [value]
                        current_key = key
                else:
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    self.env_vars[key] = value
                    current_key = None
                    current_value_lines = []
            else:
                # Continuación de un valor multilínea
                if current_key:
                    if line.endswith('"""'):
                        current_value_lines.append(line[:-3])
                        self.env_vars[current_key] = '\n'.join(current_value_lines)
                        current_key = None
                        current_value_lines = []
                    else:
                        current_value_lines.append(line)

        if current_key:
            self.env_vars[current_key] = '\n'.join(current_value_lines).rstrip('\n')

        # Leer el archivo rol.txt
        if not rol_path.exists():
            # Crear rol.txt si no existe
            with open(rol_path, 'w', encoding='utf-8') as f:
                f.write("")

        with open(rol_path, 'r', encoding='utf-8') as f:
            rol_content = f.read()

        config_window = Toplevel(self.root)
        config_window.title("Configuración")
        config_window.configure(bg="#1A1A1A")
        
        fields = ["Servidor", "Puerto", "OpenAI API", "Groq API", "Server API", "Asistente", "Modelo de lenguaje", "Rol"]
        self.entries = {}
        
        field_to_env_var = {
            "Servidor": "SERVER_URL",
            "Puerto": "PORT",
            "OpenAI API": "OPENAI_API_KEY",
            "Groq API": "GROQ_API_KEY",
            "Server API": "API_KEY",
            "Asistente": "ASSISTANT",
            "Modelo de lenguaje": "MODELO",
            # "Rol" ya no se maneja desde .env
        }
        
        for field in fields:
            label = tk.Label(config_window, text=f"{field}:", fg="white", bg="#1A1A1A", font=("Helvetica", 10))
            label.pack(pady=5)
            if field == 'Rol':
                entry_frame = tk.Frame(config_window)
                entry_frame.pack(pady=5, fill='both', expand=True)
                scrollbar = Scrollbar(entry_frame)
                scrollbar.pack(side='right', fill='y')
                entry = Text(entry_frame, height=10, wrap='word', yscrollcommand=scrollbar.set)
                scrollbar.config(command=entry.yview)
                entry.pack(side='left', fill='both', expand=True)
                entry.insert('1.0', rol_content)
                self.entries[field] = entry
            else:
                env_var = field_to_env_var.get(field)
                value = self.env_vars.get(env_var, "")
                show_char = '*' if 'API' in field else None
                entry = tk.Entry(config_window, width=40, show=show_char)
                entry.insert(0, value)
                entry.pack(pady=5, fill='x')
                self.entries[field] = entry
        
        # Botón para enviar la configuración
        send_button = tk.Button(config_window, text="Enviar", command=lambda: self.send_config(config_window), bg="#333333", fg="white", font=("Helvetica", 12))
        send_button.pack(pady=10)
        self.config_window = config_window  # Guardar referencia a la ventana

    def send_config(self, config_window):
        dotenv_path = Path('.') / '.env'
        rol_path = Path('.') / 'rol.txt'

        # Leer la API_KEY actual antes de modificar el .env
        current_env = dotenv_values(dotenv_path)
        old_api_key = current_env.get("API_KEY", "")
        if not old_api_key:
            messagebox.showerror("Error", "API_KEY no está definida en el archivo .env")
            print("API_KEY no está definida en el archivo .env")
            return

        # Obtener los datos de los campos
        config_data = {field: (entry.get() if isinstance(entry, tk.Entry) else entry.get('1.0', 'end-1c').rstrip('\n')) for field, entry in self.entries.items()}
        
        field_to_env_var = {
            "Servidor": "SERVER_URL",
            "Puerto": "PORT",
            "OpenAI API": "OPENAI_API_KEY",
            "Groq API": "GROQ_API_KEY",
            "Server API": "API_KEY",
            "Asistente": "ASSISTANT",
            "Modelo de lenguaje": "MODELO",
            # "Rol" ya no se maneja desde .env
        }
        
        # Actualizar las variables en self.env_vars
        for field, value in config_data.items():
            if field != "Rol":
                env_var = field_to_env_var.get(field)
                self.env_vars[env_var] = value

        # Reescribir las líneas del archivo .env
        new_env_lines = []
        keys_written = set()
        current_key = None
        is_multiline = False

        for line in self.env_lines:
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('#'):
                new_env_lines.append(line.rstrip('\n'))
                continue
            if '=' in line:
                if is_multiline:
                    is_multiline = False
                    continue  # Omitir líneas de valores multilínea ya procesadas
                key, _ = line.split('=', 1)
                key = key.strip()
                if key in self.env_vars:
                    value = self.env_vars[key]
                    if '\n' in value:
                        # Escribir variable multilínea con comillas triples
                        new_env_lines.append(f'{key}="""{value}"""')
                    else:
                        new_env_lines.append(f'{key}={value}')
                    keys_written.add(key)
                    current_key = key
                    is_multiline = '\n' in value
                else:
                    new_env_lines.append(line.rstrip('\n'))
            else:
                if is_multiline and current_key:
                    continue  # Omitir líneas de valores multilínea ya escritas
                else:
                    new_env_lines.append(line.rstrip('\n'))

        # Añadir variables nuevas o que no estaban en el archivo original
        for key, value in self.env_vars.items():
            if key not in keys_written:
                if '\n' in value:
                    new_env_lines.append(f'{key}="""{value}"""')
                else:
                    new_env_lines.append(f'{key}={value}')
                keys_written.add(key)

        with open(dotenv_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_env_lines))

        # Actualizar rol.txt
        rol_content = config_data.get("Rol", "")
        with open(rol_path, 'w', encoding='utf-8') as f:
            f.write(rol_content)

        # Enviar los archivos al servidor
        try:
            with open(dotenv_path, 'rb') as f_env, open(rol_path, 'rb') as f_rol:
                files = {
                    'env_file': ('config.env', f_env, 'text/plain'),
                    'rol_file': ('rol.txt', f_rol, 'text/plain'),
                }
                # Leer SERVER_URL del archivo .env para construir la URL del servidor
                server_url = self.env_vars.get("SERVER_URL", "raspi.local")
                FASTAPI_SERVER_URL = f"http://{server_url}:6996/enviroments"
                
                headers = {
                    "API_KEY": old_api_key  # Usar la API Key antigua para autenticar la solicitud
                }
                
                print(f"Enviando solicitud a {FASTAPI_SERVER_URL} con API_KEY: {old_api_key}")
                response = requests.post(
                    FASTAPI_SERVER_URL,
                    files=files,
                    headers=headers
                )
                if response.status_code == 200:
                    messagebox.showinfo("Configuración", "Variables actualizadas correctamente y enviadas al servidor.")
                else:
                    messagebox.showerror("Error", f"Error al enviar archivos al servidor: {response.status_code} {response.text}")
                    print(f"Error al enviar archivos al servidor: {response.status_code} {response.text}")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al enviar los archivos al servidor: {str(e)}")
            print(f"Ocurrió un error al enviar los archivos al servidor: {str(e)}")
            return  # Salir del método sin mostrar el mensaje de éxito

        # Leer el nuevo API_KEY para futuras solicitudes
        new_env_config = dotenv_values(dotenv_path)
        new_api_key = new_env_config.get("API_KEY", "")
        if new_api_key:
            print("Actualizando API_KEY en el cliente.")
            # Actualizar la API_KEY en una variable de instancia para futuras solicitudes
            self.API_KEY = new_api_key
        else:
            print("Advertencia: No se encontró una nueva API_KEY en el archivo .env.")

        print("Configuración enviada:", {k: v for k, v in config_data.items() if k != "Rol"})
        messagebox.showinfo("Configuración", "Variables actualizadas correctamente")
        config_window.destroy()  # Cerrar la ventana de configuración

    def on_closing(self):
        self.root.quit()
        self.root.destroy()
        os._exit(0)  # Asegura que todos los hilos se cierren completamente

if __name__ == "__main__":
    root = tk.Tk()
    app = TranscriberApp(root)
    root.mainloop()
