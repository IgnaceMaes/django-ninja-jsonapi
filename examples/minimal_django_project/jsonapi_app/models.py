from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=128)
    email = models.EmailField(unique=True)

    def __str__(self) -> str:
        return self.name


class Computer(models.Model):
    serial = models.CharField(max_length=128)
    owner = models.ForeignKey(Customer, related_name="computers", null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self) -> str:
        return self.serial
