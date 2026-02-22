from django.db import models


class User(models.Model):
    name = models.CharField(max_length=128)
    email = models.EmailField(unique=True)


class Computer(models.Model):
    serial = models.CharField(max_length=128)
    owner = models.ForeignKey(User, related_name="computers", null=True, blank=True, on_delete=models.SET_NULL)
