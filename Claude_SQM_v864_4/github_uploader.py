import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import subprocess
import os
import sys
import json
import re
from datetime import datetime

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    import google.genai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as genai
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False


class GitHubUploader:
    MAX_AI_REPAIR = 3

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub 업로드 도우미")
        self.root.geometry("600x520")
        self.root.configure(bg="#f0f0f0")

        self.folder_path = tk.StringVar()
        self.repo_name = tk.StringVar()
        self.branch = tk.StringVar(value="main")
        self.release_note = tk.StringVar()
        self.ai_retry_count = 0
        self.last_error = ""
        self.ai_provider = tk.StringVar(value="openai")

        self._load_api_keys()
        self._setup_ui()
        self._update_ai_status()

    def _load_api_keys(self):
        self.gemini_key = None
        self.openai_key = None
        self.claude_key = None

        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.claude_key = os.environ.get("ANTHROPIC_API_KEY")

        if not self.gemini_key and not self.openai_key and not self.claude_key:
            current_dir = os.getcwd()
            env_path = os.path.join(current_dir, ".env")
            if not os.path.exists(env_path):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                env_path = os.path.join(script_dir, ".env")

            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY="):
                            self.gemini_key = line.split("=")[1].strip()
                        elif line.startswith("OPENAI_API_KEY="):
                            self.openai_key = line.split("=")[1].strip()
                        elif line.startswith("ANTHROPIC_API_KEY="):
                            self.claude_key = line.split("=")[1].strip()
            else:
                self._prompt_api_keys()

    def _prompt_api_keys(self):
        if OPENAI_AVAILABLE:
            key = simpledialog.askstring(
                "API 키 입력",
                "OpenAI API 키를 입력하세요:\n(없으면 Cancel)"
            )
            if key:
                self.openai_key = key.strip()

        if CLAUDE_AVAILABLE and not self.claude_key:
            key = simpledialog.askstring(
                "API 키 입력",
                "Anthropic API 키를 입력하세요:\n(없으면 Cancel)"
            )
            if key:
                self.claude_key = key.strip()

        if GEMINI_AVAILABLE and not self.gemini_key:
            key = simpledialog.askstring(
                "API 키 입력",
                "Google API 키를 입력하세요:\n(없으면 Cancel)"
            )
            if key:
                self.gemini_key = key.strip()

    def _update_ai_status(self):
        provider = self.ai_provider.get()
        status = "사용불가"
        fg_color = "#999"

        if provider == "gemini" and GEMINI_AVAILABLE and self.gemini_key:
            status = "Gemini 준비됨"
            fg_color = "#4CAF50"
        elif provider == "openai" and OPENAI_AVAILABLE and self.openai_key:
            status = "OpenAI 준비됨"
            fg_color = "#4CAF50"
        elif provider == "claude" and CLAUDE_AVAILABLE and self.claude_key:
            status = "Claude 준비됨"
            fg_color = "#4CAF50"

        self.ai_status.config(text=status, fg=fg_color)

    def _setup_ui(self):
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        title = tk.Label(
            main_frame,
            text="GitHub 업로드 도우미",
            font=("Segoe UI", 18, "bold"),
            bg="#f0f0f0",
            fg="#333"
        )
        title.pack(pady=(0, 10))

        provider_frame = tk.Frame(main_frame, bg="#f0f0f0")
        provider_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            provider_frame,
            text="AI:",
            font=("Segoe UI", 10),
            bg="#f0f0f0",
            width=10,
            anchor="e"
        ).pack(side="left", padx=(0, 5))

        providers = []
        if OPENAI_AVAILABLE:
            providers.append("OpenAI")
        if CLAUDE_AVAILABLE:
            providers.append("Claude")
        if GEMINI_AVAILABLE:
            providers.append("Gemini")

        if not providers:
            providers = ["없음"]

        self.ai_provider.set(providers[0])
        provider_menu = tk.OptionMenu(
            provider_frame,
            self.ai_provider,
            *providers,
            command=lambda _: self._update_ai_status()
        )
        provider_menu.config(font=("Segoe UI", 10), width=12)
        provider_menu.pack(side="left", padx=(0, 10))

        self.ai_status = tk.Label(
            provider_frame,
            text="준비됨",
            font=("Segoe UI", 10),
            bg="#f0f0f0",
            fg="green"
        )
        self.ai_status.pack(side="left")

        btn_frame = tk.Frame(main_frame, bg="#f0f0f0")
        btn_frame.pack(fill="x", pady=(0, 10))

        btn_select = tk.Button(
            btn_frame,
            text="1. 폴더 선택",
            font=("Segoe UI", 11, "bold"),
            width=15,
            height=2,
            bg="#4CAF50",
            fg="white",
            relief="flat",
            command=self._select_folder
        )
        btn_select.pack(pady=3)

        self.lbl_folder = tk.Label(
            btn_frame,
            text="선택된 폴더: 없음",
            font=("Segoe UI", 9),
            bg="#f0f0f0",
            fg="#666",
            wraplength=500
        )
        self.lbl_folder.pack(pady=(0, 10))

        btn_repo = tk.Button(
            btn_frame,
            text="2. GitHub 업로드",
            font=("Segoe UI", 11, "bold"),
            width=15,
            height=2,
            bg="#2196F3",
            fg="white",
            relief="flat",
            command=self._upload_to_github
        )
        btn_repo.pack(pady=3)

        self.status = tk.Label(
            main_frame,
            text="준비됨",
            font=("Segoe UI", 11, "bold"),
            bg="#f0f0f0",
            fg="#2196F3"
        )
        self.status.pack(pady=(0, 10))

        log_frame = tk.Frame(main_frame, bg="#f0f0f0")
        log_frame.pack(fill="x", pady=(10, 0))

        tk.Label(
            log_frame,
            text="로그",
            font=("Segoe UI", 9, "bold"),
            bg="#f0f0f0"
        ).pack(anchor="w")

        self.error_log = tk.Text(
            log_frame,
            height=4,
            font=("Consolas", 8),
            bg="#1e1e1e",
            fg="#00ff00",
            insertbackground="white"
        )
        self.error_log.pack(fill="x")

    def _select_folder(self):
        folder = filedialog.askdirectory(title="업로드할 폴더 선택")
        if folder:
            self.folder_path.set(folder)
            self.lbl_folder.config(text=f"선택된 폴더: {folder}")
            self._log_error(f"폴더 선택: {folder}")

    def _upload_to_github(self):
        if not self.folder_path.get():
            messagebox.showerror("오류", "폴더를 선택해주세요.")
            return

        repo_full = simpledialog.askstring(
            "레포지터리",
            "레포지터리 입력 (예: username/repo):"
        )
        if not repo_full:
            return

        if "/" not in repo_full:
            messagebox.showerror("오류", "형식: username/repo")
            return

        self.repo_name.set(repo_full)
        self.ai_retry_count = 0
        self.last_error = ""
        self.status.config(text="처리 중...", fg="orange")
        self.root.update()

        while self.ai_retry_count <= self.MAX_AI_REPAIR:
            try:
                self._git_process(repo_full)
                messagebox.showinfo("완료", f"업로드 완료!\n{repo_full}")
                self.status.config(text="완료됨", fg="green")
                return
            except Exception as e:
                error_msg = str(e)
                self.last_error = error_msg
                self._log_error(error_msg)

                if self.ai_retry_count >= self.MAX_AI_REPAIR:
                    messagebox.showerror(
                        "복구 실패",
                        f"최대 시도 횟수 초과\n{error_msg}"
                    )
                    self.status.config(text="실패", fg="red")
                    return

                repair_result = self._ai_repair(error_msg, repo_full)
                if repair_result:
                    self.ai_retry_count += 1
                    self.status.config(
                        text=f"AI 복구 시도 {self.ai_retry_count}/{self.MAX_AI_REPAIR}...",
                        fg="purple"
                    )
                    self.root.update()
                else:
                    messagebox.showerror("오류", error_msg)
                    self.status.config(text="실패", fg="red")
                    return

    def _log_error(self, msg):
        self.error_log.config(state="normal")
        self.error_log.insert("end", f"\n[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.error_log.see("end")
        self.error_log.config(state="disabled")

    def _git_process(self, repo_full):
        folder = self.folder_path.get()
        os.chdir(folder)

        branch_name = self.branch.get()
        commit_msg = f"Upload {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            subprocess.run(["git", "init"], check=True, capture_output=True)

        subprocess.run(
            ["git", "add", "-A"],
            check=True,
            capture_output=True
        )

        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True
        )
        if not result.stdout.strip():
            raise Exception("nothing to commit")

        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            check=True,
            capture_output=True
        )

        try:
            subprocess.run(
                ["git", "branch", "-M", branch_name],
                check=True,
                capture_output=True
            )
        except Exception:
            pass

        result = subprocess.run(
            ["git", "remote", "get", "origin"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            subprocess.run(
                ["git", "remote", "add", "origin",
                 f"https://github.com/{repo_full}.git"],
                check=True,
                capture_output=True
            )
        else:
            subprocess.run(
                ["git", "remote", "set-url", "origin",
                 f"https://github.com/{repo_full}.git"],
                check=True,
                capture_output=True
            )

        result = subprocess.run(
            ["git", "push", "-u", "origin", branch_name, "--force"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            error_output = result.stderr
            if "rejected" in error_output.lower() or "denied" in error_output.lower():
                fetch_result = subprocess.run(
                    ["git", "fetch", "origin", branch_name],
                    capture_output=True,
                    text=True
                )
                if fetch_result.returncode == 0:
                    subprocess.run(
                        ["git", "rebase", f"origin/{branch_name}"],
                        check=True,
                        capture_output=True
                    )
                    subprocess.run(
                        ["git", "push", "-u", "origin", branch_name, "--force"],
                        check=True,
                        capture_output=True
                    )
                else:
                    raise Exception(f"Push 실패: {error_output}")
            else:
                raise Exception(f"Push 실패: {error_output}")

        self._create_release_note()

    def _create_release_note(self):
        commit_msg = f"Upload {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        tag = datetime.now().strftime("v%Y%m%d-%H%M")
        note_content = f"{tag}\n\n- {commit_msg}"

        try:
            subprocess.run(
                ["git", "tag", "-a", tag, "-m", note_content],
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "push", "origin", tag],
                check=True,
                capture_output=True
            )
        except Exception as e:
            print(f"태그 푸시 실패: {e}")

    def _ai_repair(self, error_msg, repo_full):
        provider = self.ai_provider.get()

        if provider == "gemini":
            return self._ai_repair_gemini(error_msg, repo_full)
        elif provider == "openai":
            return self._ai_repair_openai(error_msg, repo_full)
        elif provider == "claude":
            return self._ai_repair_claude(error_msg, repo_full)

        return False

    def _ai_repair_gemini(self, error_msg, repo_full):
        if not GEMINI_AVAILABLE or not self.gemini_key:
            return False

        self._log_error("Gemini 복구 시작...")

        try:
            from google import genai

            client = genai.GenAI(api_key=self.gemini_key)

            folder = os.path.basename(self.folder_path.get())
            prompt = f"""GitHub Push 오류 분석 및 복구 명령어 제안.

오류: {error_msg}
폴더: {folder}
레포지터리: {repo_full}

Git 복구 명령어만 출력."""

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt]
            )
            response_text = response.text.strip()

            self._log_error(f"Gemini 제안: {response_text[:150]}")

            return self._execute_repair_commands(response_text)

        except Exception as e:
            self._log_error(f"Gemini 오류: {str(e)}")
            return False

    def _ai_repair_openai(self, error_msg, repo_full):
        if not OPENAI_AVAILABLE or not self.openai_key:
            return False

        self._log_error("OpenAI 복구 시작...")

        try:
            client = openai.OpenAI(api_key=self.openai_key)

            folder = os.path.basename(self.folder_path.get())
            prompt = f"""GitHub Push 오류: {error_msg}

폴더: {folder}
레포지터리: {repo_full}

복구 Git 명령어만 출력."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )

            response_text = response.choices[0].message.content.strip()
            self._log_error(f"OpenAI 제안: {response_text[:150]}")

            return self._execute_repair_commands(response_text)

        except Exception as e:
            self._log_error(f"OpenAI 오류: {str(e)}")
            return False

    def _ai_repair_claude(self, error_msg, repo_full):
        if not CLAUDE_AVAILABLE or not self.claude_key:
            return False

        self._log_error("Claude 복구 시작...")

        try:
            client = anthropic.Anthropic(api_key=self.claude_key)

            folder = os.path.basename(self.folder_path.get())
            prompt = f"""GitHub Push 오류: {error_msg}

폴더: {folder}
레포지터리: {repo_full}

Git 복구 명령어만 출력."""

            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text.strip()
            self._log_error(f"Claude 제안: {response_text[:150]}")

            return self._execute_repair_commands(response_text)

        except Exception as e:
            self._log_error(f"Claude 오류: {str(e)}")
            return False

    def _execute_repair_commands(self, response_text):
        if "git" not in response_text.lower():
            return False

        commands = self._extract_commands(response_text)
        for cmd in commands:
            self._log_error(f"실행: {cmd}")
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.folder_path.get()
            )
            if result.returncode != 0:
                self._log_error(f"실패: {result.stderr[:100]}")
            else:
                self._log_error(f"성공")

        return True

    def _extract_commands(self, text):
        commands = []
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("git ") or line.startswith("!git"):
                cmd = line.lstrip("!").strip()
                if cmd.startswith("git "):
                    commands.append(cmd)
        return commands

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = GitHubUploader()
    app.run()