from django.core.management.base import BaseCommand

from jsonapi_app.models import Computer, Customer


class Command(BaseCommand):
    help = "Seed demo customers and computers for the minimal example app"

    def handle(self, *args, **options):
        customers_data = [
            {"name": "Alice Johnson", "email": "alice@example.com"},
            {"name": "Bob Smith", "email": "bob@example.com"},
            {"name": "Charlie Brown", "email": "charlie@example.com"},
        ]

        for i in range(1, 31):
            customers_data.append(
                {
                    "name": f"Demo Customer {i:02d}",
                    "email": f"demo-customer-{i:02d}@example.com",
                }
            )

        created_customers = []
        for data in customers_data:
            customer, created = Customer.objects.get_or_create(
                email=data["email"],
                defaults={"name": data["name"]},
            )
            if not created and customer.name != data["name"]:
                customer.name = data["name"]
                customer.save(update_fields=["name"])
            created_customers.append(customer)

        computers_data = [
            {"serial": "MBP-001", "owner": created_customers[0]},
            {"serial": "MBP-002", "owner": created_customers[0]},
            {"serial": "THINK-101", "owner": created_customers[1]},
            {"serial": "NUC-900", "owner": created_customers[2]},
            {"serial": "LAB-777", "owner": None},
        ]

        for i in range(1, 76):
            owner = None if i % 7 == 0 else created_customers[(i - 1) % len(created_customers)]
            computers_data.append(
                {
                    "serial": f"DEMO-{i:04d}",
                    "owner": owner,
                }
            )

        for data in computers_data:
            Computer.objects.update_or_create(
                serial=data["serial"],
                defaults={"owner": data["owner"]},
            )

        self.stdout.write(self.style.SUCCESS("Seeded demo data successfully."))
        self.stdout.write(self.style.SUCCESS(f"Customers: {Customer.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Computers: {Computer.objects.count()}"))
