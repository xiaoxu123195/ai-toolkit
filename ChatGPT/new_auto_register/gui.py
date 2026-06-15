"""gptregister GUI —— ChatGPT 网页注册取 accessToken 的图形界面 (ttkbootstrap 美化版)。

复用 register_token.py 的注册逻辑：表单字段即 config.yaml 各项，
启动读 config.yaml 当默认值，点「开始」用表单值跑并存回 config.yaml，
注册在后台线程执行，日志实时刷到界面。
"""
import os
import queue
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import tkinter as tk
from tkinter import messagebox, scrolledtext

import ttkbootstrap as tb

import yaml

import register_token as rt
import domains

CONFIG_PATH = os.path.join(rt._app_dir(), "config.yaml")
THEME = "flatly"           # 浅色现代主题
UI_FONT = ("Microsoft YaHei UI", 10)

# (cfg key, 中文标签, 默认值)
TEXT_FIELDS = [
    ("email_api", "邮箱服务地址", "https://"),
    ("email_api_key", "邮箱 API Key", ""),
    ("email_domain", "邮箱域名", ""),
    ("access_token_file", "输出文件", "ac/tokens.txt"),
]


class QueueLogHandler(logging.Handler):
    """把日志记录塞进队列，由主线程定时取出刷到文本框（线程安全）。"""

    def __init__(self, q: queue.Queue):
        super().__init__()
        self.q = q

    def emit(self, record):
        try:
            self.q.put_nowait(self.format(record))
        except Exception:
            pass


class App:
    def __init__(self, root: tb.Window):
        self.root = root
        root.title("gptregister")
        root.geometry("700x640")
        root.minsize(620, 560)
        try:
            root.style.configure(".", font=UI_FONT)
        except Exception:
            pass

        self.log_queue: queue.Queue = queue.Queue()
        self.worker = None
        self.base_cfg = {}        # 保留 config.yaml 中表单未覆盖的键(如 upload_*)
        self.text_vars = {}
        self._file_log_added = False

        self._build_ui()
        self._load_config()
        self._init_logging()
        self.root.after(100, self._drain_log)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI ----------

    def _build_ui(self):
        outer = tb.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        # 标题
        tb.Label(outer, text="ChatGPT 注册取 Token", font=("Microsoft YaHei UI", 16, "bold"),
                 bootstyle="primary").pack(anchor="w")
        tb.Label(outer, text="填写邮箱服务信息，点「开始」批量注册并获取 accessToken",
                 bootstyle="secondary").pack(anchor="w", pady=(2, 14))

        # 表单
        form = tb.Labelframe(outer, text=" 配置 ", padding=14, bootstyle="primary")
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        row = 0
        for key, label, _ in TEXT_FIELDS:
            tb.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=6)
            var = tk.StringVar()
            self.text_vars[key] = var
            if key == "email_domain":
                self.domain_combo = tb.Combobox(form, textvariable=var)
                self.domain_combo.grid(row=row, column=1, columnspan=2, sticky="ew", pady=6)
                tb.Button(form, text="查询域名", command=self._query_domains,
                          bootstyle="info-outline", width=10).grid(row=row, column=3, sticky="e", padx=(10, 0), pady=6)
            else:
                tb.Entry(form, textvariable=var).grid(row=row, column=1, columnspan=3, sticky="ew", pady=6)
            row += 1

        # 数量 / 并发
        tb.Label(form, text="注册数量").grid(row=row, column=0, sticky="w", padx=(0, 10), pady=6)
        self.count_var = tk.StringVar(value="1")
        tb.Spinbox(form, from_=1, to=9999, width=10, textvariable=self.count_var).grid(
            row=row, column=1, sticky="w", pady=6)
        tb.Label(form, text="并发数").grid(row=row, column=2, sticky="e", padx=(10, 10), pady=6)
        self.workers_var = tk.StringVar(value="1")
        tb.Spinbox(form, from_=1, to=64, width=10, textvariable=self.workers_var).grid(
            row=row, column=3, sticky="w", pady=6)
        row += 1

        # 写日志开关
        self.logfile_var = tk.BooleanVar(value=False)
        tb.Checkbutton(form, text="写日志到文件 (logs/)", variable=self.logfile_var,
                       bootstyle="round-toggle").grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 2))

        # 操作栏
        bar = tb.Frame(outer)
        bar.pack(fill="x", pady=14)
        self.start_btn = tb.Button(bar, text="▶  开始", command=self._start, bootstyle="success", width=12)
        self.start_btn.pack(side="left")
        self.stop_btn = tb.Button(bar, text="■  停止", command=self._stop, bootstyle="danger-outline",
                                  width=12, state="disabled")
        self.stop_btn.pack(side="left", padx=10)
        self.status_var = tk.StringVar(value="就绪")
        tb.Label(bar, textvariable=self.status_var, bootstyle="secondary").pack(side="right")

        # 日志
        tb.Label(outer, text="日志").pack(anchor="w")
        self.text = scrolledtext.ScrolledText(outer, height=15, wrap="word", font=("Consolas", 9),
                                              relief="flat", borderwidth=1, padx=8, pady=6, state="disabled")
        self.text.pack(fill="both", expand=True, pady=(4, 0))

    # ---------- 配置 ----------

    def _load_config(self):
        cfg = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
            except Exception:
                cfg = {}
        self.base_cfg = cfg
        for key, _, default in TEXT_FIELDS:
            self.text_vars[key].set(str(cfg.get(key, default)))
        self.count_var.set(str(cfg.get("count", 1)))
        self.workers_var.set(str(cfg.get("max_workers", 1)))
        self.logfile_var.set(bool(cfg.get("log_to_file", 0)))

    def _collect_cfg(self) -> dict:
        cfg = dict(self.base_cfg)  # 保留 upload_* 等未在界面暴露的键
        for key, _, _ in TEXT_FIELDS:
            cfg[key] = self.text_vars[key].get().strip()
        cfg["count"] = self._to_int(self.count_var.get(), 1)
        cfg["max_workers"] = self._to_int(self.workers_var.get(), 1)
        cfg["log_to_file"] = 1 if self.logfile_var.get() else 0
        return cfg

    def _save_config(self, cfg: dict):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            rt.log.warning(f"保存 config.yaml 失败: {e}")

    @staticmethod
    def _to_int(s, default):
        try:
            return max(1, int(str(s).strip()))
        except (TypeError, ValueError):
            return default

    # ---------- 域名查询 ----------

    def _query_domains(self):
        api = self.text_vars["email_api"].get().strip()
        key = self.text_vars["email_api_key"].get().strip()
        if not api or not key:
            messagebox.showwarning("缺少配置", "请先填写「邮箱服务地址」和「邮箱 API Key」")
            return
        rt.log.info("查询可用域名…")
        threading.Thread(target=self._do_query_domains, args=(api, key), daemon=True).start()

    def _do_query_domains(self, api, key):
        try:
            doms = [d.strip() for d in domains.get_domains(api, key) if d.strip()]
            self.root.after(0, lambda: self._fill_domains(doms))
        except Exception as e:
            rt.log.warning(f"查询域名失败: {e}")
            self.root.after(0, lambda: messagebox.showerror("查询失败", str(e)))

    def _fill_domains(self, doms):
        self.domain_combo["values"] = doms
        rt.log.info(f"可用域名 {len(doms)} 个: {', '.join(doms)}")
        if doms and not self.text_vars["email_domain"].get().strip():
            self.text_vars["email_domain"].set(doms[0])

    # ---------- 日志 ----------

    def _init_logging(self):
        rt.log.setLevel(logging.INFO)
        handler = QueueLogHandler(self.log_queue)
        handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
        rt.log.addHandler(handler)

    def _enable_file_log(self):
        if self._file_log_added:
            return
        try:
            import time
            logs_dir = os.path.join(rt._app_dir(), "logs")
            os.makedirs(logs_dir, exist_ok=True)
            fh = logging.FileHandler(
                os.path.join(logs_dir, f"{time.strftime('%Y%m%d_%H%M%S')}_token.log"), encoding="utf-8")
            fh.setFormatter(logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s", datefmt="%H:%M:%S"))
            rt.log.addHandler(fh)
            self._file_log_added = True
        except Exception as e:
            rt.log.warning(f"启用文件日志失败: {e}")

    def _drain_log(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.text.configure(state="normal")
                self.text.insert("end", msg + "\n")
                self.text.see("end")
                self.text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._drain_log)

    # ---------- 运行 ----------

    def _start(self):
        cfg = self._collect_cfg()
        if not cfg.get("email_api") or not cfg.get("email_api_key"):
            messagebox.showwarning("缺少配置", "请填写「邮箱服务地址」和「邮箱 API Key」")
            return
        self._save_config(cfg)

        if cfg.get("log_to_file"):
            self._enable_file_log()

        rt.STOP.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set("运行中…")

        count = cfg["count"]
        max_workers = cfg["max_workers"]
        self.worker = threading.Thread(target=self._run, args=(cfg, count, max_workers), daemon=True)
        self.worker.start()

    def _run(self, cfg, count, max_workers):
        success = 0
        done = 0
        try:
            if max_workers <= 1:
                for i in range(1, count + 1):
                    if rt.STOP.is_set():
                        break
                    ok = rt.register_one(i, count, cfg)
                    done += 1
                    success += 1 if ok else 0
                    self._set_status(success, done, count)
            else:
                with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="worker") as pool:
                    futs = [pool.submit(rt.register_one, i, count, cfg) for i in range(1, count + 1)]
                    for fut in as_completed(futs):
                        done += 1
                        try:
                            success += 1 if fut.result() else 0
                        except Exception:
                            pass
                        self._set_status(success, done, count)
        finally:
            rt.log.info(f"完成: 成功 {success}/{count}")
            self.root.after(0, lambda: self._on_done(success, count))

    def _set_status(self, success, done, total):
        self.root.after(0, lambda: self.status_var.set(f"运行中… 成功 {success}/{done}（共 {total}）"))

    def _on_done(self, success, count):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        stopped = rt.STOP.is_set()
        self.status_var.set(f"{'已停止' if stopped else '完成'}：成功 {success}/{count}")

    def _stop(self):
        rt.STOP.set()
        self.stop_btn.config(state="disabled")
        rt.log.info("已请求停止，等待当前任务结束…")

    def _on_close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askokcancel("退出", "正在注册，确定退出吗？"):
                return
            rt.STOP.set()
        self.root.destroy()


def main():
    root = tb.Window(themename=THEME)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
