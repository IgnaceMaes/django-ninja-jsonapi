from django.db import models


class User(models.Model):
    name = models.CharField(max_length=128)


class UserBio(models.Model):
    user = models.OneToOneField(User, related_name="bio", on_delete=models.CASCADE)
    birth_city = models.CharField(max_length=128)


class Computer(models.Model):
    serial = models.CharField(max_length=128)
    owner = models.ForeignKey(User, related_name="computers", on_delete=models.CASCADE)
