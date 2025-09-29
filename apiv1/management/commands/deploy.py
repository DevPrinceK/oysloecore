import os
import subprocess
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Automated Deployment Process'

    def handle(self, *args, **kwargs):
        venv_python = os.path.join("venv", "bin", "python")

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
