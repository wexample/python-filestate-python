from typing import Optional, List

from wexample_filestate.config_value.readme_content_config_value import ReadmeContentConfigValue


class PythonPackageReadmeContentConfigValue(ReadmeContentConfigValue):

    def get_templates(self) -> Optional[List[str]]:
        return [
            '## Introduction',
            '## License'
        ]
