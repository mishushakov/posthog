from rest_framework import serializers, viewsets

from posthog.api.utils import WritableSerializerMethodField
from posthog.constants import AvailableFeature
from posthog.exceptions import EnterpriseFeatureException


class TaggedItemSerializerMixin(serializers.Serializer):
    """
    Serializer mixin that resolves appropriate response for tags depending on license.
    """

    tags = WritableSerializerMethodField(required=False)

    def is_licensed(self):
        return (
            "request" in self.context
            and not self.context["request"].user.is_anonymous
            and self.context["request"].user.organization.is_feature_available(AvailableFeature.TAGGING)
        )

    def get_tags(self, obj):
        if self.is_licensed():
            try:
                from ee.api.ee_tagged_item import EnterpriseTaggedItemSerializerMixin
            except ImportError:
                pass
            else:
                return EnterpriseTaggedItemSerializerMixin(self).get_tags(obj)
        return []

    def set_tags(self, tags, obj):
        if self.is_licensed():
            try:
                from ee.api.ee_tagged_item import EnterpriseTaggedItemSerializerMixin
            except ImportError:
                pass
            else:
                EnterpriseTaggedItemSerializerMixin(self).set_tags(tags, obj)
                return
        # Reject setting tags if non ee
        if tags:
            raise EnterpriseFeatureException()

    def create(self, validated_data):
        instance = super(TaggedItemSerializerMixin, self).create(validated_data)

        if self.is_licensed() and self.initial_data.get("tags", None):
            try:
                from ee.api.ee_tagged_item import EnterpriseTaggedItemSerializerMixin
            except ImportError:
                pass
            else:
                EnterpriseTaggedItemSerializerMixin(self).set_tags(self.initial_data["tags"], instance)

        return instance


class TaggedItemViewSetMixin(viewsets.GenericViewSet):
    def is_licensed(self):
        return (
            not self.request.user.is_anonymous
            # The below triggers an extra query to resolve user's organization.
            and self.request.user.organization.is_feature_available(AvailableFeature.TAGGING)
        )

    def get_queryset(self):
        queryset = super(TaggedItemViewSetMixin, self).get_queryset()
        if self.is_licensed():
            try:
                from ee.api.ee_tagged_item import EnterpriseTaggedItemViewSetMixin
            except ImportError:
                pass
            else:
                return EnterpriseTaggedItemViewSetMixin.get_queryset_with_tags(queryset)
        return queryset.defer("tags")
