import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont
import tempfile
import sys
from pathlib import Path
import glob

# Добавляем ffmpeg в PATH
os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')

class FFmpegHandler:
    """Класс для работы с FFmpeg"""
    @staticmethod
    def check_ffmpeg():
        """Проверяет наличие ffmpeg в системе"""
        ffmpeg_path = '/opt/homebrew/bin/ffmpeg' if sys.platform == 'darwin' else 'ffmpeg'
        try:
            subprocess.run([ffmpeg_path, '-version'], capture_output=True, check=True)
            return True
        except:
            return False

    @staticmethod
    def get_dimensions(image_path):
        """Получает размеры изображения"""
        ffprobe_path = '/opt/homebrew/bin/ffprobe' if sys.platform == 'darwin' else 'ffprobe'
        try:
            cmd = [
                ffprobe_path,
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=s=x:p=0',
                image_path
            ]
            dimensions = subprocess.check_output(cmd).decode().strip().split('x')
            return tuple(map(int, dimensions))
        except Exception as e:
            print(f"Ошибка получения размеров: {e}")
            return None, None

    @staticmethod
    def apply_watermark(input_path, watermark_path, output_path, config):
        """Накладывает водяной знак на изображение"""
        ffmpeg_path = '/opt/homebrew/bin/ffmpeg' if sys.platform == 'darwin' else 'ffmpeg'
        try:
            # Получаем размеры входного изображения
            width, height = FFmpegHandler.get_dimensions(input_path)
            if not width or not height:
                raise Exception("Не удалось получить размеры изображения")

            # Определяем масштаб и создаем фильтр
            scale = min(width, height) * (0.15 if config['tile_enabled'] else 0.3)
            filter_complex = FFmpegHandler._create_filter_complex(
                scale, config['opacity'], config['tile_enabled'], config['density']
            )

            # Формируем команду
            command = [
                ffmpeg_path,
                '-i', input_path,
                '-i', watermark_path,
                '-filter_complex', filter_complex,
                '-y',
                output_path
            ]

            # Выполняем команду
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, stderr = process.communicate()

            if process.returncode != 0:
                raise Exception(f"FFmpeg error: {stderr.decode()}")
            
            return True

        except Exception as e:
            print(f"Ошибка обработки изображения: {e}")
            return False

    @staticmethod
    def _create_filter_complex(scale, opacity, tile_enabled, density):
        """Создает строку filter_complex для ffmpeg"""
        if tile_enabled:
            filter_parts = []
            filter_parts.append(f'[1:v]scale={scale}:-1[scaled]')
            filter_parts.append(f'[scaled]format=rgba,colorchannelmixer=aa={opacity}[watermark]')
            
            total_marks = density * density
            splits = [f'[watermark]split={total_marks}']
            splits.extend(f'[w{i}]' for i in range(total_marks))
            filter_parts.append(''.join(splits))
            
            current = '[0:v]'
            overlays = []
            for row in range(density):
                for col in range(density):
                    mark_idx = row * density + col
                    out_name = f'[v{mark_idx}]' if mark_idx < total_marks - 1 else ''
                    x_pos = f'(W-w)*{col}/{density-1}'
                    y_pos = f'(H-h)*{row}/{density-1}'
                    overlays.append(
                        f'{current}[w{mark_idx}]overlay={x_pos}:{y_pos}{out_name}'
                    )
                    current = out_name
            
            filter_parts.extend(overlays)
            return ';'.join(filter_parts)
        else:
            return (
                f'[1:v]scale={scale}:-1[watermark];'
                f'[watermark]format=rgba,colorchannelmixer=aa={opacity}[watermark_alpha];'
                '[0:v][watermark_alpha]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2'
            )

class WatermarkCreator:
    """Класс для создания водяного знака"""
    def __init__(self, text, font_path, font_size, color, angle):
        self.text = text
        self.font_path = font_path
        self.font_size = font_size
        self.color = color
        self.angle = angle
        self._temp_file = None

    def create(self):
        """Создает изображение водяного знака"""
        try:
            # Создаем базовое изображение
            img = Image.new('RGBA', (1024, 1024), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            # Загружаем шрифт
            try:
                font = ImageFont.truetype(self.font_path, self.font_size)
            except Exception as e:
                print(f"Ошибка загрузки шрифта: {e}")
                font = ImageFont.load_default()

            # Получаем размеры текста
            bbox = draw.textbbox((0, 0), self.text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Создаем изображение нужного размера
            img = Image.new('RGBA', (text_width + 50, text_height + 50), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            # Рисуем текст
            draw.text((25, 25), self.text, font=font, fill=self.color)

            # Поворачиваем если нужно
            if self.angle != 0:
                img = img.rotate(self.angle, expand=True, fillcolor=(255, 255, 255, 0))

            # Сохраняем во временный файл
            self._temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            img.save(self._temp_file.name, 'PNG')
            return self._temp_file.name

        except Exception as e:
            print(f"Ошибка создания водяного знака: {e}")
            return None

    def cleanup(self):
        """Удаляет временный файл"""
        if self._temp_file and os.path.exists(self._temp_file.name):
            try:
                os.unlink(self._temp_file.name)
            except Exception as e:
                print(f"Ошибка удаления временного файла: {e}")

class FontManager:
    """Класс для управления шрифтами"""
    DEFAULT_FONT = "Montserrat-Black"  # Устанавливаем шрифт по умолчанию здесь
    
    @staticmethod
    def get_system_fonts():
        """Получает список доступных системных шрифтов, с Montserrat Black в начале списка"""
        fonts = []
        if sys.platform == "darwin":
            font_dirs = [
                "/Library/Fonts",
                "/System/Library/Fonts",
                os.path.expanduser("~/Library/Fonts")
            ]
            for font_dir in font_dirs:
                if os.path.exists(font_dir):
                    fonts.extend([os.path.splitext(f)[0] for f in os.listdir(font_dir)
                                if f.endswith(('.ttf', '.ttc'))])
                    
        fonts = sorted(list(set(fonts)))  # Удаляем дубликаты и сортируем
        
        # Перемещаем Montserrat Black в начало списка, если он есть
        if FontManager.DEFAULT_FONT in fonts:
            fonts.remove(FontManager.DEFAULT_FONT)
            fonts.insert(0, FontManager.DEFAULT_FONT)
            
        return fonts

    @staticmethod
    def get_font_path(font_name):
        """Получает путь к файлу шрифта"""
        if sys.platform == "darwin":
            # Проверяем, запрашивается ли шрифт по умолчанию
            if font_name == FontManager.DEFAULT_FONT:
                montserrat_paths = [
                    "/Library/Fonts/Montserrat-Black.ttf",
                    os.path.expanduser("~/Library/Fonts/Montserrat-Black.ttf"),
                    os.path.expanduser("/System/Library/Fonts/Montserrat-Black.ttf")
                ]
                for path in montserrat_paths:
                    if os.path.exists(path):
                        return path
            
            # Поиск в стандартных директориях
            font_dirs = [
                "/Library/Fonts",
                "/System/Library/Fonts",
                os.path.expanduser("~/Library/Fonts")
            ]
            for font_dir in font_dirs:
                for ext in ['.ttf', '.ttc']:
                    path = os.path.join(font_dir, f"{font_name}{ext}")
                    if os.path.exists(path):
                        return path
            
            # Возвращаем путь к Helvetica как запасной вариант
            return "/System/Library/Fonts/Helvetica.ttc"

class WatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced Text Watermark Tool")
        self.root.geometry("800x800")
        
        # Проверяем наличие ffmpeg
        if not FFmpegHandler.check_ffmpeg():
            messagebox.showerror(
                "Ошибка",
                "FFmpeg не найден! Установите FFmpeg и добавьте его в PATH."
            )
            self.root.quit()
            return

        # Инициализация переменных
        self._init_variables()
        
        # Создаем интерфейс
        self._create_ui()

    def _init_variables(self):
        """Инициализация переменных"""
        self.images_folder = tk.StringVar()
        self.output_path = tk.StringVar()
        self.watermark_text = tk.StringVar(value="@lirahush")
        self.font_size = tk.StringVar(value="100")
        self.opacity = tk.StringVar(value="0.1")
        self.angle = tk.StringVar(value="45")
        self.color = tk.StringVar(value="#FFFFFF")
        self.tile_enabled = tk.BooleanVar(value=True)
        self.tile_density = tk.StringVar(value="8")
        
        # Инициализация шрифта
        self.selected_font = tk.StringVar(value=FontManager.DEFAULT_FONT)
        
        self.progress = tk.DoubleVar()
        self.status = tk.StringVar(value="Готов к работе")

        # Загружаем список шрифтов
        self.available_fonts = FontManager.get_system_fonts()

    def _create_ui(self):
        """Создание пользовательского интерфейса"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(sticky='nsew')

        # Создаем секции интерфейса
        self._create_watermark_section(main_frame)
        self._create_input_section(main_frame)
        self._create_settings_section(main_frame)
        self._create_output_section(main_frame)
        self._create_progress_section(main_frame)

    def _create_watermark_section(self, parent):
        """Создание секции водяного знака"""
        frame = ttk.LabelFrame(parent, text="Текст водяного знака", padding="5")
        frame.grid(sticky='ew', pady=5)
        
        ttk.Entry(frame, textvariable=self.watermark_text).pack(fill='x')

    def _create_input_section(self, parent):
        """Создание секции выбора входной папки"""
        frame = ttk.LabelFrame(parent, text="Папка с изображениями", padding="5")
        frame.grid(sticky='ew', pady=5)

        ttk.Entry(frame, textvariable=self.images_folder).pack(side='left', fill='x', expand=True)
        ttk.Button(frame, text="Выбрать", command=self._select_input_folder).pack(side='left', padx=5)

    def _create_settings_section(self, parent):
        """Создание секции настроек"""
        frame = ttk.LabelFrame(parent, text="Настройки", padding="5")
        frame.grid(sticky='ew', pady=5)

        # Шрифт
        font_frame = ttk.Frame(frame)
        font_frame.pack(fill='x', pady=2)
        ttk.Label(font_frame, text="Шрифт:").pack(side='left')
        ttk.Combobox(font_frame, textvariable=self.selected_font,
                    values=self.available_fonts).pack(side='left', fill='x', expand=True)

        # Размер шрифта
        size_frame = ttk.Frame(frame)
        size_frame.pack(fill='x', pady=2)
        ttk.Label(size_frame, text="Размер:").pack(side='left')
        ttk.Spinbox(size_frame, from_=12, to=200, textvariable=self.font_size).pack(side='left')

        # Прозрачность
        opacity_frame = ttk.Frame(frame)
        opacity_frame.pack(fill='x', pady=2)
        ttk.Label(opacity_frame, text="Прозрачность:").pack(side='left')
        ttk.Spinbox(opacity_frame, from_=0.1, to=1.0, increment=0.1,
                   textvariable=self.opacity).pack(side='left')

        # Угол наклона
        angle_frame = ttk.Frame(frame)
        angle_frame.pack(fill='x', pady=2)
        ttk.Label(angle_frame, text="Угол:").pack(side='left')
        ttk.Spinbox(angle_frame, from_=-180, to=180, textvariable=self.angle).pack(side='left')

        # Цвет
        color_frame = ttk.Frame(frame)
        color_frame.pack(fill='x', pady=2)
        ttk.Label(color_frame, text="Цвет (HEX):").pack(side='left')
        ttk.Entry(color_frame, textvariable=self.color, width=10).pack(side='left')

        # Тайлинг
        tile_frame = ttk.Frame(frame)
        tile_frame.pack(fill='x', pady=2)
        ttk.Checkbutton(tile_frame, text="Тайлинг", variable=self.tile_enabled).pack(side='left')
        ttk.Label(tile_frame, text="Плотность:").pack(side='left', padx=(10, 0))
        ttk.Spinbox(tile_frame, from_=2, to=10, textvariable=self.tile_density, width=5).pack(side='left')

    def _create_output_section(self, parent):
        """Создание секции выходной папки"""
        frame = ttk.LabelFrame(parent, text="Папка для сохранения", padding="5")
        frame.grid(sticky='ew', pady=5)

        ttk.Entry(frame, textvariable=self.output_path).pack(side='left', fill='x', expand=True)
        ttk.Button(frame, text="Выбрать", command=self._select_output_folder).pack(side='left', padx=5)

    def _create_progress_section(self, parent):
        """Создание секции прогресса"""
        frame = ttk.Frame(parent)
        frame.grid(sticky='ew', pady=5)

        ttk.Progressbar(frame, variable=self.progress, mode='determinate').pack(fill='x', pady=5)
        ttk.Label(frame, textvariable=self.status).pack()
        ttk.Button(frame, text="Начать обработку", command=self._process_images).pack(pady=5)

    def _select_input_folder(self):
        """Выбор входной папки"""
        folder = filedialog.askdirectory(title="Выберите папку с изображениями")
        if folder:
            self.images_folder.set(folder)
            # Автоматически устанавливаем выходную папку
            self.output_path.set(os.path.join(folder, "watermarked"))

    def _select_output_folder(self):
        """Выбор выходной папки"""
        folder = filedialog.askdirectory(title="Выберите папку для сохранения")
        if folder:
            self.output_path.set(folder)

    def _validate_inputs(self):
        """Проверка входных данных"""
        if not self.watermark_text.get():
            messagebox.showwarning("Предупреждение", "Введите текст водяного знака!")
            return False
        
        if not self.images_folder.get():
            messagebox.showwarning("Предупреждение", "Выберите папку с изображениями!")
            return False
        
        if not self.output_path.get():
            messagebox.showwarning("Предупреждение", "Выберите папку для сохранения!")
            return False
        
        try:
            # Проверяем числовые значения
            opacity = float(self.opacity.get())
            if not 0 <= opacity <= 1:
                raise ValueError("Прозрачность должна быть от 0 до 1")

            font_size = int(self.font_size.get())
            if not 12 <= font_size <= 200:
                raise ValueError("Размер шрифта должен быть от 12 до 200")

            angle = float(self.angle.get())
            if not -180 <= angle <= 180:
                raise ValueError("Угол должен быть от -180 до 180")

            density = int(self.tile_density.get())
            if not 2 <= density <= 10:
                raise ValueError("Плотность должна быть от 2 до 10")

            # Проверяем цвет
            color = self.color.get()
            if not (color.startswith('#') and len(color) == 7):
                raise ValueError("Неверный формат цвета (должен быть #RRGGBB)")

            # Проверяем шрифт
            if not self.selected_font.get():
                raise ValueError("Выберите шрифт")

            return True

        except ValueError as e:
            messagebox.showwarning("Предупреждение", str(e))
            return False

    def _process_images(self):
        """Обработка изображений"""
        if not self._validate_inputs():
            return

        try:
            # Создаем водяной знак
            creator = WatermarkCreator(
                text=self.watermark_text.get(),
                font_path=FontManager.get_font_path(self.selected_font.get()),
                font_size=int(self.font_size.get()),
                color=self.color.get(),
                angle=float(self.angle.get())
            )
            
            watermark_path = creator.create()
            if not watermark_path:
                raise Exception("Не удалось создать водяной знак")

            # Подготавливаем папки
            input_folder = self.images_folder.get()
            output_folder = self.output_path.get()
            os.makedirs(output_folder, exist_ok=True)

            # Получаем список изображений
            images = [f for f in os.listdir(input_folder) 
                     if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

            if not images:
                raise Exception("В указанной папке нет изображений")

            # Конфигурация для обработки
            config = {
                'opacity': float(self.opacity.get()),
                'tile_enabled': self.tile_enabled.get(),
                'density': int(self.tile_density.get())
            }

            # Обрабатываем изображения
            self.progress.set(0)
            total_files = len(images)
            processed = 0

            for image_file in images:
                try:
                    input_path = os.path.join(input_folder, image_file)
                    output_path = os.path.join(output_folder, f"watermarked_{image_file}")

                    self.status.set(f"Обработка {image_file}...")
                    if FFmpegHandler.apply_watermark(input_path, watermark_path, output_path, config):
                        processed += 1
                    else:
                        print(f"Ошибка при обработке {image_file}")

                except Exception as e:
                    print(f"Ошибка при обработке {image_file}: {e}")
                    continue

                finally:
                    # Обновляем прогресс
                    self.progress.set((processed / total_files) * 100)
                    self.root.update()

            # Очистка
            creator.cleanup()

            # Итоговое сообщение
            if processed == total_files:
                self.status.set("Обработка завершена успешно!")
                messagebox.showinfo("Успех", f"Обработано {processed} изображений")
            else:
                self.status.set("Обработка завершена с ошибками")
                messagebox.showwarning("Предупреждение", 
                    f"Обработано {processed} из {total_files} изображений")

        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            self.status.set("Произошла ошибка")

def main():
    root = tk.Tk()
    app = WatermarkApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()