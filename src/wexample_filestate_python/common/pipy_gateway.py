from __future__ import annotations

from wexample_api.common.abstract_gateway import AbstractGateway
from wexample_helpers.classes.field import public_field
from wexample_helpers.decorator.base_class import base_class


@base_class
class PipyGateway(AbstractGateway):
    base_url: str | None = public_field(
        default="https://pypi.org/", description="Base Pipy API URL"
    )

    def package_release_exists(self, package_name: str, version: str) -> bool:
        response = self.make_request(f"pypi/{package_name}/json")
        # Package exists
        if response.status_code == 200:
            return bool(response.json().get("releases", {}).get(version))

        return False
