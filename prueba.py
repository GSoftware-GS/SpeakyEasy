
import os
import pyaudio
import queue
import threading
import tkinter as tk
from google.cloud import speech
from google.cloud import translate_v2 as translate

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
target_language = "en-US"     # Idioma para la traducción

transcription_history = ""
translated_history = ""

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

    stream.stop_stream()
    stream.close()
    audio.terminate()

# Función para transcribir el audio en tiempo real
def listen_print_loop(responses):
    global transcription_history, translated_history
    print("listen_loop")
    
    for response in responses:
        if not response.results:
            continue

        result = response.results[0]
        if not result.alternatives:
            continue

        # Transcripción obtenida
        transcript = result.alternatives[0].transcript
        is_final = result.is_final

        # Realizar la traducción provisional
        translation = translate_client.translate(transcript, target_language=target_language)
        translated_text = translation['translatedText']
        translated_text = translated_text.replace("&#39;", "'")

        if is_final:
            # Si la transcripción es final, añadirla al historial y la traducción también
            transcription_history += transcript + "\n"
            translated_history += translated_text + "\n"

            # Limpiar la consola y mostrar las transcripciones y traducciones finales
            os.system("cls")
            print(f"Transcripción (español):\n{transcription_history}")
            print(f"Traducción ({target_language}):\n{translated_history}")
        else:
            # Mostrar transcripción provisional y traducción provisional en tiempo real
            os.system("cls")
            print(f"Traducción ({target_language}):\n{translated_history}")
            print(f"Transcripción (en progreso): {transcript}")
            print(f"Traducción (en progreso): {translated_text}")
            
# Función principal de reconocimiento de audio
def recognize_streaming():
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
    listen_print_loop(responses)

# Crear ventana con Tkinter
root = tk.Tk()
root.title("Transcripción en tiempo real con traducción")
label = tk.Label(root, text="Esperando audio...", font=("Helvetica", 16))
label.pack(padx=10, pady=10)

# Hilo de captura de audio
audio_thread = threading.Thread(target=record_audio)
audio_thread.start()

# Hilo de transcripción
recognition_thread = threading.Thread(target=recognize_streaming)
recognition_thread.start()

# Iniciar la ventana de Tkinter
root.mainloop()

# Para detener la grabación y el reconocimiento
stop_event.set()
audio_thread.join()
recognition_thread.join()

