import os
import pyaudio
import queue
import threading
import tkinter as tk
from google.cloud import speech
from google.cloud import translate_v2 as translate  # Importamos Google Cloud Translation

# Configura tus credenciales de Google Cloud
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "api.json"

# Configura el cliente de Google Cloud Speech-to-Text y Translation
speech_client = speech.SpeechClient()
translate_client = translate.Client()

# Parámetros de audio
RATE = 16000  # Frecuencia de muestreo
CHUNK = int(RATE / 10)  # 100ms por chunk

# Events
stop_event = threading.Event()

# Cola para audio
audio_queue = queue.Queue()

# Asegurarse de que tkinter solo se actualice desde el hilo principal
def update_ui_from_thread_safe(text):
    root.after(0, lambda: label.config(text=text))

# Función para capturar el audio del micrófono
def record_audio():
    print("record")
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

# Función de streaming para la API
def stream_generator():
    print("stream")
    while not stop_event.is_set():
        chunk = audio_queue.get()
        if chunk is None:
            return
        yield speech.StreamingRecognizeRequest(audio_content=chunk)

# Función para traducir el texto
def translate_text(text, target_language="es"):
    result = translate_client.translate(text, target_language=target_language)
    return result["translatedText"]

# Función para procesar y mostrar la transcripción
def listen_print_loop(responses, text_widget):
    print("listen_loop")
    for response in responses:
        
        if stop_event.is_set():
            break
        if not response.results:
            continue

        result = response.results[0]
        if not result.alternatives:
            continue

        transcript = result.alternatives[0].transcript
        print(f"Transcript: {transcript}")

        # Traducir el texto transcrito al español (o cualquier idioma que desees)
        translation = translate_text(transcript, target_language="es")
        print(f"Translation: {translation}")

        # Actualizar el texto en el hilo principal usando after para transcripción
        text_widget.after(0, text_widget.delete, 1.0, tk.END)
        text_widget.after(0, text_widget.insert, tk.END, f"Transcripción: {transcript}\n")
        
        # Mostrar traducción justo debajo de la transcripción
        text_widget.after(0, text_widget.insert, tk.END, f"Traducción: {translation}\n")

# Configuración de la interfaz gráfica (UI) con Tkinter
def setup_ui():
    global root
    root = tk.Tk()
    root.title("Transcripción y Traducción en Tiempo Real")

    # Crear un widget de texto para mostrar la transcripción y la traducción
    text_widget = tk.Text(root, height=20, width=50)
    text_widget.pack()

    # Iniciar el reconocimiento de voz cuando la UI esté lista
    threading.Thread(target=start_recognition, args=(text_widget,)).start()

    root.protocol("WM_DELETE_WINDOW", stop_recognition)  # Para detener al cerrar la ventana
    root.mainloop()

# Función para iniciar el reconocimiento de voz
def start_recognition(text_widget):
    stop_event.clear()

    # Iniciar el hilo de grabación de audio
    threading.Thread(target=record_audio).start()

    # Configuración de reconocimiento de voz
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="en-US",
    )
    streaming_config = speech.StreamingRecognitionConfig(
        config=config, interim_results=True
    )

    # Iniciar el streaming de reconocimiento
    with speech_client.streaming_recognize(streaming_config, stream_generator()) as responses:
        listen_print_loop(responses, text_widget)

# Función para detener la grabación
def stop_recognition():
    stop_event.set()
    audio_queue.put(None)

# Iniciar la UI
if __name__ == "__main__":
    setup_ui()
