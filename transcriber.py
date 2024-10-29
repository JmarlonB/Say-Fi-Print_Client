# transcriber.py

import speech_recognition as sr
import os
import time
import queue
import threading
from dotenv import load_dotenv
from rapidfuzz import fuzz  # Reemplazado 'fuzzywuzzy' por 'rapidfuzz'
import webrtcvad
import collections
import subprocess
import websocket
import json
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import requests

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class Transcriber:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.keyword = os.getenv("ASSISTANT")
        self.language = 'es-ES'
        self.audio_buffer = queue.Queue(maxsize=6)
        self.cleanup_time = 10  # Tiempo de limpieza en segundos
        self.time_counter = 0
        self.error_counter = 0
        self.reset_threshold = 20  # Umbral de reinicio en errores consecutivos
        self.playsound('sounds/spaceship.wav')
        self.psilencio = False
        self.buffer_processing_thread = threading.Thread(target=self.process_audio_buffer)
        self.buffer_processing_thread.start()
        self.vad = webrtcvad.Vad(3)  # Nivel de agresividad aumentado

        # Configuración del WebSocket
        self.server_url = os.getenv("SERVER_URL")
        self.api_key = os.getenv("API_KEY")
        if not self.server_url or not self.api_key:
            print("Advertencia: SERVER_URL y/o API_KEY no están definidas en el archivo .env. Algunas funcionalidades estarán deshabilitadas.")
            self.ws_url = None
            self.ws = None
        else:
            self.ws_url = f"ws://{self.server_url}:6996/ws"
            self.ws = None
            self.ws_thread = threading.Thread(target=self.connect_to_server_ws, daemon=True)
            self.ws_thread.start()

        self.notification_queue = queue.Queue()

    def playsound(self, file_path):
        """Reproduce un sonido dado un archivo de audio usando ffplay."""
        subprocess.call(['ffplay', '-nodisp', '-autoexit', file_path], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    def adjust_to_ambient_noise(self, source):
        self.recognizer.adjust_for_ambient_noise(source, duration=1.5)

    def clear_audio_buffer(self):
        while not self.audio_buffer.empty():
            self.audio_buffer.get_nowait()
            print(f"Limpiando buffer")

    def listen_for_keyword(self):
        keyword_detected = self.detect_keyword_in_buffer()
        return keyword_detected

    def process_audio_buffer(self):
        while True:
            audio_segment = self.audio_buffer.get()
            keyword_detected = self.detect_keyword_in_segment(audio_segment)
            if keyword_detected:
                break

    def detect_keyword_in_buffer(self):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            while True:
                try:
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                    print("Audio capturado")
                    if self.audio_buffer.full():
                        self.audio_buffer.get_nowait()  # Eliminar el elemento más antiguo del buffer
                    self.audio_buffer.put(audio)
                    print("Audio capturado en el buffer")

                    self.time_counter += 1
                    if self.time_counter >= self.cleanup_time:
                        self.clear_audio_buffer()
                        self.time_counter = 0

                    keyword_detected = self.detect_keyword_in_segment(audio)
                    if keyword_detected:
                        print(f"Palabra clave detectada: {keyword_detected}")
                        self.clear_audio_buffer()
                        return keyword_detected
                except sr.WaitTimeoutError:
                    print("Tiempo de espera agotado")
                    self.time_counter += 1
                    if self.time_counter >= self.cleanup_time:
                        self.clear_audio_buffer()
                        self.time_counter = 0
                    self.error_counter += 1  # Incrementar el contador de errores
                    if self.error_counter >= self.reset_threshold:
                        print(f"Reiniciando reconocimiento de voz después de {self.error_counter} errores consecutivos.")
                        self.recognizer = sr.Recognizer()  # Reiniciar el reconocedor
                        self.error_counter = 0
                    continue

    def detect_keyword_in_segment(self, audio_segment):
        try:
            text = self.recognizer.recognize_google(audio_segment, language=self.language)
            print(f"Texto reconocido: {text}")
            words = text.split()
            for word in words:
                similarity_reset = fuzz.ratio(word.lower(), self.keyword.lower())
                if similarity_reset > 80:
                    return text[text.lower().find(word):].strip()

        except sr.UnknownValueError:
            print("Error de reconocimiento de voz: Valor desconocido")
        except Exception as e:
            print(f"Error de reconocimiento de voz: {e}")
        return None

    def listen_for_command(self):
        with sr.Microphone(sample_rate=16000) as source:
            self.recognizer.adjust_for_ambient_noise(source)
            self.playsound('sounds/start_sound.mp3')
            print("Grabación iniciada.")
            recorded_audio = AudioSegment.empty()
            start_time = time.time()
            max_recording_time = 60  # Máximo 1 minuto
            frame_duration_ms = 30  # Duración de cada frame en milisegundos
            sample_rate = 16000  # Tasa de muestreo para VAD
            self.psilencio = False

            while time.time() - start_time < max_recording_time:
                try:
                    # Capturar audio
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=None)
                    audio_data = audio.get_raw_data(convert_rate=sample_rate, convert_width=2)
                    frames = self.frame_generator(frame_duration_ms, audio_data, sample_rate)
                    segments = self.vad_collector(sample_rate, frame_duration_ms, frames)

                    # Reconstruir el audio a partir de los segmentos de voz
                    for segment in segments:
                        audio_segment = AudioSegment(
                            data=segment,
                            sample_width=2,
                            frame_rate=sample_rate,
                            channels=1
                        )
                        recorded_audio += audio_segment

                    # Si no se detectó voz, continuar escuchando
                    if len(recorded_audio) == 0:
                        print("Silencio detectado, continuando grabación.")
                        self.psilencio = True
                        continue
                    else:
                        print(f"Duración total grabada: {len(recorded_audio)} ms")
                        break  # Salir después de obtener el comando

                except sr.WaitTimeoutError:
                    print("Tiempo de espera agotado durante la grabación del comando.")
                    break

            # Implementación de la lógica para detectar silencio
            detect_silence = True  # Asumir que hay silencio por defecto
            if len(recorded_audio) > 0:
                # Configurar el umbral de silencio
                silence_thresh = recorded_audio.dBFS - 16
                # Detectar rangos no silenciosos
                nonsilent_ranges = detect_nonsilent(recorded_audio, min_silence_len=500, silence_thresh=silence_thresh)
                print(f"Rangos no silenciosos detectados: {nonsilent_ranges}")

                if nonsilent_ranges:
                    # Calcular la duración total no silenciosa
                    total_nonsilent_duration = sum((end - start) for start, end in nonsilent_ranges)
                    total_duration = len(recorded_audio)
                    nonsilent_proportion = total_nonsilent_duration / total_duration
                    print(f"Proporción de audio no silencioso: {nonsilent_proportion * 100:.2f}%")

                    # Definir un umbral de proporción para considerar que hay voz
                    if nonsilent_proportion > 0.3:  # Por ejemplo, más del 30% del audio es no silencioso
                        detect_silence = False
                    else:
                        print("Proporción de audio no suficientemente alta para considerar que hay voz.")
                else:
                    print("No se detectaron rangos no silenciosos.")

            else:
                print("No se grabó ningún audio.")

            if not detect_silence:
                try:
                    if GROQ_API_KEY is not None and GROQ_API_KEY !="":
                        print("Usando reconocimiento de voz de Groq.")
                        text = self.transcribe_with_groq(recorded_audio)
                        return text
                    else:
                        print("Usando reconocimiento de voz de Google.")
                        text = self.recognizer.recognize_google(recorded_audio, language=self.language)
                except Exception as e:
                    print("Error al transcribir el audio:", e)
            else:
                print("No se detectó comando de voz.")
                self.playsound('sounds/stop_sound.mp3')  # Opcional: notificar al usuario

    def frame_generator(self, frame_duration_ms, audio, sample_rate):
        """Genera frames de audio de la duración especificada."""
        frame_size = int(sample_rate * (frame_duration_ms / 1000.0) * 2)  # 2 bytes por muestra (16 bits)
        offset = 0
        while offset + frame_size <= len(audio):
            yield audio[offset:offset + frame_size]
            offset += frame_size

    def vad_collector(self, sample_rate, frame_duration_ms, frames):
        """Recoge frames de voz utilizando VAD y devuelve segmentos de voz."""
        padding_duration_ms = 400  # Duración del padding en milisegundos
        num_padding_frames = int(padding_duration_ms / frame_duration_ms)
        ring_buffer = collections.deque(maxlen=num_padding_frames)
        triggered = False
        voiced_frames = []

        for frame in frames:
            is_speech = self.vad.is_speech(frame, sample_rate)
            print(f"VAD decision for frame: {'Speech' if is_speech else 'Silence'}")  # Información de depuración

            if not triggered:
                ring_buffer.append((frame, is_speech))
                num_voiced = len([f for f, speech in ring_buffer if speech])
                if num_voiced > 0.9 * ring_buffer.maxlen:
                    triggered = True
                    print("Inicio de voz detectado")
                    for f, s in ring_buffer:
                        voiced_frames.append(f)
                    ring_buffer.clear()
            else:
                voiced_frames.append(frame)
                ring_buffer.append((frame, is_speech))
                num_unvoiced = len([f for f, speech in ring_buffer if not speech])
                if num_unvoiced > ring_buffer.maxlen:
                    triggered = False
                    print("Fin de voz detectado")
                    yield b''.join(voiced_frames)
                    ring_buffer.clear()
                    voiced_frames = []

        if voiced_frames:
            yield b''.join(voiced_frames)

    def transcribe_with_groq(self, audio_segment):
        """Transcribe el audio utilizando el servicio de Groq."""
        # Exportar AudioSegment a un archivo temporal
        temp_file = "temp_audio.wav"
        audio_segment.export(temp_file, format="wav")

        # Leer el archivo temporal
        with open(temp_file, "rb") as file:
            files = {
                'file': ('temp_audio.wav', file, 'audio/wav')
            }
            data = {
                'model': 'whisper-large-v3-turbo',
                'temperature': '0',
                'response_format': 'json',
                'language': 'es'
            }
            headers = {
                'Authorization': f'Bearer {GROQ_API_KEY}'
            }
            response = requests.post(
                'https://api.groq.com/openai/v1/audio/transcriptions',
                headers=headers,
                files=files,
                data=data
            )
            if response.status_code == 200:
                transcription = response.json()
                print(f"Transcripción: {transcription['text']}")
                return transcription['text']
            else:
                print(f"Error al transcribir el audio: {response.status_code}")
                print(f"Respuesta: {response.text}")
                raise Exception(f"Error al transcribir el audio: {response.status_code}")

    def transcribe(self):
        """Método principal para iniciar la transcripción."""
        while True:
            text_after_keyword = self.listen_for_keyword()

            if text_after_keyword is not None:

                command = self.listen_for_command()
                if command:
                    print(f"Comando recibido: {command}")
                    data = {"text": command}
                else:
                    self.playsound('sounds/stop_sound.mp3')
                    continue
                self.playsound('sounds/stop_sound.mp3')
                # Enviar el mensaje al servidor a través del WebSocket
                self.send_message_to_server(data)
                # Esperar una respuesta (opcional)
                # Aquí puedes implementar lógica para esperar y procesar la respuesta del servidor

    def send_message_to_server(self, data):
        """Envía un mensaje al servidor a través del WebSocket."""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            try:
                payload = {
                    "API_KEY": self.api_key,
                    "action": "process_text",
                    "text": data["text"]
                }
                self.ws.send(json.dumps(payload))
                print(f"Mensaje enviado al servidor: {data['text']}")
            except Exception as e:
                print(f"Error al enviar mensaje al servidor: {e}")
        else:
            print("No hay conexión WebSocket con el servidor. El mensaje no se pudo enviar.")

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

    def on_server_message(self, ws, message):
        # Manejar mensajes entrantes del servidor si es necesario
        print(f"Mensaje recibido del servidor: {message}")

    def on_server_error(self, ws, error):
        print(f"Error en WebSocket con el servidor: {error}")

    def on_server_close(self, ws, close_status_code, close_msg):
        print("Conexión WebSocket con el servidor cerrada")

if __name__ == '__main__':
    transcriber = Transcriber()
    transcriber.transcribe()
