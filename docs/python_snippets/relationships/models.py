from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=128)


class CustomerBio(models.Model):
    customer = models.OneToOneField(Customer, related_name="bio", on_delete=models.CASCADE)
    birth_city = models.CharField(max_length=128)


class Computer(models.Model):
    serial = models.CharField(max_length=128)
    owner = models.ForeignKey(Customer, related_name="computers", on_delete=models.CASCADE)
