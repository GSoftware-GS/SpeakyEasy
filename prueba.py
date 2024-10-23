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

# Para Windows (PyAudio)
if platform.system() == "Windows":
    import pyaudio

# Configura tus credenciales de Google Cloud
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

# Función para grabar audio
def record_audio():
    system = platform.system()
    
    if system == "Windows":
        # Uso de PyAudio en Windows
        print("Recording audio in Windows...")
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        while not stop_event.is_set():
            data = stream.read(CHUNK)
            audio_queue.put(data)

        stream.stop_stream()
        stream.close()
        audio.terminate()

    elif system == "Linux" or system == "Android":
        # Grabar audio en Android (y Linux si fuera necesario)
        print("Recording audio in Android...")
        # Aquí deberás usar la herramienta nativa del sistema, como Kivy SoundRecorder o FFmpeg
        # Ejemplo con FFmpeg o un grabador de Android:
        # Implementación personalizada para grabar el audio.
        pass

# Función para transcribir y traducir el audio
def listen_print_loop(responses, label):
    global transcription_history, translated_history
    
    for response in responses:
        if not response.results:
            continue

        result = response.results[0]
        if not result.alternatives:
            continue

        transcript = result.alternatives[0].transcript
        is_final = result.is_final

        # Realizar la traducción provisional
        translation = translate_client.translate(transcript, target_language=target_language)
        translated_text = translation['translatedText']

        if is_final:
            transcription_history += transcript + "\n"
            translated_history += translated_text + "\n"

            # Actualizar la UI con la transcripción final
            update_ui(f"Transcripción: {transcription_history}\nTraducción: {translated_history}", label)
        else:
            # Actualizar la UI con la transcripción y traducción en progreso
            update_ui(f"Transcripción en progreso: {transcript}\nTraducción en progreso: {translated_text}", label)

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
    #contener texto dentro del tamaño de ventana
        
        self.label = Label(text="Esperando audio...", font_size='15sp', size_hint=(1, 0.1))
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
