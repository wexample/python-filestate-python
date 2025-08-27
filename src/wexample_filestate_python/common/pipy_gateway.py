from pydantic import Field

from wexample_helpers_api.common.abstract_gateway import AbstractGateway


class PipyGateway(AbstractGateway):
    base_url: str | None = Field(
        default="https://pypi.org/",
        description="Base Pipy API URL"
    )

    def package_release_exists(self, package_name: str, version: str) -> bool:
        response = self.make_request(f'pypi/{package_name}/json')
        # Package exists
        if response.status_code == 200:
            return bool(response.json().get("releases", {}).get(version))

        return False
