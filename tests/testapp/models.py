"""Minimal Django models for E2E integration tests."""

from django.db import models


class Tag(models.Model):
    label = models.CharField(max_length=64)

    class Meta:
        app_label = "testapp"

    def __str__(self):
        return self.label


class Customer(models.Model):
    name = models.CharField(max_length=128)
    email = models.EmailField(unique=True)

    class Meta:
        app_label = "testapp"

    def __str__(self):
        return self.name


class Computer(models.Model):
    serial = models.CharField(max_length=128)
    owner = models.ForeignKey(
        Customer,
        related_name="computers",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    tags = models.ManyToManyField(Tag, related_name="computers", blank=True)

    class Meta:
        app_label = "testapp"

    def __str__(self):
        return self.serial
