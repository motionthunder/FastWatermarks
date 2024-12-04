import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess
from pathlib import Path

class WatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Наложение водяных знаков")
        self.root.geometry("800x600")
        
        # Создаем основной контейнер
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Инициализация путей
        self.watermark_path = tk.StringVar()
        self.images_folder = tk.StringVar()
        self.output_path = tk.StringVar()
        
        # Настройка интерфейса
        self.setup_widgets(main_frame)
        
    def setup_widgets(self, frame):
        # Секция выбора водяного знака
        watermark_frame = ttk.LabelFrame(frame, text="Водяной знак (PNG с прозрачностью)", padding="5")
        watermark_frame.grid(row=0, column=0, columnspan=2, pady=5, sticky="ew")
        
        self.watermark_entry = ttk.Entry(watermark_frame, textvariable=self.watermark_path, width=60)
        self.watermark_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(watermark_frame, text="Выбрать", 
                  command=self.select_watermark).pack(side=tk.LEFT, padx=5)
        
        # Секция выбора папки с изображениями
        images_frame = ttk.LabelFrame(frame, text="Папка с изображениями", padding="5")
        images_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")
        
        self.images_entry = ttk.Entry(images_frame, textvariable=self.images_folder, width=60)
        self.images_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(images_frame, text="Выбрать", 
                  command=self.select_images_folder).pack(side=tk.LEFT, padx=5)
        
        # Опции наложения
        options_frame = ttk.LabelFrame(frame, text="Настройки", padding="5")
        options_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        
        # Позиция водяного знака
        position_frame = ttk.Frame(options_frame)
        position_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(position_frame, text="Позиция:").pack(side=tk.LEFT, padx=5)
        self.position_var = tk.StringVar(value="center")
        position_combo = ttk.Combobox(position_frame, textvariable=self.position_var, 
                                    values=["top-left", "top-right", "bottom-left", "bottom-right", "center"])
        position_combo.pack(side=tk.LEFT, padx=5)
        
        # Прозрачность
        opacity_frame = ttk.Frame(options_frame)
        opacity_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(opacity_frame, text="Прозрачность:").pack(side=tk.LEFT, padx=5)
        self.opacity_var = tk.StringVar(value="0.5")
        opacity_spin = ttk.Spinbox(opacity_frame, from_=0.1, to=1.0, increment=0.1,
                                 textvariable=self.opacity_var, width=5)
        opacity_spin.pack(side=tk.LEFT, padx=5)
        
        # Размер водяного знака (в процентах от оригинального изображения)
        scale_frame = ttk.Frame(options_frame)
        scale_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(scale_frame, text="Размер (%):").pack(side=tk.LEFT, padx=5)
        self.scale_var = tk.StringVar(value="30")
        scale_spin = ttk.Spinbox(scale_frame, from_=1, to=100, increment=1,
                               textvariable=self.scale_var, width=5)
        scale_spin.pack(side=tk.LEFT, padx=5)

        # Тайлинг
        tile_frame = ttk.Frame(options_frame)
        tile_frame.pack(fill=tk.X, pady=5)
        
        self.tile_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tile_frame, text="Включить тайлинг", 
                       variable=self.tile_var).pack(side=tk.LEFT, padx=5)
        
        # Выходная папка
        output_frame = ttk.LabelFrame(frame, text="Папка для сохранения", padding="5")
        output_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
        
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_path, width=60)
        self.output_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(output_frame, text="Выбрать", 
                  command=self.select_output_folder).pack(side=tk.LEFT, padx=5)
        
        # Прогресс
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(frame, length=300, mode='determinate', 
                                      variable=self.progress_var)
        self.progress.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        
        # Статус
        self.status_var = tk.StringVar(value="Готово к работе")
        ttk.Label(frame, textvariable=self.status_var).grid(row=5, column=0, 
                                                           columnspan=2, pady=5)
        
        # Кнопки действий
        actions_frame = ttk.Frame(frame)
        actions_frame.grid(row=6, column=0, columnspan=2, pady=10)
        
        ttk.Button(actions_frame, text="Начать обработку", 
                  command=self.process_images).pack(side=tk.LEFT, padx=5)
        
    def select_watermark(self):
        filename = filedialog.askopenfilename(
            title="Выберите водяной знак",
            filetypes=[("PNG files", "*.png")]
        )
        if filename:
            self.watermark_path.set(filename)
    
    def select_images_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с изображениями")
        if folder:
            self.images_folder.set(folder)
            # Автоматически установим выходную папку
            self.output_path.set(os.path.join(folder, "watermarked"))
    
    def select_output_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку для сохранения")
        if folder:
            self.output_path.set(folder)
    
    def get_image_dimensions(self, image_path):
        """Получает размеры изображения с помощью ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=s=x:p=0',
                image_path
            ]
            dimensions = subprocess.check_output(cmd).decode().strip().split('x')
            return map(int, dimensions)
        except:
            return None, None

    def process_images(self):
        if not self.validate_inputs():
            return
        
        watermark = self.watermark_path.get()
        input_folder = self.images_folder.get()
        output_folder = self.output_path.get()
        opacity = float(self.opacity_var.get())
        
        # Создаем выходную папку, если её нет
        os.makedirs(output_folder, exist_ok=True)
        
        # Получаем список всех изображений
        image_files = [f for f in os.listdir(input_folder) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not image_files:
            messagebox.showwarning("Предупреждение", "В выбранной папке нет изображений!")
            return
        
        # Настраиваем прогресс бар
        self.progress_var.set(0)
        total_files = len(image_files)
        
        for i, image_file in enumerate(image_files):
            input_path = os.path.join(input_folder, image_file)
            output_path = os.path.join(output_folder, f"watermarked_{image_file}")
            
            try:
                # Получаем размеры входного изображения
                input_width, input_height = self.get_image_dimensions(input_path)
                if not input_width or not input_height:
                    raise Exception("Не удалось получить размеры изображения")

                # Формируем команду ffmpeg
                scale = f"scale=iw*{float(self.scale_var.get())/100}:-1"
                
                if self.tile_var.get():
                    # Создаем тайлинг с перекрытием
                    filter_complex = [
                        f'[1:v]{scale}[watermark];',
                        f'[watermark]format=rgba,colorchannelmixer=aa={opacity}[watermark1];',
                        f'[watermark1]tile=layout=2x2:overlap=1[tiled_watermark];',
                        f'[0:v][tiled_watermark]overlay=0:0'
                    ]
                else:
                    # Обычное наложение водяного знака
                    position = "0:0"
                    filter_complex = [
                        f'[1:v]{scale}[watermark];',
                        f'[watermark]format=rgba,colorchannelmixer=aa={opacity}[watermark1];',
                        f'[0:v][watermark1]overlay={position}'
                    ]
                
                command = [
                    'ffmpeg',
                    '-i', input_path,
                    '-i', watermark,
                    '-filter_complex', ''.join(filter_complex),
                    '-y',
                    output_path
                ]
                
                # Выполняем команду
                self.status_var.set(f"Обработка {image_file}...")
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    raise Exception(f"FFmpeg error: {stderr.decode()}")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при обработке {image_file}: {str(e)}")
                continue
            
            # Обновляем прогресс
            self.progress_var.set((i + 1) / total_files * 100)
            self.root.update()
        
        self.status_var.set("Обработка завершена!")
        messagebox.showinfo("Успех", "Все изображения обработаны!")
    
    def validate_inputs(self):
        if not self.watermark_path.get():
            messagebox.showwarning("Предупреждение", "Выберите водяной знак!")
            return False
        
        if not self.images_folder.get():
            messagebox.showwarning("Предупреждение", "Выберите папку с изображениями!")
            return False
        
        if not self.output_path.get():
            messagebox.showwarning("Предупреждение", "Выберите папку для сохранения!")
            return False
        
        try:
            opacity = float(self.opacity_var.get())
            if not 0 <= opacity <= 1:
                raise ValueError
            scale = float(self.scale_var.get())
            if not 0 < scale <= 100:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Предупреждение", "Некорректные значения прозрачности или размера!")
            return False
        
        return True

def main():
    root = tk.Tk()
    app = WatermarkApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()