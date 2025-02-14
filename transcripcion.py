
import tkinter as tk
from tkinter import ttk, font
import speech_recognition as sr
import pyaudio
import threading
import sounddevice as sd


class TranscriptorOverlay:
    def __init__(self):
        # Inicializar el reconocedor de voz
        self.recognizer = sr.Recognizer()

        # Obtener lista de dispositivos de audio
        self.dispositivos_audio = sd.query_devices()

        # Configuración inicial
        self.recording = False
        self.texto_actual = ""

        # Crear ventana principal
        self.root = tk.Tk()
        self.root.title("Configuración Transcriptor")

        # Crear interfaz de configuración
        self.crear_interfaz_config()

        # Crear ventana overlay (inicialmente oculta)
        self.overlay = None

        # Variables para redimensionamiento
        self.resizing = False

    def crear_interfaz_config(self):
        # Frame principal
        frame = ttk.Frame(self.root, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Selector de dispositivo de entrada
        ttk.Label(frame, text="Dispositivo de entrada:").grid(
            row=0, column=0, pady=5)
        self.dispositivo_var = tk.StringVar()
        dispositivos = ttk.Combobox(frame, textvariable=self.dispositivo_var)
        dispositivos['values'] = [str(i) + ": " + d['name']
                                  for i, d in enumerate(self.dispositivos_audio)]
        dispositivos.grid(row=0, column=1, pady=5)
        dispositivos.current(0)

        # Selector de fuente
        ttk.Label(frame, text="Fuente:").grid(row=1, column=0, pady=5)
        self.fuente_var = tk.StringVar(value="Arial")
        fuentes = ttk.Combobox(frame, textvariable=self.fuente_var)
        fuentes['values'] = list(font.families())
        fuentes.grid(row=1, column=1, pady=5)

        # Selector de tamaño de fuente
        ttk.Label(frame, text="Tamaño de fuente:").grid(
            row=2, column=0, pady=5)
        self.tamano_var = tk.StringVar(value="24")
        tamano = ttk.Entry(frame, textvariable=self.tamano_var)
        tamano.grid(row=2, column=1, pady=5)

        # Botón de inicio/parada
        self.btn_inicio = ttk.Button(
            frame, text="Iniciar Transcripción", command=self.toggle_transcripcion)
        self.btn_inicio.grid(row=3, column=0, columnspan=2, pady=10)

    def crear_overlay(self):
        self.overlay = tk.Toplevel(self.root)
        self.overlay.title("Transcripción")

        # Configurar ventana transparente
        self.overlay.attributes('-alpha', 0.7)  # Transparencia
        self.overlay.attributes('-topmost', True)  # Siempre visible
        self.overlay.overrideredirect(True)  # Sin decoración de ventana

        # Frame principal para el contenido
        self.frame_contenido = tk.Frame(self.overlay, bg='black')
        self.frame_contenido.pack(expand=True, fill='both')

        # Etiqueta para el texto
        self.label_texto = tk.Label(
            self.frame_contenido,
            text="",
            font=(self.fuente_var.get(), int(self.tamano_var.get())),
            bg='black',
            fg='white',
            wraplength=800
        )
        self.label_texto.pack(expand=True, fill='both', padx=10, pady=10)

        # Marco de redimensionamiento
        self.resize_frame = tk.Frame(
            self.frame_contenido, bg='white', width=10, height=10)
        self.resize_frame.place(relx=1.0, rely=1.0, anchor='se')

        # Bindings para mover y redimensionar
        self.label_texto.bind('<Button-1>', self.iniciar_movimiento)
        self.label_texto.bind('<B1-Motion>', self.mover_ventana)
        self.resize_frame.bind('<Button-1>', self.iniciar_redimension)
        self.resize_frame.bind('<B1-Motion>', self.redimensionar)

        # Cursor personalizado para la esquina de redimensionamiento
        self.resize_frame.bind(
            '<Enter>', lambda e: self.resize_frame.configure(cursor='sizing'))
        self.resize_frame.bind(
            '<Leave>', lambda e: self.resize_frame.configure(cursor=''))

        # Posicionar ventana
        self.overlay.geometry('800x200+100+100')

    def iniciar_movimiento(self, event):
        self.x = event.x
        self.y = event.y

    def mover_ventana(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.overlay.winfo_x() + deltax
        y = self.overlay.winfo_y() + deltay
        self.overlay.geometry(f"+{x}+{y}")

    def iniciar_redimension(self, event):
        self.resizing = True
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.start_width = self.overlay.winfo_width()
        self.start_height = self.overlay.winfo_height()

    def redimensionar(self, event):
        if self.resizing:
            # Calcular nuevo tamaño
            new_width = self.start_width + (event.x_root - self.start_x)
            new_height = self.start_height + (event.y_root - self.start_y)

            # Establecer tamaño mínimo
            new_width = max(200, new_width)
            new_height = max(100, new_height)

            # Actualizar el wraplength del texto
            self.label_texto.configure(wraplength=new_width - 20)

            # Aplicar nuevo tamaño
            self.overlay.geometry(f"{new_width}x{new_height}")

    def toggle_transcripcion(self):
        if not self.recording:
            # Iniciar transcripción
            self.recording = True
            self.btn_inicio.configure(text="Detener Transcripción")

            if not self.overlay:
                self.crear_overlay()
            else:
                self.overlay.deiconify()

            # Iniciar thread de reconocimiento
            self.thread = threading.Thread(target=self.transcribir_audio)
            self.thread.daemon = True
            self.thread.start()
        else:
            # Detener transcripción
            self.recording = False
            self.btn_inicio.configure(text="Iniciar Transcripción")
            if self.overlay:
                self.overlay.withdraw()

    def transcribir_audio(self):
        while self.recording:
            try:
                # Configurar el micrófono seleccionado
                with sr.Microphone(
                    device_index=int(self.dispositivo_var.get().split(':')[0])
                ) as source:

                    print("Escuchando...")
                    self.recognizer.adjust_for_ambient_noise(source)
                    audio = self.recognizer.listen(source)

                    # Intentar reconocer el audio
                    texto = self.recognizer.recognize_google(
                        audio, language="es-ES")

                    # Actualizar el texto en el overlay
                    self.texto_actual = texto
                    if self.overlay:
                        self.label_texto.configure(text=self.texto_actual)

            except sr.UnknownValueError:
                print("No se pudo entender el audio")
            except sr.RequestError as e:
                print(f"Error en el servicio de reconocimiento: {e}")

    def iniciar(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = TranscriptorOverlay()
    app.iniciar()
