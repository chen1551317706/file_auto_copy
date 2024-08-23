import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import time
import threading
from datetime import datetime
import uuid

# 常量
uuid_str = str(uuid.getnode())
db = 'sync.db'

class SyncTask:
    def __init__(self, task_id, source, target, frequency):
        self.task_id = task_id  # 添加主键ID
        self.source = source
        self.target = target
        self.frequency = frequency
        self.thread = None
        self.running = False

class SyncApp:
    def __init__(self, root):
        self.root = root
        self.root.title('文件同步工具')
        self.tasks = []
        self.setup_ui()
        self.load_tasks_from_db() # 从数据库加载任务

    def setup_ui(self):
        # 任务列表，高度为4行
        self.tree = ttk.Treeview(self.root, columns=('ID', 'Source', 'Target', 'Frequency'), show='headings', height=4)
        self.tree.heading('ID', text='ID')
        self.tree.heading('Source', text='源文件路径')
        self.tree.heading('Target', text='目标地址路径')
        self.tree.heading('Frequency', text='同步频率(秒)')

        self.tree.column('ID', width=0, stretch=tk.NO) 
        self.tree.column('Source', width=40)  
        self.tree.column('Target', width=40) 
        self.tree.column('Frequency', width=40, anchor=tk.CENTER) 
        self.tree.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.tree.bind('<Double-1>', self.edit_task)  # 添加双击事件

        # 控制按钮
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=10)

        ttk.Button(control_frame, text='添加任务', command=self.open_add_task_window).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text='删除选中任务', command=self.delete_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text='开始同步', command=self.start_sync).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text='停止同步', command=self.stop_sync).pack(side=tk.LEFT, padx=5)

        # 日志区域
        self.log_area = scrolledtext.ScrolledText(self.root, width=45, height=10, wrap=tk.NONE)
        self.log_area.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.logs = []

    def load_tasks_from_db(self):
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS task_list
                     (id INTEGER PRIMARY KEY, uuid TEXT, source TEXT, target TEXT, frequency INTEGER)''')
        
        print(uuid_str)
        c.execute("SELECT id, source, target, frequency FROM task_list WHERE uuid = ?", (uuid_str,))
        rows = c.fetchall()
        
        for row in rows:
            task_id, source, target, frequency = row
            task = SyncTask(task_id, source, target, frequency)
            self.tasks.append(task)
            self.tree.insert('', 'end', values=(task_id, source, target, frequency))
        
        conn.commit()
        conn.close()
    
    def refresh_task(self):
        self.tasks.clear()
        self.tree.delete(*self.tree.get_children())
        self.load_tasks_from_db()

    def edit_task(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning('警告', '请选择要编辑的任务')
            return

        item_values = self.tree.item(selected_item, 'values')
        self.edit_window = tk.Toplevel(self.root)
        self.edit_window.title('编辑任务')

        # 获取主窗口的位置和大小
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        width = self.root.winfo_width()
        height = self.root.winfo_height()

        # 计算弹窗的中心位置
        window_x = x + (width // 2) - (350 // 2)
        window_y = y + (height // 2) - (150 // 2)

        # 设置弹窗的位置
        self.edit_window.geometry(f'350x150+{window_x}+{window_y}')

        ttk.Label(self.edit_window, text='源文件路径:').grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.source_entry = ttk.Entry(self.edit_window, width=30)
        self.source_entry.grid(row=0, column=1, padx=5, pady=5)
        self.source_entry.insert(0, item_values[1])  # 填充当前值

        ttk.Label(self.edit_window, text='目标地址路径:').grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.target_entry = ttk.Entry(self.edit_window, width=30)
        self.target_entry.grid(row=1, column=1, padx=5, pady=5)
        self.target_entry.insert(0, item_values[2])  # 填充当前值

        ttk.Label(self.edit_window, text='同步频率(秒):').grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.freq_entry = ttk.Entry(self.edit_window, width=10)
        self.freq_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        self.freq_entry.insert(0, str(item_values[3]))  # 填充当前值

        button_frame = ttk.Frame(self.edit_window)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text='确认', command=lambda: self.save_task(item_values[0], selected_item)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text='取消', command=self.edit_window.destroy).pack(side=tk.LEFT, padx=5)

    def save_task(self, id, selected_item):
        source = self.source_entry.get()
        target = self.target_entry.get()
        try:
            frequency = int(self.freq_entry.get())
        except ValueError:
            messagebox.showerror('错误', '请输入有效的同步频率（秒）')
            return

        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute("UPDATE task_list SET source = ?, target = ?, frequency = ? WHERE id = ?", 
        (source, target, frequency, id))
        conn.commit()
        conn.close()
        self.refresh_task()
        # index = self.tree.index(selected_item)
        # self.tasks[index] = SyncTask(source, target, frequency)
        # self.tree.item(selected_item, values=(source, target, frequency))  # 更新Treeview
        self.edit_window.destroy()

    def open_add_task_window(self):
        self.add_window = tk.Toplevel(self.root)
        self.add_window.title('添加同步任务')
        self.add_window.geometry('350x150')

        # 获取主窗口的位置和大小
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        width = self.root.winfo_width()
        height = self.root.winfo_height()

        # 计算弹窗的中心位置
        window_x = x + (width // 2) - (350 // 2)
        window_y = y + (height // 2) - (150 // 2)

        # 设置弹窗的位置
        self.add_window.geometry(f'350x150+{window_x}+{window_y}')

        ttk.Label(self.add_window, text='源文件路径:').grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.source_entry = ttk.Entry(self.add_window, width=30)
        self.source_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.add_window, text='目标地址路径:').grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.target_entry = ttk.Entry(self.add_window, width=30)
        self.target_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(self.add_window, text='同步频率(秒):').grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.freq_entry = ttk.Entry(self.add_window, width=10)
        self.freq_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')

        button_frame = ttk.Frame(self.add_window)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text='确认', command=self.add_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text='取消', command=self.add_window.destroy).pack(side=tk.LEFT, padx=5)

    def add_task(self):
        source = self.source_entry.get()
        target = self.target_entry.get()
        try:
            frequency = int(self.freq_entry.get())
        except ValueError:
            messagebox.showerror('错误', '请输入有效的同步频率（秒）')
            return

        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute("INSERT INTO task_list (uuid, source, target, frequency) VALUES (?, ?, ?, ?)", 
                  (uuid_str, source, target, frequency))
        conn.commit()
        conn.close()

        self.refresh_task()

        self.add_window.destroy()

    def delete_task(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning('警告', '请选择要删除的任务')
            return
        column_names = self.tree['columns']
        item_values = self.tree.item(selected_item[0])['values']
        column_index = column_names.index('ID') 
        id = item_values[column_index]
        print(id)

        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute("DELETE FROM task_list WHERE id = ?", (id,)) # 元组
        conn.commit()
        conn.close()
        self.refresh_task()

    def start_sync(self):
        for task in self.tasks:
            if not task.running:
                task.running = True
                task.thread = threading.Thread(target=self.sync_task, args=(task,), daemon=True)
                task.thread.start()

    def stop_sync(self):
        for task in self.tasks:
            task.running = False


    def sync_task(self, task):
        while task.running:
            command = f'copy /Y "{task.source}" "{task.target}"'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            self.log_output(f"同步: {task.source} -> {task.target}\n{result.stdout}")
            time.sleep(task.frequency)

    def log_output(self, output):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        formatted_log = f'{current_time} - {output.strip()}'
        self.logs.append(formatted_log)

        if len(self.logs) > 5:
            self.logs.pop(0)  # 移除最旧的日志

        self.update_log_area()

    def update_log_area(self):
        self.log_area.delete(1.0, tk.END)  # 清空文本框
        for log in self.logs:
            self.log_area.insert(tk.END, log + '\n')

# 创建主窗口
root = tk.Tk()
app = SyncApp(root)
root.mainloop()
