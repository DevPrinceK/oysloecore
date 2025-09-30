import os
import subprocess
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Automated Deployment Process'

    def handle(self, *args, **kwargs):
        venv_python = os.path.join("venv", "bin", "python")

        # Preflight: if there are only .pyc/__pycache__ changes, discard them safely
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.returncode == 0:
            dirty = status.stdout.strip().splitlines()
            if dirty:
                # Extract file paths from porcelain format (positions 3: end)
                paths = []
                for line in dirty:
                    # Lines can start with ' M', 'M ', '??', 'A ', 'D ', 'R  old -> new', etc.
                    # Handle rename lines by taking the path after ' -> '
                    entry = line[3:] if len(line) > 3 else ""
                    if " -> " in entry:
                        entry = entry.split(" -> ", 1)[1]
                    paths.append(entry)

                def is_bytecode(p: str) -> bool:
                    return p.endswith('.pyc') or "/__pycache__/" in p or p.startswith('__pycache__/')

                if all(is_bytecode(p) for p in paths if p):
                    self.stdout.write(self.style.WARNING("Detected only Python bytecode/cache changes. Discarding them before pulling..."))
                    reset = subprocess.run(["git", "reset", "--hard"], capture_output=True, text=True)
                    if reset.returncode != 0:
                        self.stderr.write(self.style.ERROR("Failed to discard local bytecode changes:"))
                        self.stderr.write(self.style.ERROR(reset.stderr))
                        self.stderr.write(self.style.ERROR("🚫 Deployment aborted due to error"))
                        return
                else:
                    self.stderr.write(self.style.ERROR("Uncommitted changes detected that are not limited to .pyc/__pycache__."))
                    self.stderr.write(self.style.ERROR("Please commit or stash your changes before deploying."))
                    self.stderr.write(self.style.ERROR("🚫 Deployment aborted to avoid losing work."))
                    return

        commands = [
            ["git", "pull", "origin", "main"],
            [venv_python, "manage.py", "makemigrations"],
            [venv_python, "manage.py", "migrate"],
            [venv_python, "manage.py", "collectstatic", "--noinput"],
            ["sudo", "systemctl", "restart", "nginx"],
            ["sudo", "systemctl", "restart", "uvicorn"]
        ]

        for command in commands:
            cmd_str = " ".join(command)
            self.stdout.write(self.style.SUCCESS(f"Running: {cmd_str}"))

            process = subprocess.run(command, capture_output=True, text=True)

            if process.returncode == 0:
                self.stdout.write(self.style.SUCCESS(f"✅ Success: {cmd_str}"))
            else:
                self.stderr.write(self.style.ERROR(f"❌ Error running: {cmd_str}"))
                self.stderr.write(self.style.ERROR(process.stderr))
                self.stderr.write(self.style.ERROR("🚫 Deployment aborted due to error"))
                return  # Stop on first failure

        self.stdout.write(self.style.SUCCESS("====================="))
        self.stdout.write(self.style.SUCCESS("🚀 Deployment Successful!"))
        self.stdout.write(self.style.SUCCESS("====================="))
