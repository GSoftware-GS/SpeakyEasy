#V2.0 With GUI

import os
import pyaudio
import queue
import threading
import tkinter as tk
from tkinter import ttk
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
target_language = "en"  # Idioma para la traducción

transcription_history = ""
translated_history = ""

# Events
stop_event = threading.Event()

# Cola para audio
audio_queue = queue.Queue()

# Función para actualizar la etiqueta de traducción en el hilo principal de Tkinter
def update_translation_label(text):
    root.after(0, lambda: translation_label.config(text=text))

# Función para actualizar la etiqueta de transcripción en el hilo principal de Tkinter
def update_transcription_label(text):
    root.after(0, lambda: transcription_label.config(text=text))

# Función para capturar el audio del micrófono
def record_audio():
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
            # Añadir al historial si es una transcripción final
            transcription_history += transcript + "\n"
            translated_history += translated_text + "\n"

            # Actualizar las etiquetas con las transcripciones y traducciones finales
            update_transcription_label(transcription_history)
            update_translation_label(translated_history)
        else:
            # Actualizar las etiquetas con las transcripciones y traducciones provisionales
            update_transcription_label(transcript)
            update_translation_label(translated_text)

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
root.title("Transcripción y Traducción en Tiempo Real")
root.geometry("700x450")
root.configure(bg="#2E2E2E")

# Añadir estilo a la aplicación
style = ttk.Style()
style.configure("TLabel", font=("Verdana", 12), padding=10, background="#2E2E2E", foreground="#FFFFFF")
style.configure("Title.TLabel", font=("Verdana", 18, "bold"), background="#2E2E2E", foreground="#FFC300")
style.configure("Subtitle.TLabel", font=("Verdana", 10), background="#2E2E2E", foreground="#A4A4A4")

# Título de la aplicación
title_label = ttk.Label(root, text="Transcripción y Traducción en Tiempo Real", style="Title.TLabel")
title_label.pack(pady=20)

# Subtítulos elegantes
subtitle_transcription = ttk.Label(root, text="Transcripción en Español", style="Subtitle.TLabel")
subtitle_transcription.pack()

# Etiquetas para la transcripción
transcription_label = ttk.Label(root, text="Esperando audio...", style="TLabel", wraplength=600, anchor="center")
transcription_label.pack(pady=10, fill='x')

# Subtítulo para la traducción
subtitle_translation = ttk.Label(root, text="Traducción al Inglés", style="Subtitle.TLabel")
subtitle_translation.pack()

# Etiqueta para la traducción
translation_label = ttk.Label(root, text="Esperando audio...", style="TLabel", wraplength=600, anchor="center")
translation_label.pack(pady=10, fill='x')

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
