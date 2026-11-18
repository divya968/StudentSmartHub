from django.core.management.base import BaseCommand

from hub.demo import ensure_demo_user


class Command(BaseCommand):
    help = "Create (or rebuild with --reset) the demo account with sample data."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete and recreate the demo user")

    def handle(self, *args, **opts):
        user = ensure_demo_user(reset=opts["reset"])
        self.stdout.write(self.style.SUCCESS(f"Demo user ready: '{user.username}'. Set DEMO_MODE=True to enable the Try Demo button."))
