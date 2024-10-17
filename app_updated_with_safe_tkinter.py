import os
import pyaudio
import queue
import threading
import tkinter as tk
from google.cloud import speech

# Configura tus credenciales de Google Cloud
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "api.json"

# Configura el cliente de Google Cloud Speech-to-Text
client = speech.SpeechClient()

# Parámetros de audio
RATE = 16000  # Frecuencia de muestreo
CHUNK = int(RATE / 10)  # 100ms por chunk

#Events
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


# Función para procesar y mostrar la transcripción
def listen_print_loop(responses, text_widget):
    print("listen_loop")
    for response in responses:
        print(f"Response: {response}")
        if stop_event.is_set():
            break
        if not response.results:
            continue

        result = response.results[0]
        if not result.alternatives:
            continue

        transcript = result.alternatives[0].transcript

        # Actualizar el texto en el hilo principal usando after
        text_widget.after(0, text_widget.delete, 1.0, tk.END)
        text_widget.after(0, text_widget.insert, tk.END, transcript)

        # Si es el resultado final, agregar una nueva línea en el hilo principal
        if result.is_final:
            text_widget.after(0, text_widget.insert, tk.END, "\n")
            break


# Interfaz de usuario con tkinter
def create_gui():
    root = tk.Tk()
    root.title("Transcripción en tiempo real")

    # Mejorando la apariencia del widget de texto
    text_widget = tk.Text(
        root, height=20, width=80, font=("Helvetica", 14), bg="#f0f0f0", fg="#333333"
    )
    text_widget.pack(padx=10, pady=10)

    # Iniciar transcripción en un hilo separado
    threading.Thread(target=transcribe_streaming, args=(text_widget,)).start()
    root.mainloop()


# Función principal para iniciar la transcripción en tiempo real
def transcribe_streaming(text_widget):
    print("transcribe_streaming")
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="es-ES",
        enable_automatic_punctuation=True,
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config, interim_results=True
    )

    # Corrección: Eliminar el 'with' y usar directamente el iterador de respuestas
    responses = client.streaming_recognize(streaming_config, stream_generator())
    listen_print_loop(responses, text_widget)


if __name__ == "__main__":
    threading.Thread(target=record_audio).start()
    create_gui()
    stop_event.set()
    print("stop")
    