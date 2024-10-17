import os
import pyaudio
import queue
import threading
import tkinter as tk
from google.cloud import speech

# Configura tus credenciales de Google Cloud
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'api.json'

# Configura el cliente de Google Cloud Speech-to-Text
client = speech.SpeechClient()

# Parámetros de audio
RATE = 16000  # Frecuencia de muestreo
CHUNK = int(RATE / 10)  # 100ms por chunk

# Cola para audio
audio_queue = queue.Queue()

# Función para capturar el audio del micrófono
def record_audio():
    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)
    
    while True:
        data = stream.read(CHUNK)
        audio_queue.put(data)

# Función de streaming para la API
def stream_generator():
    while True:
        chunk = audio_queue.get()
        if chunk is None:
            return
        yield speech.StreamingRecognizeRequest(audio_content=chunk)

# Función para procesar y mostrar la transcripción
def listen_print_loop(responses, text_widget):
    for response in responses:
        if not response.results:
            continue
        
        result = response.results[0]
        if not result.alternatives:
            continue

        transcript = result.alternatives[0].transcript

        # Mostrar el texto en la ventana
        text_widget.insert(tk.END, transcript + '\n')
        text_widget.see(tk.END)

        if result.is_final:
            break

# Interfaz de usuario con tkinter
def create_gui():
    root = tk.Tk()
    root.title("Transcripción en tiempo real")
    
    text_widget = tk.Text(root, height=20, width=80)
    text_widget.pack()
    
    threading.Thread(target=transcribe_streaming, args=(text_widget,)).start()
    
    root.mainloop()

# Función principal para iniciar la transcripción en tiempo real
def transcribe_streaming(text_widget):
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="es-ES",
    )
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,
    )
    
    # Inicia la captura de audio en un hilo separado
    threading.Thread(target=record_audio, daemon=True).start()
    
    # Envía las solicitudes de transcripción
    responses = client.streaming_recognize(streaming_config, stream_generator())

    # Procesa las respuestas
    listen_print_loop(responses, text_widget)

if __name__ == "__main__":
    create_gui()
