from typing import Optional, List

from wexample_filestate.config_value.readme_content_config_value import ReadmeContentConfigValue
from wexample_filestate_python.workdir.python_package_workdir import PythonPackageWorkdir
from wexample_helpers.helpers.string import string_remove_prefix


class PythonPackageReadmeContentConfigValue(ReadmeContentConfigValue):
    workdir: PythonPackageWorkdir
    vendor: Optional[str]

    def get_templates(self) -> Optional[List[str]]:
        project_info = self.workdir.get_project_info()
        project = project_info.get('project', {})
        
        # Extract information
        description = project.get('description', '')
        python_version = project.get('requires-python', '')
        dependencies = project.get('dependencies', [])
        homepage = project.get('urls', {}).get('homepage', '')
        license_info = project.get('license', {}).get('text', '')
        version = project.get('version', '')
        
        # Format dependencies list
        deps_list = '\n'.join([f'- {dep}' for dep in dependencies])

        return [
            f'# {self.build_package_name()}\n\n'
            f'{description}\n\n'
            f'Version: {version}\n\n'
            '## Requirements\n\n'
            f'- Python {python_version}\n\n'
            '## Dependencies\n\n'
            f'{deps_list}\n\n'
            '## Installation\n\n'
            '```bash\n'
            f'pip install {project.get("name", "")}\n'
            '```\n\n'
            '## Links\n\n'
            f'- Homepage: {homepage}\n\n'
            '## License\n\n'
            f'{license_info}'
        ]

    def build_package_name(self) -> str:
        project_info = self.workdir.get_project_info()

        # Get project name from pyproject.toml
        project_name = project_info.get('project', {}).get('name', '')

        # Remove vendor prefix if vendor is provided
        if self.vendor:
            vendor_prefix = f"{self.vendor.lower()}-"
            project_name = string_remove_prefix(project_name, vendor_prefix)

        # Convert remaining kebab-case to Title Case
        # e.g. "vendor-package-name" -> "Package Name"
        package_name = ' '.join(word.title() for word in project_name.split('-'))

        return package_name
