
import os
import platform
import queue
import threading
from google.cloud import speech
from google.cloud import translate_v2 as translate
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.clock import Clock
from plyer import audio  # Usar Plyer para Android

# Configura tus credenciales de Google Cloud (esto puede requerir ajustes para Android)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "api.json"

# Configura el cliente de Google Cloud Speech-to-Text y Translation
speech_client = speech.SpeechClient()
translate_client = translate.Client()

# Parámetros de audio
RATE = 16000  # Frecuencia de muestreo
CHUNK = int(RATE / 10)  # 100ms por chunk

# Idiomas
source_language = "es"  # Idioma para la transcripción
target_language = "en-US"  # Idioma para la traducción

transcription_history = ""
translated_history = ""

# Cola para audio
audio_queue = queue.Queue()

# Event para detener la grabación
stop_event = threading.Event()

# Función para actualizar la etiqueta
def update_label(label, text):
    label.text = text

# Función para actualizar la UI desde el hilo principal
def update_ui(text, label):
    Clock.schedule_once(lambda dt: update_label(label, text))

# Función para grabar audio usando Plyer en Android
def record_audio():
    audio.start()
    while not stop_event.is_set():
        data = audio.read(CHUNK)
        audio_queue.put(data)

    audio.stop()

# Función para mostrar transcripción y traducción en la interfaz
def listen_print_loop(responses, label):
    global transcription_history, translated_history

    for response in responses:
        if not response.results:
            continue

        result = response.results[0]
        transcript = result.alternatives[0].transcript

        if result.is_final:
            # Transcripción final
            transcription_history += transcript + "\n"

            # Traducción
            translation = translate_client.translate(transcript, target_language=target_language)
            translated_text = translation['translatedText']
            translated_history += translated_text + "\n"

            # Actualizar la UI con el resultado
            update_ui(f"Transcripción final: {transcript}\nTraducción final: {translated_text}", label)

        else:
            # Actualizar la UI con la transcripción y traducción en progreso
            update_ui(f"Transcripción en progreso: {transcript}\nTraducción en progreso: (traduciendo...)", label)

# Función principal de reconocimiento de audio
def recognize_streaming(label):
    audio_generator = (audio_queue.get() for _ in iter(int, 1))

    requests = (speech.StreamingRecognizeRequest(audio_content=content) for content in audio_generator)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=source_language,
    )

    streaming_config = speech.StreamingRecognitionConfig(config=config, interim_results=True)

    responses = speech_client.streaming_recognize(config=streaming_config, requests=requests)

    # Escuchar y mostrar los resultados de la transcripción y traducción en tiempo real
    listen_print_loop(responses, label)

# Aplicación Kivy
class AudioTranscriptionApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical')

        self.label = Label(text="Esperando audio...", font_size='20sp')
        layout.add_widget(self.label)

        start_button = Button(text="Comenzar Grabación", font_size='20sp', on_press=self.start_recognition)
        layout.add_widget(start_button)

        stop_button = Button(text="Detener Grabación", font_size='20sp', on_press=self.stop_recognition)
        layout.add_widget(stop_button)

        return layout

    def start_recognition(self, instance):
        # Hilo de captura de audio
        audio_thread = threading.Thread(target=record_audio)
        audio_thread.start()

        # Hilo de transcripción
        recognition_thread = threading.Thread(target=recognize_streaming, args=(self.label,))
        recognition_thread.start()

    def stop_recognition(self, instance):
        stop_event.set()

# Ejecutar la app
if __name__ == "__main__":
    AudioTranscriptionApp().run()
