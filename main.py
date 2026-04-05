import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
from rembg import remove, new_session
import io
import logging
import sys

# 配置日志
logging.basicConfig(
    filename='error.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

# 设置外观
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 配置窗口
        self.title("智能扣图软件 - Windows 11 中文版")
        self.geometry("1450x750")
        self.minsize(1300, 700)

        # 变量
        self.input_path = None
        self.output_image = None
        self.preview_image = None
        self.current_session = None
        self.current_model_name = "u2net"

        # 默认值常量
        self.DEFAULTS = {
            "alpha_matting": False,
            "fg_threshold": 240,
            "bg_threshold": 10,
            "erode_size": 10
        }

        # 调节参数变量
        self.alpha_matting_var = tk.BooleanVar(value=self.DEFAULTS["alpha_matting"])
        self.fg_threshold_var = tk.IntVar(value=self.DEFAULTS["fg_threshold"])
        self.bg_threshold_var = tk.IntVar(value=self.DEFAULTS["bg_threshold"])
        self.erode_size_var = tk.IntVar(value=self.DEFAULTS["erode_size"])

        # 模型列表
        self.models_map = {
            "通用模型 (u2net)": "u2net",
            "轻量模型 (u2netp)": "u2netp",
            "人像优化 (human)": "u2net_human_seg",
            "衣物优化 (cloth)": "u2net_cloth_seg",
            "物体优化 (silueta)": "silueta",
            "新一代通用 (isnet)": "isnet-general-use"
        }

        # 布局
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 侧边栏
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(9, weight=1) # 恢复底部弹性空间
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="AI 智能扣图", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.select_button = ctk.CTkButton(self.sidebar_frame, text="选择图片", height=32, command=self.open_image)
        self.select_button.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        # 模型选择
        self.model_label = ctk.CTkLabel(self.sidebar_frame, text="选择 AI 模型:", anchor="w", font=ctk.CTkFont(size=12))
        self.model_label.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
        self.model_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, height=32,
                                                   values=list(self.models_map.keys()),
                                                   command=self.change_model_event)
        self.model_optionemenu.grid(row=3, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.model_optionemenu.set("通用模型 (u2net)")

        # 调节参数面板
        self.settings_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.settings_frame.grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        self.alpha_matting_switch = ctk.CTkSwitch(self.settings_frame, text="Alpha 蒙版", 
                                                  font=ctk.CTkFont(size=12),
                                                  variable=self.alpha_matting_var,
                                                  command=self.toggle_matting_controls)
        self.alpha_matting_switch.pack(padx=0, pady=5, anchor="w")

        self.fg_label = ctk.CTkLabel(self.settings_frame, text=f"前景阈值: {self.fg_threshold_var.get()}", font=ctk.CTkFont(size=11))
        self.fg_label.pack(padx=0, pady=(5, 0), anchor="w")
        self.fg_slider = ctk.CTkSlider(self.settings_frame, from_=0, to=255, height=16,
                                       variable=self.fg_threshold_var,
                                       command=lambda e: self.fg_label.configure(text=f"前景阈值: {int(self.fg_threshold_var.get())}"))
        self.fg_slider.pack(padx=0, pady=5, fill="x")

        self.bg_label = ctk.CTkLabel(self.settings_frame, text=f"背景阈值: {self.bg_threshold_var.get()}", font=ctk.CTkFont(size=11))
        self.bg_label.pack(padx=0, pady=(5, 0), anchor="w")
        self.bg_slider = ctk.CTkSlider(self.settings_frame, from_=0, to=255, height=16,
                                       variable=self.bg_threshold_var,
                                       command=lambda e: self.bg_label.configure(text=f"背景阈值: {int(self.bg_threshold_var.get())}"))
        self.bg_slider.pack(padx=0, pady=5, fill="x")

        self.erode_label = ctk.CTkLabel(self.settings_frame, text=f"边缘腐蚀: {self.erode_size_var.get()}", font=ctk.CTkFont(size=11))
        self.erode_label.pack(padx=0, pady=(5, 0), anchor="w")
        self.erode_slider = ctk.CTkSlider(self.settings_frame, from_=0, to=50, height=16,
                                          variable=self.erode_size_var,
                                          command=lambda e: self.erode_label.configure(text=f"边缘腐蚀: {int(self.erode_size_var.get())}"))
        self.erode_slider.pack(padx=0, pady=5, fill="x")

        self.reset_button = ctk.CTkButton(self.settings_frame, text="恢复默认", height=32,
                                          command=self.reset_defaults)
        self.reset_button.pack(padx=0, pady=(10, 0), fill="x")

        # 初始化参数状态
        self.toggle_matting_controls()

        self.process_button = ctk.CTkButton(self.sidebar_frame, text="开始抠图", height=32, command=self.start_processing, state="disabled")
        self.process_button.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

        self.save_button = ctk.CTkButton(self.sidebar_frame, text="保存结果", height=32, command=self.save_image, state="disabled")
        self.save_button.grid(row=6, column=0, padx=20, pady=10, sticky="ew")

        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="外观模式:", anchor="w", font=ctk.CTkFont(size=11))
        self.appearance_mode_label.grid(row=7, column=0, padx=20, pady=(15, 0), sticky="w")
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, height=32, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=8, column=0, padx=20, pady=(5, 20), sticky="ew")
        self.appearance_mode_optionemenu.set("System")

        # 主显示区域
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.main_frame.grid_columnconfigure((0, 1), weight=1, uniform="previews")
        self.main_frame.grid_rowconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(self.main_frame, text="请选择一张图片开始", font=ctk.CTkFont(size=14))
        self.status_label.grid(row=0, column=0, columnspan=2, pady=10)

        # 图片预览容器
        self.original_frame = ctk.CTkFrame(self.main_frame)
        self.original_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.original_label = ctk.CTkLabel(self.original_frame, text="原始图片", font=ctk.CTkFont(size=13))
        self.original_label.pack(pady=5)
        self.original_canvas = ctk.CTkLabel(self.original_frame, text="未选择图片", width=560, height=315, fg_color="gray25")
        self.original_canvas.pack(expand=True, padx=10, pady=10)

        self.result_frame = ctk.CTkFrame(self.main_frame)
        self.result_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.result_label = ctk.CTkLabel(self.result_frame, text="抠图结果", font=ctk.CTkFont(size=13))
        self.result_label.pack(pady=5)
        self.result_canvas = ctk.CTkLabel(self.result_frame, text="等待处理", width=560, height=315, fg_color="gray25")
        self.result_canvas.pack(expand=True, padx=10, pady=10)

        # 进度条
        self.progressbar = ctk.CTkProgressBar(self.main_frame, height=10)
        self.progressbar.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.progressbar.set(0)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def reset_defaults(self):
        self.alpha_matting_var.set(self.DEFAULTS["alpha_matting"])
        self.fg_threshold_var.set(self.DEFAULTS["fg_threshold"])
        self.bg_threshold_var.set(self.DEFAULTS["bg_threshold"])
        self.erode_size_var.set(self.DEFAULTS["erode_size"])
        
        # 更新 UI 标签
        self.fg_label.configure(text=f"前景阈值: {self.DEFAULTS['fg_threshold']}")
        self.bg_label.configure(text=f"背景阈值: {self.DEFAULTS['bg_threshold']}")
        self.erode_label.configure(text=f"边缘腐蚀大小: {self.DEFAULTS['erode_size']}")
        
        self.toggle_matting_controls()
        self.status_label.configure(text="参数已恢复默认")

    def toggle_matting_controls(self):
        # 参数始终保持可调，只是在 Alpha 蒙版开启时才生效
        pass

    def change_model_event(self, new_model_display: str):
        new_model_name = self.models_map.get(new_model_display)
        if new_model_name != self.current_model_name:
            self.current_model_name = new_model_name
            self.current_session = None  # 重置会话以加载新模型
            self.status_label.configure(text=f"已切换到模型: {new_model_display}")

    def open_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.bmp")])
        if file_path:
            self.input_path = file_path
            img = Image.open(file_path)
            self.show_image(img, self.original_canvas)
            self.status_label.configure(text=f"已加载: {os.path.basename(file_path)}")
            self.process_button.configure(state="normal")
            self.result_canvas.configure(image=None, text="等待处理")
            self.save_button.configure(state="disabled")
            self.progressbar.set(0)

    def show_image(self, img, canvas_label):
        # 缩放图片以适应 16:9 比例 (560x315)
        width, height = img.size
        # 设定的最大预览区域为 560x315
        ratio = min(560 / width, 315 / height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        ctk_img = ctk.CTkImage(light_image=img_resized, dark_image=img_resized, size=(new_width, new_height))
        canvas_label.configure(image=ctk_img, text="")
        canvas_label.image = ctk_img  # 保持引用

    def start_processing(self):
        if not self.input_path:
            return
        
        self.process_button.configure(state="disabled")
        self.select_button.configure(state="disabled")
        self.status_label.configure(text="正在抠图，请稍候... (首次运行可能需要下载模型)")
        self.progressbar.set(0.3)
        self.progressbar.start()

        # 在新线程中处理
        thread = threading.Thread(target=self.process_image)
        thread.daemon = True
        thread.start()

    def process_image(self):
        try:
            logging.info(f"开始抠图，模型: {self.current_model_name}")
            # 如果会话不存在，则创建新会话
            if self.current_session is None:
                logging.info(f"加载模型会话: {self.current_model_name}")
                # 显式尝试捕获模型加载错误
                try:
                    self.current_session = new_session(self.current_model_name)
                except Exception as e:
                    logging.error(f"模型会话加载失败: {e}", exc_info=True)
                    raise Exception(f"模型文件加载失败，请检查网络或模型名: {e}")
            
            # 获取当前调节参数
            alpha_matting = self.alpha_matting_var.get()
            fg_threshold = int(self.fg_threshold_var.get())
            bg_threshold = int(self.bg_threshold_var.get())
            erode_size = int(self.erode_size_var.get())

            logging.debug(f"参数: alpha_matting={alpha_matting}, fg={fg_threshold}, bg={bg_threshold}, erode={erode_size}")

            with open(self.input_path, 'rb') as i:
                input_data = i.read()
                logging.info(f"读取图片成功: {len(input_data)} bytes")
                # 使用当前会话和参数进行处理
                output_data = remove(
                    input_data, 
                    session=self.current_session,
                    alpha_matting=alpha_matting,
                    alpha_matting_foreground_threshold=fg_threshold,
                    alpha_matting_background_threshold=bg_threshold,
                    alpha_matting_erode_size=erode_size
                )
                logging.info("抠图计算完成")
                self.output_image = Image.open(io.BytesIO(output_data))
            
            # 回到主线程更新 UI
            self.after(0, self.processing_finished)
        except Exception as e:
            logging.error(f"抠图过程中发生错误: {e}", exc_info=True)
            self.after(0, lambda: self.processing_failed(str(e)))

    def processing_finished(self):
        self.progressbar.stop()
        self.progressbar.set(1.0)
        self.show_image(self.output_image, self.result_canvas)
        self.status_label.configure(text="抠图完成！")
        self.process_button.configure(state="normal")
        self.select_button.configure(state="normal")
        self.save_button.configure(state="normal")

    def processing_failed(self, error_msg):
        self.progressbar.stop()
        self.progressbar.set(0)
        messagebox.showerror("错误", f"抠图失败: {error_msg}")
        self.status_label.configure(text="处理出错")
        self.process_button.configure(state="normal")
        self.select_button.configure(state="normal")

    def save_image(self):
        if self.output_image:
            file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                     filetypes=[("PNG Files", "*.png")])
            if file_path:
                self.output_image.save(file_path)
                messagebox.showinfo("成功", "图片已保存！")

if __name__ == "__main__":
    app = App()
    app.mainloop()
