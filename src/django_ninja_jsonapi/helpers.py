"""High-level helpers for common JSON:API endpoint patterns."""

from __future__ import annotations

from typing import Any, Sequence


def apply_attributes(
    instance: Any,
    body: Any,
    *,
    save: bool = True,
    extra_update_fields: Sequence[str] = (),
    exclude: set[str] | None = None,
) -> dict[str, Any]:
    """Apply JSON:API body attributes to a Django model instance.

    Extracts ``exclude_unset=True`` attributes from the body, sets them on the
    instance via ``setattr``, and optionally saves the instance.

    Args:
        instance: A Django model instance to update.
        body: A ``jsonapi_body()`` parsed model.  Must have
            ``body.data.attributes``.
        save: If ``True`` (default), call ``instance.save()`` with
            ``update_fields`` limited to changed attributes plus
            *extra_update_fields*.
        extra_update_fields: Additional field names to include in
            ``update_fields`` (e.g. ``["updated_dt"]``).
        exclude: Optional set of attribute names to skip.

    Returns:
        The dict of attributes that were applied (``exclude_unset`` keys).

    Example::

        from django_ninja_jsonapi import apply_attributes

        @api.patch("/articles/{article_id}", ...)
        @jsonapi_resource("articles")
        def update_article(request, article_id: int, body: jsonapi_body(...)):
            article = Article.objects.get(id=article_id)
            apply_attributes(article, body, extra_update_fields=["updated_dt"])
            return article
    """
    attrs = body.data.attributes.model_dump(exclude_unset=True)

    if exclude:
        attrs = {k: v for k, v in attrs.items() if k not in exclude}

    for key, value in attrs.items():
        setattr(instance, key, value)

    if save and attrs:
        update_fields = [*attrs.keys(), *extra_update_fields]
        instance.save(update_fields=update_fields)

    return attrs
