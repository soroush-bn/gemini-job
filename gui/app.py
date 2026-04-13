import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import threading
import queue
import time
import os
import sys
import base64
import io
import re
from datetime import datetime
from PIL import Image, ImageTk

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from main import run_job_application_pipeline, run_job_finder
from agents.apply_agent.agent import run_apply_pipeline, get_apply_agent, get_ready_jobs
from utils.messenger import pipeline_messenger

# Constants for Dropdowns
TECH_ROLES = [
    "Software Engineer", "Senior Software Engineer", "Backend Developer", "Frontend Developer", 
    "Fullstack Developer", "Machine Learning Engineer", "Data Scientist", "Data Engineer", 
    "DevOps Engineer", "Cloud Architect", "Cyber Security Analyst", "Mobile Developer (Android/iOS)", 
    "AI Research Scientist", "Embedded Systems Engineer", "Quality Assurance Engineer", 
    "Site Reliability Engineer (SRE)", "Product Manager (Tech)"
]

COUNTRIES = [
    "United States", "Canada", "United Kingdom", "Germany", "France", "Netherlands", 
    "Australia", "India", "Singapore", "Japan", "United Arab Emirates", "Remote",
    "Sweden", "Switzerland", "Poland", "Ireland", "Spain", "Italy", "Brazil", "Other"
]

WORK_TYPES = ["Any", "Remote", "In-person", "Hybrid"]

class JobAgentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gemini Job Agent")
        self.root.geometry("1400x950")

        self.setup_ui()
        self.log_queue = queue.Queue()
        self.update_gui_from_queue()

        # Metrics state
        self.total_cost = 0.0
        self.total_tokens = 0
        self.current_tk_image = None 

        # Intercept pipeline_messenger
        self.original_send = pipeline_messenger.send
        pipeline_messenger.send = self.custom_send
        
        # Load existing jobs on startup
        self.root.after(1000, self.load_existing_jobs)

    def load_existing_jobs(self):
        try:
            from config import TRACKER_FILE_PATH
            if os.path.exists(TRACKER_FILE_PATH):
                for i in self.job_tree.get_children():
                    self.job_tree.delete(i)
                    
                with open(TRACKER_FILE_PATH, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines:
                        if "|" in line and "---" not in line and "Job Name" not in line:
                            parts = [p.strip() for p in line.split("|")]
                            if len(parts) >= 8:
                                company = parts[2]
                                role = parts[3]
                                status = parts[6]
                                if company and role:
                                    # Add '🚀 APPLY' to action column
                                    self.job_tree.insert('', tk.END, values=(company, role, status, "🚀 APPLY"))
        except Exception as e:
            print(f"Error loading existing jobs: {e}")

    def setup_ui(self):
        # Main Layout: 3 Columns
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # --- LEFT PANEL: Token Tracker ---
        self.left_frame = ttk.Frame(self.paned_window, padding="5")
        self.paned_window.add(self.left_frame, weight=1)
        
        ttk.Label(self.left_frame, text="Token Tracker", font=('Helvetica', 12, 'bold')).pack(pady=5)
        
        columns = ('node', 'tokens', 'cost')
        self.token_tree = ttk.Treeview(self.left_frame, columns=columns, show='headings', height=15)
        self.token_tree.heading('node', text='Node')
        self.token_tree.heading('tokens', text='Tokens')
        self.token_tree.heading('cost', text='Cost (CAD)')
        self.token_tree.column('node', width=100)
        self.token_tree.column('tokens', width=80)
        self.token_tree.column('cost', width=80)
        self.token_tree.pack(fill=tk.BOTH, expand=True)

        self.cost_label = ttk.Label(self.left_frame, text="Total Cost: $0.000000", font=('Helvetica', 10, 'bold'))
        self.cost_label.pack(pady=10)

        # --- CENTER PANEL: Controls, Activity & Logs ---
        self.center_frame = ttk.Frame(self.paned_window, padding="5")
        self.paned_window.add(self.center_frame, weight=3)

        # 1. Controls
        ctrl_frame = ttk.LabelFrame(self.center_frame, text="Controls", padding="10")
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))

        search_frame = ttk.Frame(ctrl_frame)
        search_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="Role:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.role_cb = ttk.Combobox(search_frame, values=TECH_ROLES, width=25)
        self.role_cb.grid(row=0, column=1, sticky=tk.EW, padx=2)
        self.role_cb.set(TECH_ROLES[5])

        ttk.Label(search_frame, text="Country:").grid(row=0, column=2, sticky=tk.W, padx=(10, 2))
        self.country_cb = ttk.Combobox(search_frame, values=COUNTRIES, width=15)
        self.country_cb.grid(row=0, column=3, sticky=tk.EW, padx=2)
        self.country_cb.set(COUNTRIES[1])

        ttk.Label(search_frame, text="Type:").grid(row=0, column=4, sticky=tk.W, padx=(10, 2))
        self.type_cb = ttk.Combobox(search_frame, values=WORK_TYPES, width=10)
        self.type_cb.grid(row=0, column=5, sticky=tk.EW, padx=2)
        self.type_cb.set(WORK_TYPES[0])

        search_frame.columnconfigure(1, weight=2)
        search_frame.columnconfigure(3, weight=1)
        search_frame.columnconfigure(5, weight=1)

        btn_frame = ttk.Frame(ctrl_frame)
        btn_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(btn_frame, text="1. Find Jobs", command=self.start_job_finder).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(btn_frame, text="Apply to All Ready", command=self.start_apply_agent).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(btn_frame, text="Refresh Tracker", command=self.load_existing_jobs).pack(side=tk.LEFT, padx=2)
        
        url_frame = ttk.Frame(ctrl_frame)
        url_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        ttk.Label(url_frame, text="Direct Job URL:").pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(url_frame, text="2. Run Pipeline", command=self.start_pipeline).pack(side=tk.LEFT)

        # 2. Agent Activity (Graphic View)
        activity_frame = ttk.LabelFrame(self.center_frame, text="Agent Eyes (Live View)", padding="5")
        activity_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.stage_label = ttk.Label(activity_frame, text="Current Stage: Idle", font=('Helvetica', 10, 'bold'), foreground="blue")
        self.stage_label.pack(anchor=tk.W, pady=2)

        self.canvas = tk.Canvas(activity_frame, bg="black", height=450)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 3. Pipeline Logs
        log_label_frame = ttk.LabelFrame(self.center_frame, text="Pipeline Logs", padding="5")
        log_label_frame.pack(fill=tk.BOTH, expand=True)
        self.log_area = scrolledtext.ScrolledText(log_label_frame, state='disabled', wrap=tk.WORD, font=('Consolas', 9), height=10)
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # --- RIGHT PANEL: Job Tracker ---
        self.right_frame = ttk.Frame(self.paned_window, padding="5")
        self.paned_window.add(self.right_frame, weight=1)

        # Header for Right Panel
        tracker_header = ttk.Frame(self.right_frame)
        tracker_header.pack(fill=tk.X, pady=5)
        
        ttk.Label(tracker_header, text="Job Tracker", font=('Helvetica', 12, 'bold')).pack(side=tk.LEFT)
        ttk.Button(tracker_header, text="Refresh", command=self.load_existing_jobs, width=8).pack(side=tk.RIGHT)
        
        job_columns = ('company', 'role', 'status', 'action')
        self.job_tree = ttk.Treeview(self.right_frame, columns=job_columns, show='headings', height=15)
        self.job_tree.heading('company', text='Company')
        self.job_tree.heading('role', text='Role')
        self.job_tree.heading('status', text='Status')
        self.job_tree.heading('action', text='Action')
        self.job_tree.column('company', width=100)
        self.job_tree.column('role', width=100)
        self.job_tree.column('status', width=80)
        self.job_tree.column('action', width=80, anchor=tk.CENTER)
        self.job_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind single click to detect "Apply" link click
        self.job_tree.bind("<ButtonRelease-1>", self.on_tree_click)
        
        # Right click menu (keep as fallback)
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Apply to this Job", command=self.apply_selected_job)
        self.job_tree.bind("<Button-3>", self.on_tree_right_click)

    def on_tree_click(self, event):
        region = self.job_tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.job_tree.identify_column(event.x)
            # Column #4 is 'action'
            if column == "#4":
                item = self.job_tree.identify_row(event.y)
                if item:
                    self.job_tree.selection_set(item)
                    self.apply_selected_job()

    def on_tree_right_click(self, event):
        item = self.job_tree.identify_row(event.y)
        if item:
            self.job_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def apply_selected_job(self):
        selected = self.job_tree.selection()
        if not selected: return
        item_data = self.job_tree.item(selected[0])['values']
        company_name = str(item_data[0])
        threading.Thread(target=self.run_single_apply_thread, args=(company_name,), daemon=True).start()

    def run_single_apply_thread(self, company_name):
        self.log(f">>> Starting Apply Agent for: {company_name}")
        try:
            ready_jobs = get_ready_jobs()
            # Log all companies for debugging
            # print(f"DEBUG: Ready jobs companies: {[j['company'] for j in ready_jobs]}")
            
            target_job = next((j for j in ready_jobs if j['company'].strip().lower() == company_name.strip().lower()), None)
            
            if not target_job:
                self.log(f"Error: Job at {company_name} not found or status is not 'ready to submit'.")
                return

            import json
            with open("user_profile.json", "r", encoding="utf-8") as f:
                user_info = json.load(f)
            
            jd_path = os.path.join(target_job['path'], "job_description.txt")
            with open(jd_path, "r", encoding="utf-8") as f:
                jd_text = f.read()
            
            cv_path = None
            for f_name in os.listdir(target_job['path']):
                if f_name.endswith(".pdf") and ("CV" in f_name or "Resume" in f_name or "tailored" in f_name):
                    cv_path = os.path.join(target_job['path'], f_name)
                    break
            
            cl_path = None
            for f_name in os.listdir(target_job['path']):
                if f_name.endswith(".pdf") and ("Cover" in f_name or "Letter" in f_name):
                    cl_path = os.path.join(target_job['path'], f_name)
                    break

            agent = get_apply_agent()
            chat = agent.start_chat(enable_automatic_function_calling=True)
            prompt = f"Apply for this job:\nCompany: {target_job['company']}\nRole: {target_job['role']}\nJD Context: {jd_text[:1000]}...\nCV Path: {cv_path}\nCover Letter Path: {cl_path}\nUser Info: {json.dumps(user_info)}"
            chat.send_message(prompt)
            
            self.log(f"Finished applying for {company_name}")
            self.root.after(2000, self.load_existing_jobs)
        except Exception as e:
            self.log(f"Error applying to {company_name}: {e}")

    def custom_send(self, event_type, data):
        self.log_queue.put({"type": event_type, "data": data})

    def update_gui_from_queue(self):
        try:
            while True:
                event = self.log_queue.get_nowait()
                etype = event["type"]
                data = event["data"]

                if etype == "log":
                    self.log(str(data))
                elif etype == "agent_chat":
                    self.log(f"[{data['role'].upper()}]: {data['content']}")
                elif etype == "metrics":
                    self.update_metrics(data)
                elif etype == "job_tracked":
                    self.update_job_tracker(data)
                elif etype == "agent_activity":
                    self.stage_label.config(text=f"Current Stage: {data.get('stage', 'Unknown')}")
                elif etype == "screenshot":
                    self.update_screenshot(data["data"])
                
        except queue.Empty:
            pass
        self.root.after(100, self.update_gui_from_queue)

    def update_screenshot(self, b64_data):
        try:
            img_data = base64.b64decode(b64_data)
            img = Image.open(io.BytesIO(img_data))
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            if canvas_width > 1 and canvas_height > 1:
                img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            self.current_tk_image = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(canvas_width//2, canvas_height//2, anchor=tk.CENTER, image=self.current_tk_image)
        except Exception as e:
            print(f"Error updating screenshot: {e}")

    def log(self, message):
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, f"{message}\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state='disabled')

    def update_metrics(self, data):
        self.token_tree.insert('', tk.END, values=(data['node'], data['total_tokens'], f"${data['cost_cad']:.6f}"))
        self.total_cost += data['cost_cad']
        self.cost_label.config(text=f"Total Cost: ${self.total_cost:.6f}")

    def update_job_tracker(self, data):
        self.job_tree.insert('', tk.END, values=(data['company'], data['role'], data['status'], "🚀 APPLY"))

    def gui_input(self, prompt):
        result = [None]
        event = threading.Event()
        def ask():
            res = simpledialog.askstring("Agent Input", prompt, parent=self.root)
            result[0] = res
            event.set()
        self.root.after(0, ask)
        event.wait()
        return result[0] or ""

    def start_job_finder(self):
        role = self.role_cb.get()
        country = self.country_cb.get()
        work_type = self.type_cb.get()
        query = f"Find me {role} jobs in {country} with a preference for {work_type} roles."
        threading.Thread(target=self.run_finder_thread, args=(query,), daemon=True).start()

    def run_finder_thread(self, query):
        self.log(f">>> Starting Job Finder for: {query}")
        try:
            job_urls = run_job_finder(input_func=self.gui_input, initial_query=query)
            if job_urls:
                self.log(f"Found {len(job_urls)} jobs. Starting pipeline...")
                for url in job_urls:
                    run_job_application_pipeline(url)
            else:
                self.log("No jobs found.")
        except Exception as e:
            self.log(f"Error in Finder: {e}")

    def start_pipeline(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a Job URL")
            return
        threading.Thread(target=self.run_pipeline_thread, args=(url,), daemon=True).start()

    def run_pipeline_thread(self, url):
        self.log(f">>> Running pipeline for: {url}")
        try:
            run_job_application_pipeline(url)
            self.log("Pipeline complete!")
            self.root.after(2000, self.load_existing_jobs)
        except Exception as e:
            self.log(f"Error in Pipeline: {e}")

    def start_apply_agent(self):
        threading.Thread(target=self.run_apply_agent_thread, daemon=True).start()

    def run_apply_agent_thread(self):
        try:
            run_apply_pipeline()
            self.root.after(2000, self.load_existing_jobs)
        except Exception as e:
            self.log(f"Error in Apply Agent: {e}")

def main():
    root = tk.Tk()
    app = JobAgentGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
